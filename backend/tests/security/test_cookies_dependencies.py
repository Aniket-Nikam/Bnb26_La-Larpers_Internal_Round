import unittest
from types import SimpleNamespace

import backend.app.security.dependencies as dependency_module
from backend.app.security.config import SecurityConfig
from backend.app.security.cookies import SessionCookiePolicy
from backend.app.security.credentials import CredentialService
from backend.app.security.dependencies import (
    SecurityDependencies,
    configure_security_dependencies,
    enforce_limit,
    get_principal,
    require_drop_access,
    require_organizer,
)
from backend.app.security.errors import SecurityError
from backend.app.security.limits import LimitAction, RateLimiter
from backend.app.security.protocols import Principal
from backend.app.security.sessions import SessionService
from fakes import FakeRepository, RecordingRedis


def config():
    return SecurityConfig(
        "test",
        "http://localhost:8080",
        b"s" * 32,
        b"c" * 32,
        False,
        trusted_proxy_cidrs=("10.42.0.10/32",),
    )


class CookieAndDependencyTests(unittest.TestCase):
    def tearDown(self) -> None:
        dependency_module._reset_security_dependencies_for_tests()

    def test_cookie_policy_is_httponly_lax_and_absolute(self) -> None:
        policy = SessionCookiePolicy.from_config(config())
        self.assertTrue(policy.httponly)
        self.assertFalse(policy.secure)
        self.assertEqual(policy.samesite, "lax")
        self.assertEqual(policy.path, "/")
        self.assertEqual(policy.max_age, 86_400)

    def test_stable_helpers_use_durable_service_and_exact_proxy_policy(self) -> None:
        repository = FakeRepository()
        principal = Principal("organizer-1", "org-1", "organizer", "Organizer", "UTC")
        repository.users[principal.id] = principal
        repository.owned_drops.add((principal.id, "drop-1"))
        credentials = CredentialService(repository, config())
        sessions = SessionService(repository, credentials, config())
        limiter_backend = RecordingRedis()
        configure_security_dependencies(
            SecurityDependencies(sessions, repository, RateLimiter(limiter_backend, b"k" * 32), config())
        )
        issued_credential = credentials.provision(user_id=principal.id)
        issued_session = sessions.create(issued_credential.access_code)
        request = SimpleNamespace(
            cookies={config().cookie_name: issued_session.token},
            headers={"x-forwarded-for": "198.51.100.8"},
            client=SimpleNamespace(host="10.42.0.10"),
            state=SimpleNamespace(),
        )
        resolved = get_principal(request)
        self.assertEqual(require_organizer(request), principal)
        self.assertEqual(require_drop_access(resolved, "drop-1"), principal)
        enforce_limit(request, resolved, LimitAction.ENTRY_WRITE)
        self.assertNotIn("198.51.100.8", repr(limiter_backend.calls))

    def test_helpers_fail_closed_before_bootstrap_configuration(self) -> None:
        request = SimpleNamespace(cookies={}, headers={}, client=SimpleNamespace(host="127.0.0.1"))
        with self.assertRaises(SecurityError) as caught:
            get_principal(request)
        self.assertEqual(caught.exception.code, "INTERNAL_ERROR")


if __name__ == "__main__":
    unittest.main()
