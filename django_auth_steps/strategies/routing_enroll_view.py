from django.http import HttpRequest, HttpResponseBase
from django.views import View

from ..redirect_if_authenticated import RedirectIfAuthenticatedMixin
from ..router import Router


class RoutingEnrollView(RedirectIfAuthenticatedMixin, View):
    def get(self, request: HttpRequest, *args: object, **kwargs: object) -> HttpResponseBase:
        return Router().route_try_next_method(request, is_enrolling=True)

    def post(self, request: HttpRequest, *args: object, **kwargs: object) -> HttpResponseBase:
        return Router().route_try_next_method(request, is_enrolling=True)
