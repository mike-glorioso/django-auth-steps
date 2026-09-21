from django.urls import path

from .user_select_view import UserSelectView
from .views import LogoutView

app_name = "accounts"


def register_robots(base_url: str = ""):
    return [("User-Agent *", "Disallow /{base_url}")]


urlpatterns = [
    path("user-start/", UserSelectView.get, name="identify-user"),
    path("logout/", LogoutView.get, name="logout"),
]
