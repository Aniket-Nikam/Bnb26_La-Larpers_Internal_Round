import json
import unittest

from backend.app.security.errors import invalid_credentials, rate_limited


class ErrorTests(unittest.TestCase):
    def test_error_envelope_is_stable_and_contains_no_secret(self) -> None:
        secret = "actual-user-access-code"
        envelope = invalid_credentials().envelope("request-id")
        rendered = json.dumps(envelope)
        self.assertEqual(envelope["error"]["code"], "INVALID_CREDENTIALS")
        self.assertNotIn(secret, rendered)

    def test_rate_limit_exposes_retry_after_outside_safe_envelope(self) -> None:
        error = rate_limited(4)
        self.assertEqual(error.status_code, 429)
        self.assertEqual(error.retry_after, 4)
        self.assertTrue(error.retryable)


if __name__ == "__main__":
    unittest.main()
