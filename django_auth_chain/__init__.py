from .view_pair_presentation import (
    ViewPairPresentation,
)
from .views import (
    PassphraseEnrollView,
    PassphraseVerifyView,
)

passphrase_view_pair = ViewPairPresentation(
    enroll_view=PassphraseEnrollView,
    verify_view=PassphraseVerifyView,
)
