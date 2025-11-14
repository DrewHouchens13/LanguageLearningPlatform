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
    path("lessons/", views.lessons_list, name="lessons_list"),
    path("lessons/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),
    path("lessons/<int:lesson_id>/quiz/", views.lesson_quiz, name="lesson_quiz"),
    path("lessons/<int:lesson_id>/submit/", views.submit_lesson_quiz, name="submit_lesson_quiz"),
    path("lessons/<int:lesson_id>/results/<int:attempt_id>/", views.lesson_results, name="lesson_results"),

    # Daily Quest paths
    path("quests/daily/", views.daily_quest_view, name="daily_quest"),
    path("quests/history/", views.quest_history, name="quest_history"),
]



