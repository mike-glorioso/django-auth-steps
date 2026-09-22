from dataclasses import dataclass

from .enroll_view import EnrollView
from .verify_view import VerifyView


@dataclass
class ViewPairPresentation:
    enroll_view: EnrollView
    verify_view: VerifyView
