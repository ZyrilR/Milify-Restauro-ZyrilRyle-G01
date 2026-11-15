from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import MilifyAuthenticationForm
from .views import MilifyLogoutView, SignUpView


urlpatterns = [
    path("register/", SignUpView.as_view(), name="register"),
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
