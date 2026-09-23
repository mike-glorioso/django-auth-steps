from django.http import HttpRequest, HttpResponseBase

from .base_form_handler import BaseFormHandler
from .base_view import BaseView
from .verifier import Verifier
from .router import Router
from .utils import clear_pending_user



class RoutingVerifyView(BaseView):
    def __init__(self, verifier: Verifier, form_handler: BaseFormHandler):
        self._router = Router()
        self._form_handler = form_handler
        self._verifier = verifier

    def dispatch(self, request: HttpRequest) -> HttpResponseBase:
        request_method = request.method
        if request_method is not None and request_method.upper() == "POST":
            return self._router.route_try_next_method(request, False, False)
        clear_pending_user(request)
        self.form_handler.fill_form_from_none()
        return self.form_handler.render_with_form(request, html)

    def attempt_strategy(self, request: HttpRequest):
        return self._verifier.verify(request, self._form_handler)

