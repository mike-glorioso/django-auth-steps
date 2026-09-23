import math

from django.contrib.auth import login as auth_login
from django.contrib.auth.models import AbstractUser
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect

from .constants import (
    DJANGO_AUTH_CHAIN_ENROLL,
    DJANGO_AUTH_CHAIN_USER_HOME,
    DJANGO_AUTH_CHAIN_USER_SELECT,
    DJANGO_AUTH_CHAIN_VERIFY,
    VERIFIED_METHOD_CODES,
)
from .errors import UserNotFoundError
from .models import UserAuthMethod
from .registry import AuthMethod, get_strategy
from .utils import clear_pending_user, get_pending_verification_user


def _first_eligible_auth_method(request_user: AbstractUser, after_order: int) -> AuthMethod | None:
    """The first configured, registered, permission-eligible method with
    order strictly greater than after_order. Doesn't touch the session -
    callers decide what to do with the result."""
    candidates = UserAuthMethod.objects.filter(
        user=request_user,
        enabled=True,
        order__gt=after_order,
    ).order_by("order")

    for candidate in candidates:
        method = get_strategy(candidate.code)
        if method is None:
            continue
        if method.permission is not None and not request_user.has_perm(method.permission):
            continue
        return method

    return None


def _highest_completed_order(request_user: AbstractUser, verified_codes: list[str]) -> int:
    if not verified_codes:
        return -1
    result = (
        UserAuthMethod.objects.filter(user=request_user, code__in=verified_codes)
        .order_by("-order")
        .values_list("order", flat=True)
        .first()
    )
    return -1 if result is None else result


def _current_method(request: HttpRequest) -> AuthMethod | None:
    """Derived, not stored: recomputed fresh from VERIFIED_METHOD_CODES
    every call, so GET is naturally idempotent."""
    request_user = get_pending_verification_user(request)
    verified_codes = request.session.get(VERIFIED_METHOD_CODES, [])
    baseline = _highest_completed_order(request_user, verified_codes)
    return _first_eligible_auth_method(request_user, after_order=baseline)


def _navigate_user_home(request: HttpRequest) -> HttpResponseBase:
    return redirect(DJANGO_AUTH_CHAIN_USER_HOME)


def _navigate_user_select(request: HttpRequest) -> HttpResponseBase:
    return redirect(DJANGO_AUTH_CHAIN_USER_SELECT)


def _finish(request: HttpRequest, is_enrolling: bool) -> HttpResponseBase:
    verified_method_codes = request.session.get(VERIFIED_METHOD_CODES, [])
    if not len(verified_method_codes):
        return _navigate_user_select(request)

    if not is_enrolling:
        user = get_pending_verification_user(request)
        auth_login(request, user)

    clear_pending_user(request)
    return _navigate_user_home(request)


class Router:
    def route_try_next_method(self, request: HttpRequest, is_enrolling: bool) -> HttpResponseBase:
        try:
            current_method = _current_method(request)
        except UserNotFoundError:
            clear_pending_user(request)
            return _navigate_user_select(request)

        if current_method is None:
            return _finish(request, is_enrolling)

        strategy = (
            current_method.enroll_strategy if is_enrolling else current_method.verify_strategy
        )
        form_handler = strategy.get_form_handler()
        request_user = get_pending_verification_user(request)
        user_auth_method = UserAuthMethod.objects.get(user=request_user, code=current_method.code)

        if not user_auth_method.throttle_is_allowed():
            form_handler.fill_form_from_none()
            wait_seconds = math.ceil(user_auth_method.throttle_delay_remaining())
            form_handler.add_error(None, f"Too many attempts. Try again in {wait_seconds}s.")
            return form_handler.render_with_form(request, strategy.html)

        if request.method != "POST":
            form_handler.fill_form_from_none()
            return form_handler.render_with_form(request, strategy.html)

        form_handler.fill_form_from_request_data(request.POST)
        if not form_handler.is_form_valid():
            return form_handler.render_with_form(request, strategy.html)

        strategy.execute(request, form_handler)
        if not form_handler.execution_state():
            user_auth_method.throttle_record_failure()
            return form_handler.render_with_form(request, strategy.html)

        user_auth_method.throttle_reset()

        verified_codes = request.session.get(VERIFIED_METHOD_CODES, [])
        verified_codes.append(current_method.code)
        request.session[VERIFIED_METHOD_CODES] = verified_codes
        return redirect(DJANGO_AUTH_CHAIN_ENROLL if is_enrolling else DJANGO_AUTH_CHAIN_VERIFY)
