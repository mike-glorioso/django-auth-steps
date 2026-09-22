from abc import abstractmethod

from .base_view import BaseView


class EnrollView(BaseView):
    @abstractmethod
    def enroll(self) -> bool: ...

