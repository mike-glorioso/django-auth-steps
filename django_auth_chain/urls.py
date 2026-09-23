from django.urls import path

from .strategies.routing_enroll_view import RoutingEnrollView
from .strategies.routing_verify_view import RoutingVerifyView
from .user_select_view import UserSelectView
from .views import LogoutView, UserHomeView

app_name = "django_auth_chain"


def register_robots_disallow(*, base_url: str = "", user_agent: str = "*"):
    return [(f"User-Agent: {user_agent}", f"Disallow: /{base_url}")]


urlpatterns = [
    path("", UserHomeView.as_view(), name="user_home"),
    path("user-select/", UserSelectView.as_view(), name="user_select"),
    path("enroll/", RoutingEnrollView.as_view(), name="enroll"),
    path("verify/", RoutingVerifyView.as_view(), name="verify"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
