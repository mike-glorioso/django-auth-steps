
from django.utils.datastructures import MultiValueDict

from .base_form_handler import BaseFormHandler
from .forms import UserSelectForm

class UserSelectFormHandler(BaseFormHandler):
    @abstractmethod
    def fill_form_from_none(self) -> None:
        return UserSelectForm()

    @abstractmethod
    def fill_form_from_request_data(self, data: MultiValueDict[str, str]) -> None:
        return UserSelectForm(data)

