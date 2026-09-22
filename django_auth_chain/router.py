from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect

from .base_view import BaseView
from .constants import (
    DJANGO_AUTH_CHAIN_USER_HOME,
    DJANGO_AUTH_CHAIN_USER_SELECT,
    PENDING_VERIFICATION_USER_KEY,
    VERIFICATION_METHOD_CODE,
    VERIFIED_METHOD_CODES,
)
from .enroll_view import EnrollView
from .errors import (
    AuthMethodNotFoundError,
    NotEnrollOrVerifyKindError,
    UserNotFoundError,
)
from .models import UserAuthMethod
from .registry import AuthMethod
from .registry import get as get_auth_method
from .verify_view import VerifyView


def _get_request_user(request: HttpRequest) -> User:
    user_or_none = User.objects.filter(request.session[PENDING_VERIFICATION_USER_KEY]).first()
    if user_or_none is None:
        raise UserNotFoundError()
    return user_or_none

def _cycle_to_next_method(request: HttpRequest) -> AuthMethod | None:
    request_user = _get_request_user(request)
    last_method_code = request.session[VERIFICATION_METHOD_CODE]
    last_user_auth_method = UserAuthMethod.objects.filter(
        user=request_user,
        code=last_method_code,
    ).first()
    if last_user_auth_method is None:
        raise Exception("test")
    next_user_auth_method = UserAuthMethod.objects.filter(
        user=request_user,
        order__gt=last_user_auth_method.order,
    ).first()
    if next_user_auth_method is None:
        return None

    next_auth_method = get_auth_method(next_user_auth_method.code)
    if next_auth_method is None:
        raise AuthMethodNotFoundError()

    request.session[VERIFIED_METHOD_CODES] = last_method_code
    request.session[VERIFICATION_METHOD_CODE] = next_auth_method.code

    return next_auth_method

def _enrollment_key_for_code(code: str) -> str:
    return code

def _verification_key_for_code(code: str) -> str:
    return code

def _confirm_code_enrollment(method_code: str, request: HttpRequest) -> bool:
    enrollment_for_code = request.session[_enrollment_key_for_code(method_code)]
    method = get_auth_method(method_code)
    if method is None:
        raise AuthMethodNotFoundError()
    return method.is_enrolled_for_code(method_code, enrollment_for_code, str(request.user.pk))

def _confirm_code_verification(method_code: str, request: HttpRequest) -> bool:
    verification_for_code = request.session[_verification_key_for_code(method_code)]
    method = get_auth_method(method_code)
    if method is None:
        raise AuthMethodNotFoundError()
    return method.has_verified_for_code(method_code, verification_for_code, str(request.user.pk))

def _navigate_user_home(request: HttpRequest) -> HttpResponseBase:
    return redirect(DJANGO_AUTH_CHAIN_USER_HOME)

def _navigate_user_select(request: HttpRequest) -> HttpResponseBase:
    return redirect(DJANGO_AUTH_CHAIN_USER_SELECT)

def _confirm_and_navigate(request: HttpRequest, view: EnrollView | VerifyView) -> HttpResponseBase:
    verified_method_codes = request.session[VERIFIED_METHOD_CODES]
    if not len(verified_method_codes):
        return _navigate_user_select(request)

    for method_code in verified_method_codes:
        if isinstance(view,EnrollView):
            if not _confirm_code_enrollment(method_code, request):
                messages.error(request, "Enrollment failed.")
                return _navigate_user_select(request)

        if isinstance(view,VerifyView):
            if not _confirm_code_verification(method_code, request):
                messages.error(request, "Verification failed.")
                return _navigate_user_select(request)

    return _navigate_user_home(request)


class Router:
    def route_try_next_method(
            self,
            request: HttpRequest,
            view: EnrollView | VerifyView
    ) -> HttpResponseBase:
        next_method = _cycle_to_next_method(request)
        if next_method is None:
            return _confirm_and_navigate(request,view)

        if isinstance(view,EnrollView):
            view = next_method.enroll_view

        else:
            view = next_method.verify_view

        assert(view is BaseView)
        if (request.method != "POST"):
            view.fill_form_from_none()
            return view.render_with_form(request)

        view.fill_form_from_request_data(request.POST)
        if not view.is_valid():
            return view.render_with_form(request)

        if isinstance(view, EnrollView):
            is_enrolled = view.enroll()
            if not is_enrolled():
                return view.render_with_form(request)

        elif isinstance(view,VerifyView):
            # the actual verificationd
            is_verified = view.verify() # sets the form field(S) error(s) if any
            if not is_verified:
                # we should log this or something
                return view.render_with_form(request)

        else:
            raise NotEnrollOrVerifyKindError()

        return self.route_try_next_method(request,view)

