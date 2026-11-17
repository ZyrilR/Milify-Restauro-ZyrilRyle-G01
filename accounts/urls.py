from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django.views.generic import RedirectView

from .forms import MilifyAuthenticationForm
from .views import MilifyLogoutView, SignUpView, change_password, profile


urlpatterns = [
    path("", RedirectView.as_view(url=reverse_lazy("login"), permanent=False), name="accounts_home"),
    path("register/", SignUpView.as_view(), name="register"),
    path("profile/", profile, name="profile"),
    path("change-password/", change_password, name="change_password"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            authentication_form=MilifyAuthenticationForm,
            template_name="registration/login.html",
        ),
        name="login",
    ),
    path("logout/", MilifyLogoutView.as_view(), name="logout"),
]
