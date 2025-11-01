from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("progress/", views.progress_view, name="progress"),
    path("lessons/", views.lessons_list, name="lessons_list"),
    path("lessons/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),
    path("lessons/<int:lesson_id>/quiz/", views.lesson_quiz, name="lesson_quiz"),
    path("lessons/<int:lesson_id>/submit/", views.submit_lesson_quiz, name="submit_lesson_quiz"),
    path("lessons/<int:lesson_id>/results/<int:attempt_id>/", views.lesson_results, name="lesson_results"),
]