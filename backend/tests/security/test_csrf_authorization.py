import unittest

from backend.app.security.authorization import (
    require_drop_access,
    require_organizer,
    require_owned_private_resource,
)
from backend.app.security.csrf import derive_csrf_token, require_csrf, require_origin
from backend.app.security.errors import SecurityError
from backend.app.security.protocols import Principal
from fakes import FakeRepository


class CsrfAndAuthorizationTests(unittest.TestCase):
    def test_origin_is_exact_and_normalizes_default_port(self) -> None:
        require_origin("https://fairdrop.test:443", "https://fairdrop.test")
        for received in (None, "https://evil.test", "https://fairdrop.test.evil.test", "null"):
            with self.subTest(received=received), self.assertRaises(SecurityError):
                require_origin(received, "https://fairdrop.test")

    def test_csrf_is_bound_to_session_token(self) -> None:
        key = b"s" * 32
        token = "opaque-session-token"
        csrf = derive_csrf_token(key, token)
        require_csrf(key, token, csrf)
        for submitted in (None, csrf + "x", derive_csrf_token(key, "another-session")):
            with self.subTest(submitted=submitted), self.assertRaises(SecurityError):
                require_csrf(key, token, submitted)

    def test_participant_cannot_use_organizer_access(self) -> None:
        participant = Principal("p", "pp", "participant", "P", "UTC")
        with self.assertRaises(SecurityError) as caught:
            require_organizer(participant)
        self.assertEqual(caught.exception.status_code, 403)

    def test_organizer_is_limited_to_owned_drop_and_admin_is_explicit(self) -> None:
        repository = FakeRepository()
        organizer = Principal("o", "oo", "organizer", "O", "UTC")
        admin = Principal("a", "aa", "admin", "A", "UTC")
        repository.owned_drops.add((organizer.id, "owned"))
        self.assertEqual(require_drop_access(organizer, "owned", repository), organizer)
        with self.assertRaises(SecurityError):
            require_drop_access(organizer, "foreign", repository)
        self.assertEqual(require_drop_access(admin, "foreign", repository), admin)

    def test_foreign_private_resource_returns_404_non_disclosure(self) -> None:
        participant = Principal("p1", "p1", "participant", "P", "UTC")
        with self.assertRaises(SecurityError) as caught:
            require_owned_private_resource(participant, "p2")
        self.assertEqual(caught.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
