"""
URL routing configuration for the home application.

Defines URL patterns for:
- Authentication (login, signup, logout, password reset)
- Dashboard and user account management
- Onboarding assessment system
- Lesson and quiz system
- Daily Quest system
"""
from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("progress/", views.progress_view, name="progress"),
    path("account/", views.account_view, name="account"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("reset-password/<uidb64>/<token>/", views.reset_password_view, name="reset_password"),
    path("forgot-username/", views.forgot_username_view, name="forgot_username"),
    
    # Onboarding assessment paths
    path("onboarding/", views.onboarding_welcome, name="onboarding_welcome"),
    path("onboarding/quiz/", views.onboarding_quiz, name="onboarding_quiz"),
    path("onboarding/submit/", views.submit_onboarding, name="submit_onboarding"),
    path("onboarding/results/", views.onboarding_results, name="onboarding_results"),

  # Lesson paths
    # 🤖 AI ASSISTANT WARNING - URL PATTERN ORDERING IS CRITICAL!
    # ALWAYS put more specific patterns (<int:...>) BEFORE general patterns (<str:...>)
    #
    # CORRECT ORDER (current):
    #   1. lessons/<int:lesson_id>/        ← Matches numbers only (e.g., /lessons/2/)
    #   2. lessons/<str:language>/         ← Matches any string (e.g., /lessons/spanish/)
    #
    # WRONG ORDER (causes bugs):
    #   1. lessons/<str:language>/         ← Would match "2" as a language name!
    #   2. lessons/<int:lesson_id>/        ← Never reached for numeric IDs
    #
    # If you change this order, lesson detail pages will break!
    # Example bug: /lessons/2/ would be interpreted as "show lessons for language '2'"
    #
    path("lessons/", views.lessons_list, name="lessons_list"),
    path("lessons/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),
    path("lessons/<int:lesson_id>/quiz/", views.lesson_quiz, name="lesson_quiz"),
    path("lessons/<int:lesson_id>/submit/", views.submit_lesson_quiz, name="submit_lesson_quiz"),
    path("lessons/<int:lesson_id>/results/<int:attempt_id>/", views.lesson_results, name="lesson_results"),
    path("lessons/<str:language>/", views.lessons_by_language, name="lessons_by_language"),
    path("speech/generate/", views.generate_onboarding_speech, name="generate_onboarding_speech"),
    path("lessons/<int:lesson_id>/speech/<int:card_order>/", views.generate_onboarding_speech, name="generate_speech"),


    # Daily Quest paths
    path("quests/daily/", views.daily_quest_view, name="daily_quest"),
    path("quests/daily/submit/", views.daily_quest_submit, name="daily_quest_submit"),
    path("quests/history/", views.quest_history, name="quest_history"),

    # YouTube Transcript Feature (Free API - No Key Required)
    path("youtube-transcript/", views.youtube_transcript, name="youtube_transcript"),
    path("youtube-transcript/api/", views.get_youtube_transcript_api, name="get_youtube_transcript_api"),
]



