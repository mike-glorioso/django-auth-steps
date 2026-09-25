# django_auth_steps

A pluggable, multi-step authentication orchestrator for Django. Each
authentication method (password, TOTP, email OTP, ...) is registered as
an `AuthMethod` with its own enroll/verify strategy; the app routes
users through whichever methods apply to them without hardcoding a
single login flow.

## Usage

```python
INSTALLED_APPS = [
    ...,
    "django_auth_steps",
]
```

```python
# urls.py
urlpatterns = [
    path("auth/", include("django_auth_steps.urls")),
]
```

A `passphrase` method (standard Django password verification) is
registered automatically on app startup via
`django_auth_steps.apps.DjangoAuthStepsConfig.ready()`. Additional
methods register themselves the same way — see
`django_auth_steps/passphrase_strategy.py` for the pattern:

```python
from django_auth_steps.registry import AuthMethod, register_strategy

register_strategy(
    AuthMethod(
        code="my-method",
        label="My Method",
        permission=None,  # or a permission string gating this method
        is_enrolled=lambda user: ...,
        enroll_strategy=MyEnrollStrategy(),
        verify_strategy=MyVerifyStrategy(),
    )
)
```

An `EnrollStrategy`/`VerifyStrategy` pair defines the template to render
and what `execute()` does with the submitted form; `django_auth_steps`
handles routing users to the right one, negative-testing (unregistered
methods fail clearly rather than silently), and rate-limiting.

## Status

The built-in `passphrase` method supports both verifying an existing
password and self-service enrollment (`PassphraseEnrollStrategy` sets a
new password via Django's own `validate_password()` and confirmation
matching).

Extracted from an internal project (glotronic.net), with full commit
history preserved via `git subtree split`.

## License

BSD-3-Clause — see [LICENSE](LICENSE).
