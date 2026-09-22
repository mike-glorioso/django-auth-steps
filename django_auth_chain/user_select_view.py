from django.contrib.auth.models import (
    User,
)
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import render
from django.views import View

from .constants import (
    FORM,
    PENDING_ENROLLMENT_USER_IDENTIFIER,
    PENDING_VERIFICATION_USER_KEY,
    USER_SELECT_HTML,
    VERIFICATION_METHOD_CODE,
    VERIFIED_METHOD_CODES,
)
from .errors import AuthMethodNotFoundError
from .forms import (
    UserSelectForm,
)
from .models import GroupDefaultAuthMethod, UserAuthMethod
from .router import Router
from .utils import clear_pending_user
from .views import StubEnrollView, StubVerifyView


class UserSelectView(View):
    def __init__(self):
        self._router = Router()

    def post(self, request: HttpRequest) -> HttpResponseBase:
        form = UserSelectForm(request.POST)
        if not form.is_valid():
            return self.get(request)

        user_identifier = form.cleaned_data["user_identifier"]
        user = User.objects.filter(username_iexact=user_identifier).first()
        if user is None:
            if self.is_valid_user_identifier(user_identifier):
                request.session[PENDING_ENROLLMENT_USER_IDENTIFIER] = user_identifier
                group_default_auth_method = GroupDefaultAuthMethod.objects.filter().first()
                if group_default_auth_method is None:
                    raise AuthMethodNotFoundError()
                request.session[VERIFICATION_METHOD_CODE] = (
                        group_default_auth_method.code
                )
                request.session[VERIFIED_METHOD_CODES] = []
                return self._router.route_try_next_method(request, StubEnrollView())

            else:
                form.add_error("user_identifier", "Username invalid.")
                return render(request, USER_SELECT_HTML, {FORM: form})

        first_verification_method = UserAuthMethod.objects.filter(
                user=user,
        ).first()
        if first_verification_method is None:
            form.add_error(None, "No auth methods found for user")
            return render(request, USER_SELECT_HTML, {FORM: form})

        request.session[PENDING_VERIFICATION_USER_KEY] = user.pk
        request.session[VERIFICATION_METHOD_CODE] = (
            first_verification_method.code,
        )
        request.session[VERIFIED_METHOD_CODES] = []
        return self._router.route_try_next_method(request, StubVerifyView())

    def get(self, request: HttpRequest):
        clear_pending_user(request)
        form = UserSelectForm()
        return render(request, USER_SELECT_HTML, {FORM: form})

    def is_valid_user_identifier(self, user_id: str):
        return False

