from django.contrib.auth.models import (
    AbstractUser,
    User,
)
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from .constants import (
    DJANGO_AUTH_CHAIN_ENROLL,
    DJANGO_AUTH_CHAIN_USER_HOME,
    DJANGO_AUTH_CHAIN_VERIFY,
    NEXT_VERIFICATION_METHOD_CODE,
    PENDING_ENROLLMENT_USER_IDENTIFIER,
    PENDING_VERIFICATION_USER_KEY,
    VERIFIED_METHOD_CODES,
)
from .forms import (
    UserSelectForm,
)
from .models import UserAuthMethod
from .utils import clear_pending_user


class UserSelectView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        if isinstance(request.user, AbstractUser):
            return redirect(DJANGO_AUTH_CHAIN_USER_HOME)

        if request.method == "POST":
            form = UserSelectForm(request.POST)
            if form.is_valid():
                user_identifier = form.cleaned_data["user_identifier"]
                user = User.objects.filter(username_iexact=user_identifier).first()
                if user is None:
                    if self.is_valid_user_identifier(user_identifier):
                        request.session[PENDING_ENROLLMENT_USER_IDENTIFIER] = user_identifier
                        return redirect(DJANGO_AUTH_CHAIN_ENROLL)

                    else:
                        form.add_error("user_identifier", "Username invalid.")
                        return render(request, "user_select.html", {"form": form})

                else:
                    first_verification_method = UserAuthMethod.objects.filter(
                        user=user,
                    ).first()
                    if first_verification_method is None:
                        form.add_error(None, "No auth methods found for user")
                        return render(request, "user_select.html", {"form": form})

                    request.session[PENDING_VERIFICATION_USER_KEY] = user.pk
                    request.session[NEXT_VERIFICATION_METHOD_CODE] = (
                        first_verification_method.code,
                    )
                    request.session[VERIFIED_METHOD_CODES] = []
                    return redirect(DJANGO_AUTH_CHAIN_VERIFY)

            else:
                clear_pending_user(request)
                form = UserSelectForm()
        else:
            clear_pending_user(request)
            form = UserSelectForm()

        return render(request, "user_select.html", {"form": form})

    def is_valid_user_identifier(self, user_id: str):
        return False
