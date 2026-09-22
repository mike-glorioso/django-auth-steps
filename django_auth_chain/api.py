from .registry import (
    codes,
    get,
    register,
)
from .view_pair_presentation import (
    ViewPairPresentation,
)
from .views import (
    PassphraseEnrollView,
    PassphraseVerifyView,
)

passphrase_view_pair = ViewPairPresentation(
    enroll_view=PassphraseEnrollView(),
    verify_view=PassphraseVerifyView(),
)

def __all__() -> list[str]:
    return [
            str(codes),
            str(get),
            str(register),
            str(passphrase_view_pair),
    ]
