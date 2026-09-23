from django.utils.datastructures import (
    MultiValueDict,
)

from .base_form_handler import (
    BaseFormHandler,
)
from .forms import (
    PassphraseEnrollForm,
    PassphraseVerifyForm,
    UserSelectForm,
)


class UserSelectFormHandler(BaseFormHandler):
    def fill_form_from_none(self) -> None:
        self.set_form(UserSelectForm())

    def fill_form_from_request_data(self, data: MultiValueDict[str, str]) -> None:
        self.set_form(UserSelectForm(data))


class PassphraseEnrollFormHandler(BaseFormHandler):
    def fill_form_from_none(self) -> None:
        self.set_form(PassphraseEnrollForm())

    def fill_form_from_request_data(self, data: MultiValueDict[str, str]) -> None:
        self.set_form(PassphraseEnrollForm(data))


class PassphraseVerifyFormHandler(BaseFormHandler):
    def fill_form_from_none(self) -> None:
        self.set_form(PassphraseVerifyForm())

    def fill_form_from_request_data(self, data: MultiValueDict[str, str]) -> None:
        self.set_form(PassphraseVerifyForm(data))


