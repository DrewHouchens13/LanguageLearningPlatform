"""
BDD Step Definitions for Curriculum Features
Implements Given-When-Then steps for curriculum progression scenarios
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from home.models import (
    LearningModule,
    Lesson,
    SkillCategory,
    UserLanguageProfile,
    UserModuleProgress,
    UserSkillMastery,
    Flashcard,
    LessonQuizQuestion,
)

# Load all scenarios from curriculum feature files
scenarios('../curriculum/lesson_progression.feature')
scenarios('../curriculum/level_advancement.feature')


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def context():
    """Shared context"""
    return {}


@pytest.fixture
def django_client():
    """Django test client"""
    return Client()


# ============================================================================
# GIVEN STEPS
# ============================================================================

@given(parsers.parse('I am logged in as "{email}"'), target_fixture='logged_in_user')
def logged_in_user(email, django_client):
    """Create and log in a user"""
    user = User.objects.create_user(
        username='learner',
        email=email,
        password='SecurePass123!'
    )
    django_client.login(username='learner', password='SecurePass123!')
    return user


@given('the curriculum system has Spanish Level 1 content')
def curriculum_spanish_level1():
    """Create Spanish Level 1 curriculum content"""
    # Create module
    module = LearningModule.objects.get_or_create(
        language='Spanish',
        proficiency_level=1,
        defaults={
            'name': 'Basics',
            'description': 'Basic Spanish vocabulary and grammar'
        }
    )[0]

    # Get skill categories
    vocab = SkillCategory.objects.get(name='vocabulary')
    grammar = SkillCategory.objects.get(name='grammar')
    conversation = SkillCategory.objects.get(name='conversation')
    reading = SkillCategory.objects.get(name='reading')
    listening = SkillCategory.objects.get(name='listening')

    # Create 5 lessons
    skills = [vocab, grammar, conversation, reading, listening]
    for i, skill in enumerate(skills, 1):
        lesson = Lesson.objects.get_or_create(
            slug=f'spanish-level-1-{skill.name}',
            defaults={
                'title': f'{skill.name.title()} Lesson',
                'language': 'Spanish',
                'difficulty_level': 1,
                'skill_category': skill,
                'is_published': True,
                'category': skill.name.title(),
                'lesson_type': 'flashcard',
                'xp_value': 100,
            }
        )[0]

        # Add flashcards
        for j in range(5):
            Flashcard.objects.get_or_create(
                lesson=lesson,
                front_text=f'Spanish word {j}',
                defaults={
                    'back_text': f'English translation {j}',
                    'order': j
                }
            )

        # Add quiz questions
        for j in range(5):
            LessonQuizQuestion.objects.get_or_create(
                lesson=lesson,
                question=f'Question {j}?',
                defaults={
                    'options': ['A', 'B', 'C', 'D'],
                    'correct_index': 0,
                    'order': j
                }
            )

    return module


@given(parsers.parse('I am learning {language}'))
def learning_language(language, logged_in_user):
    """Set up user learning a language"""
    UserLanguageProfile.objects.get_or_create(
        user=logged_in_user,
        language=language,
        defaults={'proficiency_level': 1}
    )


@given(parsers.parse('I have access to Level {level:d}'))
def have_access_to_level(level, logged_in_user):
    """User has access to a level"""
    lang_profile = UserLanguageProfile.objects.get_or_create(
        user=logged_in_user,
        language='Spanish',
        defaults={'proficiency_level': level}
    )[0]
    lang_profile.proficiency_level = level
    lang_profile.save()


@given(parsers.parse('I am viewing the Level {level:d} {skill} lesson'))
def viewing_lesson(level, skill, logged_in_user):
    """User is viewing a specific lesson"""
    lesson = Lesson.objects.filter(
        language='Spanish',
        difficulty_level=level,
        skill_category__name=skill
    ).first()
    return lesson


@given(parsers.parse('I have completed {count:d} lessons in Level {level:d}'))
def completed_lessons(count, level, logged_in_user):
    """User has completed some lessons"""
    module = LearningModule.objects.get(
        language='Spanish',
        proficiency_level=level
    )
    progress, _ = UserModuleProgress.objects.get_or_create(
        user=logged_in_user,
        module=module
    )

    # Get lessons for this module
    lessons = module.get_lessons()[:count]
    progress.lessons_completed = [lesson.id for lesson in lessons]
    progress.save()


@given('I have completed all 5 lessons in Level 1')
def completed_all_lessons_level1(logged_in_user):
    """User has completed all lessons in Level 1"""
    module = LearningModule.objects.get(
        language='Spanish',
        proficiency_level=1
    )
    progress, _ = UserModuleProgress.objects.get_or_create(
        user=logged_in_user,
        module=module
    )
    lessons = module.get_lessons()
    progress.lessons_completed = [lesson.id for lesson in lessons]
    progress.save()


@given(parsers.parse('I failed the Spanish Level {level:d} test {hours:d} hours ago'))
def failed_test_hours_ago(level, hours, logged_in_user):
    """User failed a test some hours ago"""
    module = LearningModule.objects.get(
        language='Spanish',
        proficiency_level=level
    )
    progress, _ = UserModuleProgress.objects.get_or_create(
        user=logged_in_user,
        module=module
    )
    progress.last_test_date = timezone.now() - timedelta(hours=hours)
    progress.test_attempts = 1
    progress.best_test_score = 70.0
    progress.save()


@given(parsers.parse('I have weak {skill} skills ({percentage:d}% mastery)'))
def weak_skill_mastery(skill, percentage, logged_in_user):
    """User has weak mastery in a skill"""
    skill_cat = SkillCategory.objects.get(name=skill)
    UserSkillMastery.objects.update_or_create(
        user=logged_in_user,
        skill_category=skill_cat,
        language='Spanish',
        defaults={'mastery_percentage': float(percentage)}
    )


@given(parsers.parse('I have strong {skill} skills ({percentage:d}% mastery)'))
def strong_skill_mastery(skill, percentage, logged_in_user):
    """User has strong mastery in a skill"""
    skill_cat = SkillCategory.objects.get(name=skill)
    UserSkillMastery.objects.update_or_create(
        user=logged_in_user,
        skill_category=skill_cat,
        language='Spanish',
        defaults={'mastery_percentage': float(percentage)}
    )


# ============================================================================
# WHEN STEPS
# ============================================================================

@when('I visit the curriculum overview page')
def visit_curriculum_overview(django_client, logged_in_user):
    """Visit curriculum overview"""
    response = django_client.get(reverse('curriculum_overview', args=['Spanish']))
    return response


@when(parsers.parse('I visit the Level {level:d} module page'))
def visit_module_page(level, django_client):
    """Visit module detail page"""
    response = django_client.get(reverse('module_detail', args=['Spanish', level]))
    return response


@when('I complete all flashcards')
def complete_flashcards():
    """Complete flashcards"""
    pass  # Implementation would interact with flashcard UI


@when(parsers.parse('I complete the quiz with {score:d}% score'))
def complete_quiz_with_score(score):
    """Complete quiz with specific score"""
    pass  # Implementation would submit quiz answers


@when('I complete the 5th lesson')
def complete_fifth_lesson(logged_in_user):
    """Complete the final lesson"""
    module = LearningModule.objects.get(
        language='Spanish',
        proficiency_level=1
    )
    progress = UserModuleProgress.objects.get(
        user=logged_in_user,
        module=module
    )
    lessons = module.get_lessons()
    if len(progress.lessons_completed) == 4:
        progress.mark_lesson_complete(lessons[4].id)
        progress.save()


@when(parsers.parse('I try to access Level {level:d}'))
def try_access_level(level, django_client):
    """Try to access a locked level"""
    response = django_client.get(reverse('module_detail', args=['Spanish', level]))
    return response


@when('I click "Take Test"')
def click_take_test(django_client):
    """Click take test button"""
    response = django_client.get(reverse('module_test', args=['Spanish', 1]))
    return response


@when(parsers.parse('I answer {correct:d} out of {total:d} questions correctly ({percentage:d}%)'))
def answer_questions_correctly(correct, total, percentage):
    """Answer test questions"""
    pass  # Implementation would submit test answers


@when('I submit the test')
def submit_test():
    """Submit the test"""
    pass  # Implementation would submit test


# ============================================================================
# THEN STEPS
# ============================================================================

@then(parsers.parse('I should see all {count:d} levels for {language}'))
def see_all_levels(count, language, visit_curriculum_overview):
    """Verify all levels are visible"""
    assert visit_curriculum_overview.status_code == 200
    # Check context has modules
    modules = visit_curriculum_overview.context.get('modules', [])
    assert len(modules) == count


@then(parsers.parse('level {level:d} should be marked as {status}'))
def level_marked_as(level, status):
    """Verify level status"""
    pass  # Implementation would check level status in template


@then(parsers.parse('I should see {count:d} lessons ({skills})'))
def see_lessons(count, skills):
    """Verify lessons are visible"""
    pass  # Implementation would check lesson count


@then('the lesson should be marked as complete')
def lesson_marked_complete(logged_in_user):
    """Verify lesson is complete"""
    module = LearningModule.objects.get(
        language='Spanish',
        proficiency_level=1
    )
    progress = UserModuleProgress.objects.get(
        user=logged_in_user,
        module=module
    )
    assert len(progress.lessons_completed) > 0


@then(parsers.parse('my progress should show {completed:d}/{total:d} lessons completed'))
def progress_shows_lessons(completed, total, logged_in_user):
    """Verify progress display"""
    module = LearningModule.objects.get(
        language='Spanish',
        proficiency_level=1
    )
    progress = UserModuleProgress.objects.get(
        user=logged_in_user,
        module=module
    )
    assert len(progress.lessons_completed) == completed


@then('I should advance to Level 2')
def advance_to_level2(logged_in_user):
    """Verify level advancement"""
    lang_profile = UserLanguageProfile.objects.get(
        user=logged_in_user,
        language='Spanish'
    )
    assert lang_profile.proficiency_level == 2


@then('I should see a passing score of 90%')
def see_passing_score():
    """Verify passing score display"""
    pass  # Implementation would check test results page


@then('I should see a failing score of 70%')
def see_failing_score():
    """Verify failing score display"""
    pass  # Implementation would check test results page


@then(parsers.parse('{percentage:d}% of questions should be from {skill_type} skills ({skill})'))
def question_distribution(percentage, skill_type, skill):
    """Verify adaptive question distribution"""
    pass  # Implementation would check test composition

