from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.http import HttpRequest
from django.test import TestCase
from django.utils import timezone

from django_auth_steps import registry
from django_auth_steps.base_form_handler import BaseFormHandler
from django_auth_steps.constants import PENDING_VERIFICATION_USER_KEY
from django_auth_steps.form_handlers import PassphraseVerifyFormHandler
from django_auth_steps.models import UserAuthMethod
from django_auth_steps.passphrase_strategy import (
    PassphraseEnrollStrategy,
    PassphraseVerifyStrategy,
    register_with_permission,
    register_without_permission,
)
from django_auth_steps.registry import AuthMethod
from django_auth_steps.registry import register_strategy as register
from django_auth_steps.strategies.enroll_strategy import EnrollStrategy
from django_auth_steps.strategies.verify_strategy import VerifyStrategy


def _grant_passphrase_permission(user: User) -> None:
    # apps.py registers the built-in "passphrase" method via
    # register_with_permission(), which gates it behind
    # django_auth_steps.login_with_password - so any test user meant to
    # actually reach the passphrase step needs this granted explicitly.
    user.user_permissions.add(
        Permission.objects.get(
            codename="login_with_password", content_type__app_label="django_auth_steps"
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

    def test_existing_user_with_no_configured_methods_gets_the_same_generic_error(self):
        # same anti-enumeration property as the unknown-username case
        # above, for a user that genuinely exists but has zero
        # UserAuthMethod rows at all - a real username shouldn't be
        # distinguishable from a fake one by response content
        User.objects.create_user(username="nobody-configured", password="x")

        response = self.client.post("/user-select/", {"user_identifier": "nobody-configured"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid username", response.content)
        self.assertNotIn(PENDING_VERIFICATION_USER_KEY, self.client.session)


class OneStepPassphraseEnrollFlowTests(TestCase):
    def setUp(self):
        self.user: User = User.objects.create_user(username="mike", password="old-horse")
        _grant_passphrase_permission(self.user)
        UserAuthMethod.objects.create(user=self.user, code="passphrase", order=1)
        self.client.post("/user-select/", {"user_identifier": "mike"})

    def test_full_flow_sets_the_new_passphrase(self):
        get_enroll = self.client.get("/enroll/")
        self.assertEqual(get_enroll.status_code, 200)

        post_enroll = self.client.post(
            "/enroll/",
            {
                "passphrase_entry": "correct-horse-battery-staple",
                "passphrase_match": "correct-horse-battery-staple",
            },
        )
        self.assertEqual(post_enroll.status_code, 302)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("correct-horse-battery-staple"))
        self.assertFalse(self.user.check_password("old-horse"))

    def test_mismatched_passphrases_are_rejected_and_nothing_changes(self):
        response = self.client.post(
            "/enroll/",
            {
                "passphrase_entry": "correct-horse-battery-staple",
                "passphrase_match": "different-value-entirely",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"don&#x27;t match", response.content)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("old-horse"))

    def test_weak_passphrase_is_rejected_by_django_validators(self):
        response = self.client.post(
            "/enroll/",
            {"passphrase_entry": "12345678", "passphrase_match": "12345678"},
        )
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("old-horse"))


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


class PassphraseRegistrationTests(TestCase):
    """Unit-level: what AuthMethod register_with_permission()/
    register_without_permission() actually build. Can't exercise these
    against the real "passphrase" code through the module-level
    registry as-is - apps.py's ready() already registers it there once
    per process, and register_strategy() is first-write-wins - so each
    test clears the registry for its own duration and restores it
    afterward (mock.patch.dict always restores the original content on
    exit, regardless of the clear=True given here)."""

    def test_register_without_permission_registers_an_ungated_method(self):
        with mock.patch.dict(registry._methods, {}, clear=True):  # type: ignore[reportPrivateUsage]  # deliberate: isolating the module-level registry for this test only
            register_without_permission()
            method = registry.get_strategy("passphrase")

        assert method is not None
        self.assertEqual(method.code, "passphrase")
        self.assertIsNone(method.permission)
        self.assertIsInstance(method.enroll_strategy, PassphraseEnrollStrategy)
        self.assertIsInstance(method.verify_strategy, PassphraseVerifyStrategy)

    def test_register_with_permission_registers_a_gated_method(self):
        with mock.patch.dict(registry._methods, {}, clear=True):  # type: ignore[reportPrivateUsage]  # deliberate: isolating the module-level registry for this test only
            register_with_permission()
            method = registry.get_strategy("passphrase")

        assert method is not None
        self.assertEqual(method.code, "passphrase")
        self.assertEqual(method.permission, "django_auth_steps.login_with_password")
        self.assertIsInstance(method.enroll_strategy, PassphraseEnrollStrategy)
        self.assertIsInstance(method.verify_strategy, PassphraseVerifyStrategy)

    def test_is_enrolled_reflects_has_usable_password_for_both_variants(self):
        user_with_password = User.objects.create_user(username="has-pw", password="x")
        user_without_password = User.objects.create_user(username="no-pw")
        user_without_password.set_unusable_password()
        user_without_password.save()

        for register_fn in (register_without_permission, register_with_permission):
            with mock.patch.dict(registry._methods, {}, clear=True):  # type: ignore[reportPrivateUsage]  # deliberate: isolating the module-level registry for this test only
                register_fn()
                method = registry.get_strategy("passphrase")
                assert method is not None
                self.assertTrue(method.is_enrolled(user_with_password))
                self.assertFalse(method.is_enrolled(user_without_password))

    def test_register_strategy_is_first_write_wins(self):
        # what makes calling register_with_permission()/
        # register_without_permission() from apps.py's ready() safe
        # even if ready() ever runs more than once in a process
        with mock.patch.dict(registry._methods, {}, clear=True):  # type: ignore[reportPrivateUsage]  # deliberate: isolating the module-level registry for this test only
            first = AuthMethod(
                code="dup-test",
                label="First",
                permission=None,
                is_enrolled=lambda user: True,
                enroll_strategy=PassphraseEnrollStrategy(),
                verify_strategy=PassphraseVerifyStrategy(),
            )
            second = AuthMethod(
                code="dup-test",
                label="Second",
                permission=None,
                is_enrolled=lambda user: True,
                enroll_strategy=PassphraseEnrollStrategy(),
                verify_strategy=PassphraseVerifyStrategy(),
            )
            self.assertTrue(register(first))
            self.assertFalse(register(second))

            method = registry.get_strategy("dup-test")
            assert method is not None
            self.assertEqual(method.label, "First")


class PassphrasePermissionGateTests(TestCase):
    """Proves the login_with_password gate that apps.py's real
    register_with_permission() wires up for "passphrase" actually
    blocks an ungranted user - every other test class's setUp calls
    _grant_passphrase_permission() before expecting passphrase sign-in
    to work; this is the negative case proving that grant is load-
    bearing, not just cargo-culted."""

    def setUp(self):
        self.user: User = User.objects.create_user(username="mike", password="correct-horse")
        # deliberately not granted login_with_password
        UserAuthMethod.objects.create(user=self.user, code="passphrase", order=1)

    def test_user_without_permission_cannot_reach_the_passphrase_step(self):
        self.client.post("/user-select/", {"user_identifier": "mike"})

        response = self.client.get("/verify/", follow=True)

        self.assertRedirects(response, "/user-select/")
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class UnregisteredMethodCodeTests(TestCase):
    """What happens when a user's only configured UserAuthMethod row
    points at a code nothing has registered in the strategy registry
    (a typo'd code, or a project that installed django_auth_steps but
    never actually called register_strategy() for anything).

    Documents current behavior, not necessarily endorses it: router.py's
    _first_eligible_auth_method() treats an unregistered code exactly
    like a permission-ineligible one (silently skipped), so this ends up
    indistinguishable from "no configured methods at all" - a silent
    redirect to user-select, no error message, no log line. That's
    arguably not clear enough for an operator to diagnose (a genuine
    misconfiguration looks identical to a user who never had a method
    assigned) - flagging as a real gap, not asserting it's fine."""

    def setUp(self):
        self.user: User = User.objects.create_user(username="mike", password="correct-horse")
        _grant_passphrase_permission(self.user)
        UserAuthMethod.objects.create(user=self.user, code="totally-unregistered-code", order=1)

    def test_user_select_still_succeeds_since_the_row_exists_and_is_enabled(self):
        # has_any_method only checks that an enabled UserAuthMethod row
        # exists for this user - it doesn't check the row's code is
        # actually registered anywhere, so this step passes even though
        # the user can never actually complete verification. /verify/
        # itself immediately redirects again (next test), so this can't
        # use assertRedirects' default auto-follow-to-200 - same reason
        # test_full_flow_logs_the_user_in checks the redirect manually.
        response = self.client.post("/user-select/", {"user_identifier": "mike"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/verify/")

    def test_verify_silently_bounces_back_to_user_select(self):
        self.client.post("/user-select/", {"user_identifier": "mike"})

        response = self.client.get("/verify/", follow=True)

        self.assertRedirects(response, "/user-select/")
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        # no error message anywhere in the response - indistinguishable
        # from a plain, first-time visit to user-select
        self.assertNotIn(b"Invalid username", response.content)
        self.assertNotIn(b"Too many attempts", response.content)

    def test_skipping_an_unregistered_code_logs_a_warning(self):
        # the gap this class documents: an unregistered code is
        # currently indistinguishable from a normal, expected skip
        # (a permission-ineligible candidate) anywhere a developer or
        # operator could see it. Not yet true - this is the acceptance
        # test for the fix that follows.
        self.client.post("/user-select/", {"user_identifier": "mike"})

        with self.assertLogs("django_auth_steps", level="WARNING") as logs:
            self.client.get("/verify/")

        self.assertTrue(
            any("totally-unregistered-code" in message for message in logs.output),
            f"expected a warning naming the unregistered code, got: {logs.output}",
        )


class _RecordsOnDisplayVerifyStrategy(_AlwaysSucceedsMixin, VerifyStrategy):
    def __init__(self) -> None:
        self.on_display_calls = 0

    def on_display(self, request: HttpRequest, form_handler: BaseFormHandler) -> None:
        self.on_display_calls += 1


class OnDisplayHookTests(TestCase):
    """on_display() exists so a strategy like email-OTP can send a code
    before its form is shown - proving it fires exactly where it should
    (a genuine GET) and nowhere else (throttled, or POST) is what makes
    that safe to build on."""

    CODE = "test-on-display"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.strategy = _RecordsOnDisplayVerifyStrategy()
        register(
            AuthMethod(
                code=cls.CODE,
                label="Test on_display",
                permission=None,
                is_enrolled=lambda user: True,
                enroll_strategy=_AlwaysSucceedsEnrollStrategy(),
                verify_strategy=cls.strategy,
            )
        )

    def setUp(self):
        self.strategy.on_display_calls = 0
        self.user: User = User.objects.create_user(username="mike", password="x")
        UserAuthMethod.objects.create(user=self.user, code=self.CODE, order=1)
        self.client.post("/user-select/", {"user_identifier": "mike"})

    def test_on_display_fires_on_a_genuine_get(self):
        self.client.get("/verify/")
        self.assertEqual(self.strategy.on_display_calls, 1)

    def test_on_display_does_not_fire_on_post(self):
        self.client.post("/verify/", {})
        self.assertEqual(self.strategy.on_display_calls, 0)

    def test_on_display_does_not_fire_while_throttled(self):
        user_auth_method = UserAuthMethod.objects.get(user=self.user, code=self.CODE)
        user_auth_method.throttle_record_failure()

        self.client.get("/verify/")

        self.assertEqual(self.strategy.on_display_calls, 0)

    def test_passphrase_default_on_display_is_a_no_op(self):
        # PassphraseVerifyStrategy doesn't override on_display - this
        # just proves the base no-op doesn't blow up or do anything
        # observable, so passphrase (and any other pre-existing
        # strategy) is unaffected by this hook's addition.
        strategy = PassphraseVerifyStrategy()
        request = HttpRequest()
        self.assertIsNone(strategy.on_display(request, PassphraseVerifyFormHandler()))
