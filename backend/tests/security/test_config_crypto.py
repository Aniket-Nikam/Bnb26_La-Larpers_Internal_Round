import unittest

from backend.app.security.config import SecurityConfig
from backend.app.security.crypto import credential_digest, csrf_token, session_digest


class ConfigAndCryptoTests(unittest.TestCase):
    def test_normal_profile_requires_https_secure_cookie_and_real_keys(self) -> None:
        base = {
            "APP_PROFILE": "normal",
            "PUBLIC_ORIGIN": "https://fairdrop.test",
            "COOKIE_SECURE": "true",
            "SESSION_DIGEST_KEY": "s" * 40,
            "CREDENTIAL_DIGEST_KEY": "c" * 40,
        }
        config = SecurityConfig.from_env(base)
        self.assertTrue(config.cookie_secure)
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            SecurityConfig.from_env({**base, "PUBLIC_ORIGIN": "http://fairdrop.test"})
        with self.assertRaisesRegex(ValueError, "placeholder"):
            SecurityConfig.from_env({**base, "SESSION_DIGEST_KEY": "CHANGE_ME" * 5})

    def test_purpose_separation_prevents_digest_reuse(self) -> None:
        key = b"k" * 32
        value = "same-secret-value"
        self.assertNotEqual(credential_digest(key, value), session_digest(key, value))
        self.assertNotEqual(session_digest(key, value), csrf_token(key, value))

    def test_direct_config_construction_cannot_bypass_normal_policy(self) -> None:
        with self.assertRaisesRegex(ValueError, "COOKIE_SECURE"):
            SecurityConfig("normal", "https://fairdrop.test", b"s" * 32, b"c" * 32, False)
        with self.assertRaises(ValueError):
            SecurityConfig(
                "test",
                "http://localhost:8080",
                b"s" * 32,
                b"c" * 32,
                False,
                trusted_proxy_cidrs=("not-a-network",),
            )


if __name__ == "__main__":
    unittest.main()
