#!/usr/bin/env bash
# Runs the package's tests via Django's own test runner (no pytest - see
# session notes on why: plain pytest needs pytest-django to call
# django.setup() before collection, and even with that installed,
# test_custom_user_model.py still can't share a process with the rest of
# the suite, since it needs a different AUTH_USER_MODEL than everything
# else - one Django process only ever has one).
#
# Two separate invocations, same reason: the default suite runs under the
# stock auth.User, the custom-user-model suite runs under a swapped-in
# AUTH_USER_MODEL (custom_user_app.EmailUser) to prove the package
# actually supports that, not just the default.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

# Resolved to an absolute path - a relative one confuses venv detection
# (sys.prefix ends up spelled differently than the venv it actually is,
# producing a harmless but noisy RuntimeWarning on every run).
PYTHON="$(cd .venv/bin && pwd)/python3"

echo "=== default settings (stock auth.User) ==="
DJANGO_SETTINGS_MODULE=django_auth_chain.tests.settings \
    "$PYTHON" -m django test django_auth_chain.tests.test_flow -v 2

echo
echo "=== custom user model settings (swapped AUTH_USER_MODEL) ==="
DJANGO_SETTINGS_MODULE=django_auth_chain.tests.settings_custom_user \
    "$PYTHON" -m django test django_auth_chain.tests.test_custom_user_model -v 2
