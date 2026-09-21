from collections.abc import Callable
from dataclasses import dataclass

from django.contrib.auth.models import User
from django.forms import (
    CharField,
    Form,
    PasswordInput,
)


@dataclass
class FormVerifyPresentation:
    form_class: type[Form]
    verify: Callable[[Form, User], bool]


class UserSelectForm(Form):
    user_identifier = CharField(label="Username", required=True)


class PassphraseEnrollForm(Form):
    passphrase_entry = CharField(widget=PasswordInput())
    passphrase_match = CharField(widget=PasswordInput())


class PassphraseVerifyForm(Form):
    passphrase_verify = CharField(widget=PasswordInput())
