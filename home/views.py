from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from .models import Lesson, LessonQuizQuestion, LessonAttempt
from django.views.decorators.http import require_http_methods


def landing(request):
    return render(request, "index.html")


def login_view(request):
    # If user is already logged in, redirect to home
    if request.user.is_authenticated:
        return redirect('landing')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Find user by email
        try:
            user = User.objects.get(email=email)
            username = user.username
        except User.DoesNotExist:
            messages.error(request, 'Invalid email or password.')
            return render(request, 'login.html')

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')

            # Redirect to next page if specified, otherwise to landing
            next_page = request.GET.get('next', 'landing')
            return redirect(next_page)
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html')


def signup_view(request):
    # If user is already logged in, redirect to home
    if request.user.is_authenticated:
        return redirect('landing')

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm-password')

        # Validate passwords match
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'login.html')

        # Validate password length
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'login.html')

        # Split name into first and last name
        name_parts = name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Create username from email (before @ symbol)
        username = email.split('@')[0]

        # Check if username already exists, if so, add numbers
        original_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{original_username}{counter}"
            counter += 1

        try:
            # Create new user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Log the user in
            login(request, user)
            messages.success(request, f'Welcome to Language Learning Platform, {first_name}!')
            return redirect('landing')

        except IntegrityError:
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'login.html')
        except Exception as e:
            messages.error(request, 'An error occurred while creating your account. Please try again.')
            return render(request, 'login.html')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('landing')


@login_required
def dashboard(request):
    """Example of a protected view that requires login"""
    return render(request, 'dashboard.html')


def progress_view(request):
    """Progress dashboard - shows stats for logged-in users, CTA for guests"""
    if request.user.is_authenticated:
        # Get or create user progress record
        from .models import UserProgress
        user_progress, created = UserProgress.objects.get_or_create(user=request.user)
        
        # Get weekly stats
        weekly_stats = user_progress.get_weekly_stats()
        
        # Prepare context for authenticated users
        context = {
            'weekly_minutes': weekly_stats['weekly_minutes'],
            'weekly_lessons': weekly_stats['weekly_lessons'],
            'weekly_accuracy': weekly_stats['weekly_accuracy'],
            'total_minutes': user_progress.total_minutes_studied,
            'total_lessons': user_progress.total_lessons_completed,
            'total_quizzes': user_progress.total_quizzes_taken,
            'overall_accuracy': user_progress.overall_quiz_accuracy,
        }
    else:
        # Context for guest users (all None/empty)
        context = {
            'weekly_minutes': None,
            'weekly_lessons': None,
            'weekly_accuracy': None,
            'total_minutes': None,
            'total_lessons': None,
            'total_quizzes': None,
            'overall_accuracy': None,
        }
    
    return render(request, 'progress.html', context)

def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    return render(request, "lessons/shapes/lesson_detail.html", {"lesson": lesson})



def lesson_quiz(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    questions = lesson.quiz_questions.all()
    qlist = []
    for q in questions:
        qlist.append({
            'id': q.id,
            'order': q.order,
            'question': q.question,
            'options': q.options,
        })
    return render(request, 'lessons/shapes/quiz.html', {'lesson': lesson, 'questions': qlist})


@require_http_methods(["POST"])
def submit_lesson_quiz(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    # Accept JSON body or regular POST
    try:
        if request.content_type == 'application/json':
            payload = json.loads(request.body.decode('utf-8'))
        else:
            payload = request.POST.dict()
    except Exception:
        return HttpResponseBadRequest("Invalid payload")

    answers = payload.get('answers')
    # answers expected as list of {question_id: int, selected_index: int}
    if not answers:
        # try JSON string in 'answers' param
        raw = payload.get('answers')
        if raw:
            answers = json.loads(raw)
    if not answers or not isinstance(answers, list):
        return HttpResponseBadRequest("No answers provided")

    # Evaluate
    score = 0
    total = 0
    for a in answers:
        qid = a.get('question_id') or a.get('id')
        sel = a.get('selected_index') if 'selected_index' in a else a.get('selected')
        try:
            q = LessonQuizQuestion.objects.get(id=qid, lesson=lesson)
        except LessonQuizQuestion.DoesNotExist:
            continue
        total += 1
        if int(sel) == int(q.correct_index):
            score += 1

    attempt = LessonAttempt.objects.create(
        lesson=lesson,
        user=request.user if request.user.is_authenticated else None,
        score=score,
        total=total
    )

    # If request from JS expect JSON; else redirect to results
    if request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'score': score, 'total': total, 'attempt_id': attempt.id, 'redirect_url': reverse('lesson_results', args=[lesson.id, attempt.id])})
    return redirect('lesson_results', lesson_id=lesson.id, attempt_id=attempt.id)

def lesson_results(request, lesson_id, attempt_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    attempt = get_object_or_404(LessonAttempt, id=attempt_id, lesson=lesson)
    next_lesson = lesson.next_lesson
    context = {'lesson': lesson, 'attempt': attempt, 'next_lesson': next_lesson}
    return render(request, 'lessons/shapes/results.html', context)

def lessons_list(request):
    lessons = Lesson.objects.all().order_by('id')
    return render(request, 'lessons_list.html', {'lessons': lessons})

def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    cards = lesson.cards.all()
    context = {'lesson': lesson, 'cards': cards}
    return render(request, 'lessons/lesson_detail.html', context)