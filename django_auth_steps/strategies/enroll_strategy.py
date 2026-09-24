from .base_strategy import BaseStrategy


class EnrollStrategy(BaseStrategy):
    """Marker subclass: distinguishes an enrollment strategy from a
    verification one at the type level, so AuthMethod.enroll_strategy
    can't accidentally be assigned a VerifyStrategy instance."""
