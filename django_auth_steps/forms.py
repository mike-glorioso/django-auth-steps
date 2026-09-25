from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.forms import (
    CharField,
    Form,
    PasswordInput,
)


class UserSelectForm(Form):
    user_identifier = CharField(label="Username", required=True)


class PassphraseEnrollForm(Form):
    passphrase_entry = CharField(widget=PasswordInput())
    passphrase_match = CharField(widget=PasswordInput())

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        entry = cleaned_data.get("passphrase_entry")
        match = cleaned_data.get("passphrase_match")
        if entry and match and entry != match:
            self.add_error("passphrase_match", "Passphrases don't match.")
        if entry:
            try:
                validate_password(entry)
            except ValidationError as exc:
                self.add_error("passphrase_entry", exc)
        return cleaned_data


class PassphraseVerifyForm(Form):
    passphrase_verify = CharField(widget=PasswordInput())
