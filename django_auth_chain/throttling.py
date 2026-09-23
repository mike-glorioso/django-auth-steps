from datetime import datetime, timedelta

from django.db import models
from django.db.models import F
from django.utils import timezone

# Exponential backoff, same approach as django_otp's ThrottlingMixin
# (django_otp/models.py) - not reused directly, since depending on the
# whole django_otp package just for this would be a heavy, poorly-fitting
# dependency for a package meant to be generic. Required delay after N
# consecutive failures: THROTTLE_FACTOR_SECONDS * 2**(N-1), capped at
# MAX_THROTTLE_DELAY_SECONDS - occasional typos cost a few seconds,
# sustained brute-forcing gets exponentially slower fast.
THROTTLE_FACTOR_SECONDS = 1
MAX_THROTTLE_DELAY_SECONDS = timedelta(hours=24).total_seconds()


class ThrottlingMixin(models.Model):
    throttle_failure_count: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(
        default=0
    )
    throttle_failure_at: models.DateTimeField[datetime | None, datetime | None] = (
        models.DateTimeField(null=True, blank=True, default=None)
    )

    class Meta:
        abstract = True

    def throttle_delay_remaining(self) -> float:
        """Seconds still required before another attempt is allowed. 0 or
        less means an attempt is allowed right now."""
        if self.throttle_failure_count == 0 or self.throttle_failure_at is None:
            return 0.0
        elapsed = (timezone.now() - self.throttle_failure_at).total_seconds()
        required = min(
            THROTTLE_FACTOR_SECONDS * (2 ** (self.throttle_failure_count - 1)),
            MAX_THROTTLE_DELAY_SECONDS,
        )
        return max(0.0, required - elapsed)

    def throttle_is_allowed(self) -> bool:
        return self.throttle_delay_remaining() <= 0.0

    def throttle_record_failure(self) -> None:
        # An atomic UPDATE ... SET x = x + 1, not a read-modify-write on
        # self, so concurrent failed attempts against the same row can't
        # silently lose an increment to a lost-update race.
        type(self).objects.filter(pk=self.pk).update(
            throttle_failure_count=F("throttle_failure_count") + 1,
            throttle_failure_at=timezone.now(),
        )
        self.refresh_from_db(fields=["throttle_failure_count", "throttle_failure_at"])

    def throttle_reset(self) -> None:
        if self.throttle_failure_count == 0 and self.throttle_failure_at is None:
            return
        type(self).objects.filter(pk=self.pk).update(
            throttle_failure_count=0,
            throttle_failure_at=None,
        )
        # No refresh_from_db needed here, unlike throttle_record_failure:
        # the target values are fixed (0, None), not DB-computed via F().
        self.throttle_failure_count = 0
        self.throttle_failure_at = None
