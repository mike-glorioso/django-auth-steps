from django.urls import path

from .user_select_view import UserSelectView
from .views import LogoutView

app_name = "django_auth_chain"


def register_robots_disallow(*, base_url: str = "", user_agent: str = "*"):
    return [(f"User-Agent: {user_agent}", f"Disallow: /{base_url}")]


urlpatterns = [
    path("user-start", UserSelectView.as_view(), name="user_select"),
    path("logout", LogoutView.as_view(), name="logout"),
]
