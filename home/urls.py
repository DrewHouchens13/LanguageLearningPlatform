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
]
