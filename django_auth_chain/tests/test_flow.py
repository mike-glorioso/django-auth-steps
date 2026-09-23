from datetime import timedelta

from django.contrib.auth.models import Permission, User
from django.http import HttpRequest
from django.test import TestCase
from django.utils import timezone

from django_auth_chain.base_form_handler import BaseFormHandler
from django_auth_chain.constants import PENDING_VERIFICATION_USER_KEY
from django_auth_chain.form_handlers import PassphraseVerifyFormHandler
from django_auth_chain.models import UserAuthMethod
from django_auth_chain.registry import AuthMethod
from django_auth_chain.registry import register_strategy as register
from django_auth_chain.strategies.enroll_strategy import EnrollStrategy
from django_auth_chain.strategies.verify_strategy import VerifyStrategy


def _grant_passphrase_permission(user: User) -> None:
    # apps.py registers the built-in "passphrase" method via
    # register_with_permission(), which gates it behind
    # django_auth_chain.login_with_password - so any test user meant to
    # actually reach the passphrase step needs this granted explicitly.
    user.user_permissions.add(
        Permission.objects.get(
            codename="login_with_password", content_type__app_label="django_auth_chain"
        )
    )


class _AlwaysFailsMixin:
    """Deny-by-default test double for a generic step. This is the
    baseline for any test that doesn't specifically need the step to
    pass - a double that silently succeeds by default risks tests
    passing vacuously even when the real logic under test is broken.
    Use _AlwaysSucceedsMixin below only where a test intentionally
    needs a step to succeed."""

    @property
    def html(self) -> str:
        return "passphrase_verify.html"

    def get_form_handler(self) -> BaseFormHandler:
        return PassphraseVerifyFormHandler()

    def execute(self, request: HttpRequest, form_handler: BaseFormHandler) -> None:
        form_handler.set_execution_state(False)


class _AlwaysSucceedsMixin:
    """Deliberately, explicitly allowing - only for tests that need a
    step to actually pass."""

    @property
    def html(self) -> str:
        return "passphrase_verify.html"

    def get_form_handler(self) -> BaseFormHandler:
        return PassphraseVerifyFormHandler()

    def execute(self, request: HttpRequest, form_handler: BaseFormHandler) -> None:
        form_handler.set_execution_state(True)


class _AlwaysFailsEnrollStrategy(_AlwaysFailsMixin, EnrollStrategy):
    pass


class _AlwaysFailsVerifyStrategy(_AlwaysFailsMixin, VerifyStrategy):
    pass


class _AlwaysSucceedsEnrollStrategy(_AlwaysSucceedsMixin, EnrollStrategy):
    pass


class _AlwaysSucceedsVerifyStrategy(_AlwaysSucceedsMixin, VerifyStrategy):
    pass


class OneStepPassphraseFlowTests(TestCase):
    def setUp(self):
        self.user: User = User.objects.create_user(username="mike", password="correct-horse")
        _grant_passphrase_permission(self.user)
        UserAuthMethod.objects.create(user=self.user, code="passphrase", order=1)

    def test_full_flow_logs_the_user_in(self):
        get_select = self.client.get("/user-select/")
        self.assertEqual(get_select.status_code, 200)

        post_select = self.client.post("/user-select/", {"user_identifier": "mike"})
        self.assertRedirects(post_select, "/verify/")

        get_verify = self.client.get("/verify/")
        self.assertEqual(get_verify.status_code, 200)
        self.assertFalse(get_verify.wsgi_request.user.is_authenticated)

        # with only one configured step, the chain completes on this POST,
        # so /verify/ already redirects home on the very next fetch -
        # assertRedirects' default follow-check expects a 200, which
        # doesn't hold here, so check the redirect chain manually instead
        post_verify = self.client.post("/verify/", {"passphrase_verify": "correct-horse"})
        self.assertEqual(post_verify.status_code, 302)
        self.assertEqual(post_verify["Location"], "/verify/")

        finish = self.client.get("/verify/", follow=True)
        self.assertRedirects(finish, "/")
        self.assertTrue(finish.wsgi_request.user.is_authenticated)
        self.assertEqual(finish.wsgi_request.user.username, "mike")  # type: ignore[reportUnknownMemberType, reportAttributeAccessIssue]  # narrowed by the is_authenticated assertion above; django-stubs types request.user as AbstractBaseUser | AnonymousUser

    def test_wrong_passphrase_does_not_authenticate(self):
        self.client.post("/user-select/", {"user_identifier": "mike"})

        response = self.client.post("/verify/", {"passphrase_verify": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertIn(b"Incorrect passphrase", response.content)

    def test_unknown_username_gives_generic_error_and_no_session_state(self):
        response = self.client.post("/user-select/", {"user_identifier": "nobody"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid username", response.content)
        self.assertNotIn(PENDING_VERIFICATION_USER_KEY, self.client.session)


class TwoStepFlowTests(TestCase):
    DENY_SECOND_STEP_CODE = "test-second-step-deny"
    ALLOW_SECOND_STEP_CODE = "test-second-step-allow"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        register(
            AuthMethod(
                code=cls.DENY_SECOND_STEP_CODE,
                label="Test second step (deny)",
                permission=None,
                is_enrolled=lambda user: True,
                enroll_strategy=_AlwaysFailsEnrollStrategy(),
                verify_strategy=_AlwaysFailsVerifyStrategy(),
            )
        )
        register(
            AuthMethod(
                code=cls.ALLOW_SECOND_STEP_CODE,
                label="Test second step (allow)",
                permission=None,
                is_enrolled=lambda user: True,
                enroll_strategy=_AlwaysSucceedsEnrollStrategy(),
                verify_strategy=_AlwaysSucceedsVerifyStrategy(),
            )
        )

    def setUp(self):
        self.user: User = User.objects.create_user(username="mike", password="correct-horse")
        _grant_passphrase_permission(self.user)
        UserAuthMethod.objects.create(user=self.user, code="passphrase", order=1)

    def test_first_step_alone_does_not_authenticate(self):
        # deny by default here: this test never submits the second step,
        # so whether it would pass or fail is irrelevant to what's checked
        UserAuthMethod.objects.create(user=self.user, code=self.DENY_SECOND_STEP_CODE, order=2)

        self.client.post("/user-select/", {"user_identifier": "mike"})
        post_verify = self.client.post("/verify/", {"passphrase_verify": "correct-horse"})
        self.assertRedirects(post_verify, "/verify/")

        # completing step one should land back on verify for step two, not home
        second_step = self.client.get("/verify/")
        self.assertEqual(second_step.status_code, 200)
        self.assertFalse(second_step.wsgi_request.user.is_authenticated)

    def test_both_steps_together_authenticate(self):
        # intentionally allow here: this test's whole point is proving
        # that completing every step authenticates the user
        UserAuthMethod.objects.create(user=self.user, code=self.ALLOW_SECOND_STEP_CODE, order=2)

        self.client.post("/user-select/", {"user_identifier": "mike"})
        self.client.post("/verify/", {"passphrase_verify": "correct-horse"})
        self.client.post("/verify/", {"passphrase_verify": "irrelevant-for-this-step"})

        finish = self.client.get("/verify/", follow=True)
        self.assertRedirects(finish, "/")
        self.assertTrue(finish.wsgi_request.user.is_authenticated)

    def test_second_step_failure_does_not_authenticate(self):
        # the gap the old shared always-succeeds double couldn't catch:
        # a later step failing must still block the chain, even after
        # an earlier step genuinely succeeded
        UserAuthMethod.objects.create(user=self.user, code=self.DENY_SECOND_STEP_CODE, order=2)

        self.client.post("/user-select/", {"user_identifier": "mike"})
        self.client.post("/verify/", {"passphrase_verify": "correct-horse"})

        response = self.client.post("/verify/", {"passphrase_verify": "irrelevant-for-this-step"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class ThrottlingTests(TestCase):
    def setUp(self):
        self.user: User = User.objects.create_user(username="mike", password="correct-horse")
        _grant_passphrase_permission(self.user)
        UserAuthMethod.objects.create(user=self.user, code="passphrase", order=1)

    def test_immediate_retry_after_failure_is_throttled(self):
        self.client.post("/user-select/", {"user_identifier": "mike"})

        first = self.client.post("/verify/", {"passphrase_verify": "wrong"})
        self.assertIn(b"Incorrect passphrase", first.content)

        # THROTTLE_FACTOR_SECONDS=1, so the very next attempt, made well
        # under a second later, must be blocked - even with the right
        # passphrase this time, since the throttle check runs before the
        # real check
        second = self.client.post("/verify/", {"passphrase_verify": "correct-horse"})
        self.assertEqual(second.status_code, 200)
        self.assertIn(b"Too many attempts", second.content)
        self.assertFalse(second.wsgi_request.user.is_authenticated)

    def test_success_after_delay_has_passed_authenticates_and_resets_throttle(self):
        self.client.post("/user-select/", {"user_identifier": "mike"})
        self.client.post("/verify/", {"passphrase_verify": "wrong"})

        user_auth_method = UserAuthMethod.objects.get(user=self.user, code="passphrase")
        self.assertEqual(user_auth_method.throttle_failure_count, 1)
        self.assertIsNotNone(user_auth_method.throttle_failure_at)

        # simulate the required delay having already passed, rather than
        # actually sleeping in a test
        UserAuthMethod.objects.filter(pk=user_auth_method.pk).update(
            throttle_failure_at=timezone.now() - timedelta(seconds=10)
        )

        response = self.client.post("/verify/", {"passphrase_verify": "correct-horse"}, follow=True)
        self.assertRedirects(response, "/")
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        user_auth_method.refresh_from_db()
        self.assertEqual(user_auth_method.throttle_failure_count, 0)
        self.assertIsNone(user_auth_method.throttle_failure_at)
