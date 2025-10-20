from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json

@login_required
def dashboard(request):
    """
    Main dashboard view for logged-in users
    """
    return render(request, "dashboard/dashboard.html", {
        'user': request.user
    })

@login_required
@require_http_methods(["GET"])
def get_user_progress(request):
    """
    API endpoint to fetch user progress data
    Returns JSON with user stats, quests, and recent lessons
    """
    user = request.user
    
    # TODO: Replace with actual database queries
    # For now, returning mock data that matches your requirements
    
    data = {
        'name': user.first_name or user.username,
        'level': 5,
        'xp': 1250,
        'xpToNextLevel': 1500,
        'streak': 7,
        'streakFreezeAvailable': True,
        'totalMinutes': 145,
        'unitsCompleted': 8,
        'avgQuizAccuracy': 85,
        'weeklyMinutes': 45,
        'dailyQuests': [
            {
                'id': 1,
                'title': 'Complete 1 lesson',
                'progress': 1,
                'total': 1,
                'xpReward': 20,
                'completed': True
            },
            {
                'id': 2,
                'title': 'Practice for 10 minutes',
                'progress': 7,
                'total': 10,
                'xpReward': 15,
                'completed': False
            },
            {
                'id': 3,
                'title': 'Perfect quiz score',
                'progress': 0,
                'total': 1,
                'xpReward': 25,
                'completed': False
            }
        ],
        'recentLessons': [
            {
                'id': 1,
                'title': 'Colors & Numbers (Part 1)',
                'score': 5,
                'total': 6,
                'date': 'Today'
            },
            {
                'id': 2,
                'title': 'Greetings & Introductions',
                'score': 6,
                'total': 6,
                'date': 'Yesterday'
            },
            {
                'id': 3,
                'title': 'Basic Phrases',
                'score': 4,
                'total': 6,
                'date': '2 days ago'
            }
        ]
    }
    
    return JsonResponse(data)
