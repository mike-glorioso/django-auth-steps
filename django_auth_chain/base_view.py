from django.http import HttpRequest, HttpResponseBase
from django.views import View

from .base_form_handler import BaseFormHandler
from .utils import clear_pending_user


class BaseView(View):
    def get(self, request: HttpRequest, form_handler: BaseFormHandler, html: str) -> HttpResponseBase:
        clear_pending_user(request)
        form_handler.fill_form_from_none()
        return form_handler.render_with_form(request, html)

