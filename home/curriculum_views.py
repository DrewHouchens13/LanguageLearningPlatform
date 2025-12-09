"""
Curriculum system views for the Language Learning Platform.

Handles all curriculum-related HTTP request processing including:
- Curriculum overview and module navigation
- Module detail views with lesson tracking
- Skill-based lesson views
- Lesson completion and XP awarding
- Adaptive module tests (generation, display, submission, results)

All views require authentication and follow Django best practices.
"""
# Standard library imports
import json
import logging

# Django imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import TemplateDoesNotExist
from django.urls import reverse
from django.views.decorators.http import require_POST

# Local application imports
from .models import (Lesson, LessonCompletion, UserLanguageProfile)
from .services.adaptive_test_service import AdaptiveTestService

logger = logging.getLogger(__name__)


# ============================================
# HELPER FUNCTIONS
# ============================================

def _is_previous_level_complete(user_progress: dict, language: str, level: int) -> bool:
    """Check if the previous level is complete."""
    if level <= 1:
        return True
    
    for progress in user_progress.values():
        if (progress.module.language == language and 
            progress.module.proficiency_level == level - 1):
            return progress.is_module_complete
    
    return False


def _filter_lessons_by_user_level(lessons, user, language):
    """
    Filter lessons based on user's current level and completion status.
    
    Rules:
    - Show all lessons for user's current level
    - Show completed lessons from previous levels
    - Hide lessons from future levels
    - Always show shapes and colors if they're level 1
    
    Args:
        lessons: QuerySet of Lesson objects
        user: User object (can be AnonymousUser)
        language: Target language
        
    Returns:
        QuerySet: Filtered lessons
    """
    from .models import UserModuleProgress, LearningModule
    
    if not user.is_authenticated:
        # For anonymous users, only show level 1 lessons
        return lessons.filter(difficulty_level=1)
    
    # Get user's current level for this language
    lang_profile = UserLanguageProfile.objects.filter(
        user=user,
        language=language
    ).first()
    
    # Ensure current_level is always an integer (default to 1 if None)
    # Handle legacy CEFR string values (A1, A2, B1) by converting to integers
    if lang_profile and lang_profile.proficiency_level is not None:
        prof_level = lang_profile.proficiency_level
        # If it's a string (legacy CEFR format), convert it
        if isinstance(prof_level, str):
            cefr_to_level = {'A1': 1, 'A2': 2, 'B1': 3}
            current_level = cefr_to_level.get(prof_level, 1)
        else:
            # It's already an integer or can be converted
            try:
                current_level = int(prof_level)
            except (ValueError, TypeError):
                current_level = 1
    else:
        current_level = 1
    
    # Get all completed lesson IDs across all levels for this language
    completed_lesson_ids = set()
    user_progress = UserModuleProgress.objects.filter(
        user=user,
        module__language=language
    ).select_related('module')
    
    for progress in user_progress:
        completed_lesson_ids.update(progress.lessons_completed)
    
    # Filter lessons:
    # 1. Current level lessons (always visible)
    # 2. Previous level lessons that are completed
    # 3. Shapes and colors if level 1 (always visible at level 1+)
    filtered_lessons = []
    for lesson in lessons:
        # Ensure difficulty_level is an integer (handle any legacy string values)
        try:
            lesson_level = int(lesson.difficulty_level) if lesson.difficulty_level is not None else 1
        except (ValueError, TypeError):
            # If difficulty_level is invalid, default to 1
            lesson_level = 1
        
        # Check if this is a shapes/colors lesson (handles 'shapes', 'shapes-french', etc.)
        is_shapes_colors = lesson.slug and (lesson.slug.startswith('shapes') or lesson.slug.startswith('colors'))
        
        if is_shapes_colors and lesson_level == 1:
            # Always show shapes/colors if user is at least level 1
            if current_level >= 1:
                filtered_lessons.append(lesson.id)
        elif lesson_level == current_level:
            # Always show current level lessons
            filtered_lessons.append(lesson.id)
        elif lesson_level < current_level:
            # Show previous level lessons only if completed
            if lesson.id in completed_lesson_ids:
                filtered_lessons.append(lesson.id)
    
    return lessons.filter(id__in=filtered_lessons)


def _get_level_1_special_lessons(language):
    """
    Get shapes and colors lessons for level 1.
    
    These are special lessons that should always appear in level 1
    alongside the 5 skill-based lessons.
    
    Args:
        language: Target language
        
    Returns:
        QuerySet: Shapes and colors lessons for this language at level 1
    """
    return Lesson.objects.filter(
        language=language,
        difficulty_level=1,
        is_published=True
    ).filter(
        Q(slug__startswith='shapes') | Q(slug__startswith='colors')
    ).order_by('order', 'id')


def _get_custom_lesson_icon(lesson):
    """
    Get a custom icon for specific lessons (shapes, colors, etc.).
    
    Args:
        lesson: Lesson object
        
    Returns:
        str: Emoji icon or None if no custom icon
    """
    if not lesson.slug:
        return None
    
    slug_lower = lesson.slug.lower()
    
    # Special foundational lessons
    if 'shapes' in slug_lower:
        return '🔷'
    if 'colors' in slug_lower or 'colours' in slug_lower:
        return '🎨'
    
    return None


def _get_lesson_icon(lesson):
    """
    Determine appropriate icon for a lesson based on its content.
    
    Args:
        lesson: Lesson object
        
    Returns:
        str: Emoji icon representing the lesson topic
    """
    # Check for custom icon first
    custom_icon = _get_custom_lesson_icon(lesson)
    if custom_icon:
        return custom_icon
    
    # Fall back to skill category icon if available
    if lesson.skill_category:
        return lesson.skill_category.icon
    
    # Default icon
    return '📚'


# ============================================
# CURRICULUM VIEWS
# ============================================

@login_required
def curriculum_overview(request, language):
    """
    Display all 10 levels for a language curriculum.
    
    Shows level progress, completion status, and navigation to each module.
    
    Args:
        request: HTTP request object
        language: Target language (e.g., 'Spanish', 'French')
    
    Returns:
        HttpResponse: Rendered curriculum overview template
    """
    from .models import LearningModule, UserModuleProgress
    
    # Normalize language name
    language = language.strip().title()
    
    # Get all modules for this language
    modules = LearningModule.objects.filter(
        language=language
    ).order_by('proficiency_level')
    
    if not modules.exists():
        messages.info(request, f'No curriculum available for {language} yet.')
        return redirect('lessons_list')
    
    # Get user's progress for each module
    user_progress = {
        p.module_id: p for p in UserModuleProgress.objects.filter(
            user=request.user,
            module__language=language
        ).select_related('module')
    }
    
    # Build module data with progress
    module_data = []
    for module in modules:
        progress = user_progress.get(module.id)
        module_data.append({
            'module': module,
            'progress': progress,
            'lessons_completed': len(progress.lessons_completed) if progress else 0,
            'is_complete': progress.is_module_complete if progress else False,
            'best_score': progress.best_test_score if progress else 0,
            'is_locked': module.proficiency_level > 1 and not _is_previous_level_complete(
                user_progress, language, module.proficiency_level
            ),
        })
    
    # Get user's current level for this language
    lang_profile = UserLanguageProfile.objects.filter(
        user=request.user,
        language=language
    ).first()
    current_level = lang_profile.proficiency_level if lang_profile else 1
    
    context = {
        'language': language,
        'modules': module_data,
        'current_level': current_level,
    }
    
    return render(request, 'curriculum/overview.html', context)


@login_required
def module_detail(request, language, level):
    """
    Display a learning module with its 5 lessons and test access.
    
    Shows lesson completion status and enables test-taking when ready.
    For level 1, also includes shapes and colors lessons.
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level (1-10)
    
    Returns:
        HttpResponse: Rendered module detail template
    """
    from .models import LearningModule, UserModuleProgress, SkillCategory
    
    language = language.strip().title()
    
    # Get the module
    module = get_object_or_404(
        LearningModule,
        language=language,
        proficiency_level=level
    )
    
    # Get user's progress
    progress, _ = UserModuleProgress.objects.get_or_create(
        user=request.user,
        module=module
    )
    
    # Get lessons for this module with completion status
    lessons = module.get_lessons()
    lesson_data = []
    for lesson in lessons:
        # Check for custom icon first, then fall back to skill category icon
        custom_icon = _get_custom_lesson_icon(lesson)
        icon = custom_icon if custom_icon else (lesson.skill_category.icon if lesson.skill_category else '📚')
        lesson_data.append({
            'lesson': lesson,
            'is_complete': lesson.id in progress.lessons_completed,
            'skill_icon': icon,
            'skill_name': lesson.skill_category.get_name_display() if lesson.skill_category else 'Unknown',
        })
    
    # For level 1, also include optional lessons
    if level == 1:
        special_lessons = _get_level_1_special_lessons(language)
        for lesson in special_lessons:
            # Check if already in lesson_data (shouldn't happen, but safe)
            if not any(item['lesson'].id == lesson.id for item in lesson_data):
                # Check for custom icon first, then fall back to lesson icon
                custom_icon = _get_custom_lesson_icon(lesson)
                icon = custom_icon if custom_icon else _get_lesson_icon(lesson)
                lesson_data.append({
                    'lesson': lesson,
                    'is_complete': lesson.id in progress.lessons_completed,
                    'skill_icon': icon,
                    'skill_name': lesson.title.replace(f' in {language}', '').replace(f' in {language.title()}', ''),
                })
        # Sort by order to maintain proper sequence
        lesson_data.sort(key=lambda x: (x['lesson'].order, x['lesson'].id))
    
    # Check if test is available
    test_service = AdaptiveTestService()
    test_status = test_service.can_take_test(request.user, module)
    
    # Calculate progress toward test (only count the 5 required skill-based lessons)
    required_lessons = module.get_lessons()
    completed_required = sum(1 for lesson in required_lessons if lesson.id in progress.lessons_completed)
    lessons_remaining = max(0, 5 - completed_required)
    
    context = {
        'language': language,
        'level': level,
        'module': module,
        'progress': progress,
        'lessons': lesson_data,
        'can_take_test': test_status['can_take'],
        'test_status_reason': test_status['reason'],
        'retry_available_at': test_status.get('retry_available_at'),
        'completed_required': completed_required,
        'lessons_remaining': lessons_remaining,
    }
    
    return render(request, 'curriculum/module_detail.html', context)


@login_required
def lesson_by_skill(request, language, level, skill):
    """
    Display a lesson by skill category within a level.
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level (1-10)
        skill: Skill category (vocabulary, grammar, etc.)
    
    Returns:
        HttpResponse: Rendered lesson template
    """
    from .models import SkillCategory, UserModuleProgress, LearningModule
    
    language = language.strip().title()
    skill = skill.strip().lower()
    
    # Get the skill category
    skill_category = get_object_or_404(SkillCategory, name=skill)
    
    # Get the lesson
    lesson = get_object_or_404(
        Lesson,
        language=language,
        difficulty_level=level,
        skill_category=skill_category,
        is_published=True
    )
    
    # Get module progress for marking completion
    module = LearningModule.objects.filter(
        language=language,
        proficiency_level=level
    ).first()
    
    progress = None
    if module:
        progress, _ = UserModuleProgress.objects.get_or_create(
            user=request.user,
            module=module
        )
    
    # Get flashcards and quiz questions
    flashcards = lesson.cards.all().order_by('order')
    quiz_questions = lesson.quiz_questions.all().order_by('order')
    
    context = {
        'language': language,
        'level': level,
        'skill': skill,
        'lesson': lesson,
        'flashcards': flashcards,
        'quiz_questions': quiz_questions,
        'progress': progress,
        'is_complete': progress and lesson.id in progress.lessons_completed,
    }
    
    # Choose template based on skill type
    template_name = f'curriculum/lesson_{skill}.html'
    try:
        return render(request, template_name, context)
    except TemplateDoesNotExist:
        return render(request, 'curriculum/lesson_base.html', context)


@login_required
@require_POST
def complete_curriculum_lesson(request, language, level, skill):
    """
    Mark a curriculum lesson as complete and award XP.
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level
        skill: Skill category
    
    Returns:
        JsonResponse: Success/failure response
    """
    from .models import LearningModule, UserModuleProgress, SkillCategory
    
    language = language.strip().title()
    skill = skill.strip().lower()
    
    # Get the lesson
    skill_category = get_object_or_404(SkillCategory, name=skill)
    lesson = get_object_or_404(
        Lesson,
        language=language,
        difficulty_level=level,
        skill_category=skill_category,
        is_published=True
    )
    
    # Get module progress
    module = get_object_or_404(
        LearningModule,
        language=language,
        proficiency_level=level
    )
    
    progress, _ = UserModuleProgress.objects.get_or_create(
        user=request.user,
        module=module
    )
    
    # Mark lesson complete
    if lesson.id not in progress.lessons_completed:
        progress.mark_lesson_complete(lesson.id)
        
        # Award XP
        if hasattr(request.user, 'profile'):
            xp_result = request.user.profile.award_xp(lesson.xp_value)
        else:
            xp_result = {'xp_awarded': 0}
        
        # Record lesson completion
        LessonCompletion.objects.create(
            user=request.user,
            lesson_id=str(lesson.id),
            lesson_title=lesson.title,
            language=language,
            duration_minutes=5  # Estimated
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Lesson completed! +{xp_result.get("xp_awarded", 0)} XP',
            'lessons_completed': len(progress.lessons_completed),
            'can_take_test': progress.all_lessons_completed(),
        })
    
    return JsonResponse({
        'success': True,
        'message': 'Lesson already completed',
        'lessons_completed': len(progress.lessons_completed),
        'can_take_test': progress.all_lessons_completed(),
    })


@login_required
def module_test_generate(request, language, level):
    """
    Generate the adaptive test asynchronously (called from loading page).
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level
    
    Returns:
        JsonResponse: Success/error status
    """
    from .models import LearningModule
    
    language = language.strip().title()
    
    # Get the module
    module = get_object_or_404(
        LearningModule,
        language=language,
        proficiency_level=level
    )
    
    # Check if user can take the test
    test_service = AdaptiveTestService()
    test_status = test_service.can_take_test(request.user, module)
    
    if not test_status['can_take']:
        return JsonResponse({
            'success': False,
            'error': test_status['reason']
        }, status=403)
    
    try:
        # Generate the test
        test_data = test_service.generate_adaptive_test(
            request.user, language, level
        )
        
        # Store test data in session for validation on submit
        request.session[f'test_{language}_{level}'] = test_data
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'test_id': test_data.get('test_id'),
            'total_questions': test_data.get('total_questions', 0)
        })
    except Exception as e:
        logger.error('Error generating test: %s', str(e), exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to generate test. Please try again.'
        }, status=500)


@login_required
def module_test(request, language, level):
    """
    Display the adaptive test for a module.
    
    Shows loading page if test not yet generated, otherwise displays the test.
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level
    
    Returns:
        HttpResponse: Rendered test template, loading page, or redirect if not eligible
    """
    from .models import LearningModule
    
    language = language.strip().title()
    
    # Get the module
    module = get_object_or_404(
        LearningModule,
        language=language,
        proficiency_level=level
    )
    
    # Check if user can take the test
    test_service = AdaptiveTestService()
    test_status = test_service.can_take_test(request.user, module)
    
    if not test_status['can_take']:
        messages.warning(request, test_status['reason'])
        return redirect('module_detail', language=language, level=level)
    
    # Check if test is already generated in session
    session_key = f'test_{language}_{level}'
    test_data = request.session.get(session_key)
    
    # If test not generated yet, show loading page
    if not test_data:
        context = {
            'language': language,
            'level': level,
            'module': module,
        }
        return render(request, 'curriculum/test_loading.html', context)
    
    # Test is ready, display it
    context = {
        'language': language,
        'level': level,
        'module': module,
        'test': test_data,
        'questions': test_data['questions'],
        'time_limit': test_data['time_limit_minutes'],
    }
    
    return render(request, 'curriculum/test.html', context)


@login_required
@require_POST
def submit_module_test(request, language, level):
    """
    Submit and evaluate a module test.
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level
    
    Returns:
        JsonResponse: Test results with score and progression info
    """
    from .models import LearningModule
    
    language = language.strip().title()
    
    # Get the module
    module = get_object_or_404(
        LearningModule,
        language=language,
        proficiency_level=level
    )
    
    # Get test data from session
    session_key = f'test_{language}_{level}'
    test_data = request.session.get(session_key)
    
    if not test_data:
        return JsonResponse({
            'error': 'Test session expired. Please start a new test.'
        }, status=400)
    
    # Parse answers from request
    try:
        data = json.loads(request.body)
        user_answers = data.get('answers', [])
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request data'}, status=400)
    
    # Grade answers
    questions = test_data['questions']
    graded_answers = []
    
    for answer in user_answers:
        q_id = answer.get('question_id')
        user_answer = answer.get('answer_index')
        
        # Find the question
        question = next((q for q in questions if q['id'] == q_id), None)
        if question:
            is_correct = user_answer == question['correct_index']
            graded_answers.append({
                'question_id': q_id,
                'is_correct': is_correct,
                'skill': question.get('skill', 'vocabulary'),
                'correct_index': question['correct_index'],
                'user_answer': user_answer,
            })
    
    # Evaluate with the service
    test_service = AdaptiveTestService()
    result = test_service.evaluate_test(request.user, module, graded_answers)
    
    # Clear test from session
    del request.session[session_key]
    
    # Return results
    return JsonResponse({
        'success': True,
        'score': result['score'],
        'correct': result['correct'],
        'total': result['total'],
        'passed': result['passed'],
        'new_level': result['new_level'],
        'feedback': result['feedback'],
        'can_retry_at': result['can_retry_at'].isoformat() if result['can_retry_at'] else None,
        'redirect_url': reverse('test_results', kwargs={
            'language': language,
            'level': level,
        }) if result['passed'] else None,
    })


@login_required
def test_results(request, language, level):
    """
    Display test results page.
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level
    
    Returns:
        HttpResponse: Rendered results template
    """
    from .models import LearningModule, UserModuleProgress
    
    language = language.strip().title()
    
    module = get_object_or_404(
        LearningModule,
        language=language,
        proficiency_level=level
    )
    
    progress = UserModuleProgress.objects.filter(
        user=request.user,
        module=module
    ).first()
    
    context = {
        'language': language,
        'level': level,
        'module': module,
        'progress': progress,
        'passed': progress.is_module_complete if progress else False,
        'best_score': progress.best_test_score if progress else 0,
        'next_level': level + 1 if level < 10 else None,
    }
    
    return render(request, 'curriculum/test_results.html', context)

