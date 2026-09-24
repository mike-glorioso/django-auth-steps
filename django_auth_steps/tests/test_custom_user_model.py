"""Only meaningful under settings_custom_user (AUTH_USER_MODEL swapped to
a username-less, email-based model) - run with:

DJANGO_SETTINGS_MODULE=django_auth_steps.tests.settings_custom_user \
    python -m django test django_auth_steps.tests.test_custom_user_model

Proves the package genuinely works with a swapped AUTH_USER_MODEL, not
just that it still compiles: django.contrib.auth.models.User is never
imported or queried anywhere in the package, and the sign-in flow works
end to end against a user model that doesn't even have a username field.
"""

from django.contrib.auth.models import Permission
from django.test import TestCase

from django_auth_steps.models import UserAuthMethod

from .custom_user_app.models import EmailUser


class CustomUserModelFlowTests(TestCase):
    def setUp(self):
        self.user: EmailUser = EmailUser.objects.create_user(
            email="mike@example.com", password="correct-horse"
        )
        # apps.py gates the built-in "passphrase" method behind
        # django_auth_steps.login_with_password - PermissionsMixin gives
        # this custom user model the same has_perm()/user_permissions
        # machinery as the stock User, so the same grant works here too.
        self.user.user_permissions.add(
            Permission.objects.get(
                codename="login_with_password", content_type__app_label="django_auth_steps"
            )
        )
        UserAuthMethod.objects.create(user=self.user, code="passphrase", order=1)

    def test_full_flow_logs_the_user_in(self):
        post_select = self.client.post(
            "/user-select/", {"user_identifier": "MIKE@example.com"}
        )
        self.assertRedirects(post_select, "/verify/")

        post_verify = self.client.post("/verify/", {"passphrase_verify": "correct-horse"})
        self.assertEqual(post_verify.status_code, 302)

        finish = self.client.get("/verify/", follow=True)
        self.assertRedirects(finish, "/")
        self.assertTrue(finish.wsgi_request.user.is_authenticated)
        self.assertEqual(finish.wsgi_request.user.email, "mike@example.com")  # type: ignore[reportUnknownMemberType, reportAttributeAccessIssue]

    def test_wrong_passphrase_does_not_authenticate(self):
        self.client.post("/user-select/", {"user_identifier": "mike@example.com"})

        response = self.client.post("/verify/", {"passphrase_verify": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertIn(b"Incorrect passphrase", response.content)
