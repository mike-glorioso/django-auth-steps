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


class PassphraseVerifyForm(Form):
    passphrase_verify = CharField(widget=PasswordInput())
