from collections.abc import Callable

from django.contrib.auth import (
    login as auth_login,
)
from django.contrib.auth.models import (
    AnonymousUser,
)
from django.forms import Form
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.utils.datastructures import MultiValueDict
from django.views import View

from .constants import (
    DJANGO_AUTH_CHAIN_USER_HOME,
    DJANGO_AUTH_CHAIN_USER_SELECT,
    NEXT_VERIFICATION_METHOD_CODE,
    VERIFIED_METHOD_CODES,
)
from .models import UserAuthMethod
from .registry import get as get_auth_method
from .utils import clear_pending_user


class VerifyView[FormVT: Form](View):
    form_class: Callable[[MultiValueDict[str, str] | None], FormVT]
    verify: Callable[[FormVT], bool]
    render: Callable[[HttpRequest, FormVT], HttpResponseBase]

    def get(self, request: HttpRequest) -> HttpResponseBase:
        request_user = request.user
        if isinstance(request_user, AnonymousUser):
            return redirect(DJANGO_AUTH_CHAIN_USER_SELECT)

        if request_user.is_authenticated:
            return redirect(DJANGO_AUTH_CHAIN_USER_HOME)

        if request.method != "POST":
            clear_pending_user(request)
            next_user_auth_method = UserAuthMethod.objects.filter(user=request_user).first()
            if next_user_auth_method is None:
                if len(request.session[VERIFIED_METHOD_CODES]):
                    return redirect(DJANGO_AUTH_CHAIN_USER_HOME)

                # no verificatiosn at all and no next method
                return redirect(DJANGO_AUTH_CHAIN_USER_SELECT)
            next_method = get_auth_method(next_user_auth_method.code)
            if next_method is None:
                # auth method not found
                return redirect(DJANGO_AUTH_CHAIN_USER_HOME)
            return next_method.enroll_and_verify.verify_view.as_view()(request)
            # return next_method.render(request, form)

        form = self.form_class(request.POST)
        if not form.is_valid():
            return self.render(request, form)

        # the actual verification
        is_invalid = self.verify(form)  # sets the form field(S) error(s) if any
        if is_invalid:
            # we should log this or something
            return self.render(request, form)

        last_method_code = request.session[NEXT_VERIFICATION_METHOD_CODE]
        if last_method_code is None:
            # I don't know how we'd get here
            form.add_error(None, "Unexpected error. Contact site administrator")
            # log this too
            return self.render(request, form)

        request.session[VERIFIED_METHOD_CODES] += last_method_code
        last_method = UserAuthMethod.objects.filter(
            user=request_user,
            code=last_method_code,
        ).first()
        if last_method is None:
            # I don't know how we'd get here either
            form.add_error(None, "Unexpected Error. Contact site administrator()")
            # should probably log this too
            return self.render(request, form)

        next_user_method = UserAuthMethod.objects.filter(
            user=request_user,
            order=last_method.order,
        ).first()
        if next_user_method is None:
            auth_login(request, request_user)
            return redirect(DJANGO_AUTH_CHAIN_USER_HOME)

        next_method = get_auth_method(next_user_method.code)
        if next_method is None:
            form.add_error(None, "Next auth method could not be found")
            return self.render(request, form)

        return next_method.enroll_and_verify.verify_view.as_view()(request)
