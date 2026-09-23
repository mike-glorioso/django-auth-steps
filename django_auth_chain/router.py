from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect

from .base_form_handler import BaseFormHandler
from .constants import (
    DJANGO_AUTH_CHAIN_ENROLL,
    DJANGO_AUTH_CHAIN_USER_HOME,
    DJANGO_AUTH_CHAIN_USER_SELECT,
    DJANGO_AUTH_CHAIN_VERIFY,
    PENDING_VERIFICATION_USER_KEY,
    VERIFICATION_METHOD_CODE,
    VERIFIED_METHOD_CODES,
)
from .errors import (
    AuthMethodNotFoundError,
    UserNotFoundError,
)
from .models import UserAuthMethod
from .registry import AuthMethod
from .registry import get as get_auth_method


def _get_request_user(request: HttpRequest) -> User:
    user_or_none = User.objects.filter(pk=request.session[PENDING_VERIFICATION_USER_KEY]).first()
    if user_or_none is None:
        raise UserNotFoundError()
    return user_or_none


def _cycle_to_next_method(request: HttpRequest, is_first_pass: bool) -> AuthMethod | None:
    request_user = _get_request_user(request)
    last_method_code = request.session[VERIFICATION_METHOD_CODE]
    last_user_auth_method = UserAuthMethod.objects.filter(
        user=request_user,
        code=last_method_code,
    ).first()
    order = -1 if last_user_auth_method is None else last_user_auth_method.order
    next_user_auth_method = UserAuthMethod.objects.filter(
        user=request_user,
        order__gt=order,
    ).first()
    if next_user_auth_method is None:
        return None

    next_auth_method = get_auth_method(next_user_auth_method.code)
    if next_auth_method is None:
        raise AuthMethodNotFoundError()

    request.session[VERIFIED_METHOD_CODES].append(last_method_code)
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
    return method.has_enrolled_for_code(method_code, enrollment_for_code, str(request.user.pk))


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


def _confirm_and_navigate(
        request: HttpRequest,
        is_enrolling: bool,
) -> HttpResponseBase:
    verified_method_codes = request.session[VERIFIED_METHOD_CODES]
    if not len(verified_method_codes):
        return _navigate_user_select(request)

    for method_code in verified_method_codes:
        if is_enrolling:
            if not _confirm_code_enrollment(method_code, request):
                messages.error(request, "Enrollment failed.")
                return _navigate_user_select(request)

        else:
            if not _confirm_code_verification(method_code, request):
                messages.error(request, "Verification failed.")
                return _navigate_user_select(request)

    return _navigate_user_home(request)


class Router:
    def route_try_next_method(
            self, request: HttpRequest,
            is_enrolling: bool,
            is_first_pass: bool,
    ) -> HttpResponseBase:
        next_method = _cycle_to_next_method(request, is_first_pass)

        if next_method is None:
            return _confirm_and_navigate(
                    request,
                    is_enrolling
            )

        if is_enrolling:
            form_handler = next_method.get_enroll_form_handler()
            html = next_method.enroll_html
        else:
            form_handler = next_method.get_verify_form_handler()
            html = next_method.verify_html
        
        assert isinstance(form_handler, BaseFormHandler)
        if request.method != "POST":
            form_handler.fill_form_from_none()
            return form_handler.render_with_form(request, html)

        form_handler.fill_form_from_request_data(request.POST)
        if not form_handler.is_form_valid():
            return form_handler.render_with_form(request, html)

        if is_enrolling:
            is_enrolled = next_method.enroll(form_handler)
            if not is_enrolled:
                return form_handler.render_with_form(request, html)

        else:
            # the actual verificationd
            is_verified = next_method.verify(form_handler)  # sets the form field(S) error(s) if any
            if not is_verified:
                # we should log this or something
                return form_handler.render_with_form(request, html)

        if is_enrolling:
            return redirect(DJANGO_AUTH_CHAIN_ENROLL)

        return redirect(DJANGO_AUTH_CHAIN_VERIFY)
