import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from backend.app.security.config import SecurityConfig
from backend.app.security.credentials import CredentialService
from backend.app.security.errors import SecurityError
from backend.app.security.protocols import Principal
from backend.app.security.sessions import SessionService
from fakes import FakeRepository


NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def config(profile="test"):
    return SecurityConfig(
        app_profile=profile,
        public_origin="https://fairdrop.test" if profile == "normal" else "http://localhost:8080",
        session_digest_key=b"s" * 32,
        credential_digest_key=b"c" * 32,
        cookie_secure=profile == "normal",
    )


class CredentialAndSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeRepository()
        self.user = Principal("user-1", "participant-1", "participant", "A User", "UTC")
        self.repository.users[self.user.id] = self.user
        self.credentials = CredentialService(self.repository, config())
        self.sessions = SessionService(self.repository, self.credentials, config())

    def test_provision_requires_existing_user_and_stores_only_digest(self) -> None:
        with self.assertRaisesRegex(ValueError, "existing user"):
            self.credentials.provision(user_id="missing", now=NOW)
        issued = self.credentials.provision(user_id=self.user.id, now=NOW)
        self.assertNotEqual(issued.access_code, issued.record.digest)
        self.assertNotIn(issued.access_code, repr(self.repository.credentials))

    def test_normal_profile_rejects_demo_fixture_credentials(self) -> None:
        service = CredentialService(self.repository, config("normal"))
        with self.assertRaisesRegex(ValueError, "disabled"):
            service.provision(user_id=self.user.id, demo_fixture=True, now=NOW)

    def test_unknown_expired_and_revoked_credentials_share_safe_error(self) -> None:
        issued = self.credentials.provision(
            user_id=self.user.id, expires_at=NOW + timedelta(minutes=1), now=NOW
        )
        messages = []
        for code, moment in (("wrong", NOW), (issued.access_code, NOW + timedelta(minutes=2))):
            with self.assertRaises(SecurityError) as caught:
                self.credentials.verify(code, now=moment)
            messages.append((caught.exception.code, caught.exception.message))
        digest = issued.record.digest
        self.repository.credentials[digest] = replace(issued.record, revoked_at=NOW)
        with self.assertRaises(SecurityError) as caught:
            self.credentials.verify(issued.access_code, now=NOW)
        messages.append((caught.exception.code, caught.exception.message))
        self.assertEqual(len(set(messages)), 1)
        self.assertNotIn(issued.access_code, str(messages))

    def test_session_survives_service_instance_and_is_absolute_24_hours(self) -> None:
        credential = self.credentials.provision(user_id=self.user.id, now=NOW)
        issued = self.sessions.create(credential.access_code, now=NOW)
        restarted = SessionService(self.repository, self.credentials, config())
        authenticated = restarted.authenticate(issued.token, now=NOW + timedelta(hours=23))
        self.assertEqual(authenticated.principal.id, self.user.id)
        self.assertEqual(issued.record.expires_at, NOW + timedelta(hours=24))
        with self.assertRaisesRegex(SecurityError, "valid session"):
            restarted.authenticate(issued.token, now=NOW + timedelta(hours=24))

    def test_multiple_sessions_resolve_to_same_stable_principal(self) -> None:
        credential = self.credentials.provision(user_id=self.user.id, now=NOW)
        first = self.sessions.create(credential.access_code, now=NOW)
        second = self.sessions.create(credential.access_code, now=NOW)
        self.assertNotEqual(first.token, second.token)
        self.assertEqual(first.principal.id, second.principal.id)

    def test_logout_revokes_current_session_and_repeat_is_safe(self) -> None:
        credential = self.credentials.provision(user_id=self.user.id, now=NOW)
        issued = self.sessions.create(credential.access_code, now=NOW)
        self.assertTrue(self.sessions.revoke(issued.token, now=NOW))
        self.assertFalse(self.sessions.revoke(issued.token, now=NOW))
        with self.assertRaises(SecurityError):
            self.sessions.authenticate(issued.token, now=NOW)

    def test_profile_allows_only_display_name_and_iana_timezone(self) -> None:
        credential = self.credentials.provision(user_id=self.user.id, now=NOW)
        authenticated = self.sessions.authenticate(
            self.sessions.create(credential.access_code, now=NOW).token, now=NOW
        )
        updated = self.sessions.update_profile(
            authenticated, {"display_name": "  New   Name ", "timezone": "Asia/Kolkata"}
        )
        self.assertEqual(updated.display_name, "New Name")
        self.assertEqual(updated.timezone, "Asia/Kolkata")
        for patch in ({"role": "admin"}, {"grant": True}, {"timezone": "+05:30"}):
            with self.subTest(patch=patch), self.assertRaises(SecurityError):
                self.sessions.update_profile(authenticated, patch)


if __name__ == "__main__":
    unittest.main()
