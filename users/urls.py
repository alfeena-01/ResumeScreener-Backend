from django.urls import path
from .views import UserInfoView, SignUpView, LoginView, JobListView, JobDetailView, ResumeUploadView, ResumeDetailView, JobApplicationCreateView, JobApplicationListView, JobApplicationDetailView, NotificationListView, NotificationDetailView, AIGenerateJDView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("login/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("user-info/", UserInfoView.as_view(), name="user-info"),
    path("jobs/", JobListView.as_view(), name="job-list"),
    path("jobs/<int:pk>/", JobDetailView.as_view(), name="job-detail"),
    path("jobs/generate-description/", AIGenerateJDView.as_view(), name="generate-jd"),
    path("resume/upload/", ResumeUploadView.as_view(), name="resume-upload"),
    path("resume/", ResumeDetailView.as_view(), name="resume-detail"),
    path("applications/apply/", JobApplicationCreateView.as_view(), name="job-apply"),
    path("applications/", JobApplicationListView.as_view(), name="job-applications"),
    path("applications/<int:pk>/", JobApplicationDetailView.as_view(), name="job-application-detail"),
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path("notifications/<int:pk>/", NotificationDetailView.as_view(), name="notification-detail"),
]