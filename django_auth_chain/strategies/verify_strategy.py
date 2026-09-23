from .base_strategy import BaseStrategy


class VerifyStrategy(BaseStrategy):
    """Marker subclass: distinguishes a verification strategy from an
    enrollment one at the type level, so AuthMethod.verify_strategy
    can't accidentally be assigned an EnrollStrategy instance."""
