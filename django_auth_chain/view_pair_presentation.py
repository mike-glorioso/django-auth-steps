from dataclasses import dataclass

from django.views import View


@dataclass
class ViewPairPresentation:
    enroll_view: type[View]
    verify_view: type[View]
