from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase

from django_auth_chain.base_form_handler import BaseFormHandler
from django_auth_chain.constants import PENDING_VERIFICATION_USER_KEY
from django_auth_chain.form_handlers import PassphraseVerifyFormHandler
from django_auth_chain.models import UserAuthMethod
from django_auth_chain.registry import AuthMethod, register
from django_auth_chain.strategies.enroll_strategy import EnrollStrategy
from django_auth_chain.strategies.verify_strategy import VerifyStrategy


class _AlwaysSucceedsMixin:
    """Test-only second step: reuses the passphrase form/template but
    always succeeds, regardless of what's submitted - just exercises
    chain sequencing, not any real verification logic."""

    @property
    def html(self) -> str:
        return "passphrase_verify.html"

    def get_form_handler(self) -> BaseFormHandler:
        return PassphraseVerifyFormHandler()

    def execute(self, request: HttpRequest, form_handler: BaseFormHandler) -> None:
        form_handler.set_execution_state(True)


class _AlwaysSucceedsEnrollStrategy(_AlwaysSucceedsMixin, EnrollStrategy):
    pass


class _AlwaysSucceedsVerifyStrategy(_AlwaysSucceedsMixin, VerifyStrategy):
    pass


class OneStepPassphraseFlowTests(TestCase):
    def setUp(self):
        self.user: User = User.objects.create_user(username="mike", password="correct-horse")
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
    SECOND_STEP_CODE = "test-second-step"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        register(
            AuthMethod(
                code=cls.SECOND_STEP_CODE,
                label="Test second step",
                permission=None,
                is_enrolled=lambda user: True,
                enroll_strategy=_AlwaysSucceedsEnrollStrategy(),
                verify_strategy=_AlwaysSucceedsVerifyStrategy(),
            )
        )

    def setUp(self):
        self.user: User = User.objects.create_user(username="mike", password="correct-horse")
        UserAuthMethod.objects.create(user=self.user, code="passphrase", order=1)
        UserAuthMethod.objects.create(user=self.user, code=self.SECOND_STEP_CODE, order=2)

    def test_first_step_alone_does_not_authenticate(self):
        self.client.post("/user-select/", {"user_identifier": "mike"})
        post_verify = self.client.post("/verify/", {"passphrase_verify": "correct-horse"})
        self.assertRedirects(post_verify, "/verify/")

        # completing step one should land back on verify for step two, not home
        second_step = self.client.get("/verify/")
        self.assertEqual(second_step.status_code, 200)
        self.assertFalse(second_step.wsgi_request.user.is_authenticated)

    def test_both_steps_together_authenticate(self):
        self.client.post("/user-select/", {"user_identifier": "mike"})
        self.client.post("/verify/", {"passphrase_verify": "correct-horse"})
        self.client.post("/verify/", {"passphrase_verify": "irrelevant-for-this-step"})

        finish = self.client.get("/verify/", follow=True)
        self.assertRedirects(finish, "/")
        self.assertTrue(finish.wsgi_request.user.is_authenticated)
