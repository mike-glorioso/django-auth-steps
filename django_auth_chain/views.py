from collections.abc import Callable

from django.contrib import messages
from django.contrib.auth import (
    logout as auth_logout,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import (
    AbstractUser,
)
from django.forms import Form
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.datastructures import MultiValueDict
from django.views import View

from .constants import DJANGO_AUTH_CHAIN_USER_HOME
from .forms import (
    PassphraseEnrollForm,
    PassphraseVerifyForm,
)
from .verify_view import VerifyView
from .view_pair_presentation import (
    ViewPairPresentation,
)


class EnrollView[FormT: Form](View):
    form_class: Callable[[MultiValueDict[str, str] | None], FormT]
    verify: Callable[[FormT], bool]
    render: Callable[[HttpRequest, FormT], HttpResponse]

    @login_required
    def get(self, request: HttpRequest) -> HttpResponse:
        user = request.user
        if isinstance(user, AbstractUser):
            return redirect(DJANGO_AUTH_CHAIN_USER_HOME)

        if request.method == "POST":
            form = self.form_class(request.POST)
            if form.is_valid():
                if self.verify(form):
                    messages.success(request, "Passphrase authentication is now enabled.")
                    return redirect(DJANGO_AUTH_CHAIN_USER_HOME)
                form.add_error("passphrase_match", "Passphrases do not match.")
        else:
            form = self.form_class(None)

        return self.render(request, form)


class PassphraseEnrollView(EnrollView[PassphraseEnrollForm]):
    @staticmethod
    def passphrase_form_class(data: MultiValueDict[str, str]):
        return PassphraseEnrollForm(data)

    @staticmethod
    def passphrase_verify(form: PassphraseEnrollForm):
        return False

    @staticmethod
    def passphrase_render(request: HttpRequest, form: PassphraseEnrollForm):
        return render(request, "passphrase_enroll.html", {"form": form})

    form_class: Callable[[MultiValueDict[str, str]], PassphraseEnrollForm] = passphrase_form_class
    verify = passphrase_verify
    render = passphrase_render


class PassphraseVerifyView(VerifyView[PassphraseVerifyForm]):
    @staticmethod
    def passphrase_form_class(data: MultiValueDict[str, str] | None) -> PassphraseVerifyForm:
        return PassphraseVerifyForm(data)

    @staticmethod
    def passphrase_verify(form: PassphraseVerifyForm):
        return False

    @staticmethod
    def passphrase_render(request: HttpRequest, form: PassphraseVerifyForm):
        return render(request, "passphrase_verify.html", {"form": form})

    form_class = passphrase_form_class
    verify = passphrase_verify
    render = passphrase_render


class LogoutView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        auth_logout(request)
        return redirect(":home")


passphrase_view_pair = ViewPairPresentation(
    enroll_view=PassphraseEnrollView,
    verify_view=PassphraseVerifyView,
)
