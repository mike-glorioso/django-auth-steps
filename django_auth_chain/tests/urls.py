from django.urls import include, path

urlpatterns = [
    path("", include("django_auth_chain.urls")),
]
