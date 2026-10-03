import concurrent.futures
import unittest

from backend.app.security.errors import SecurityError
from backend.app.security.limits import LimitAction, RateLimiter
from backend.app.security.source import resolve_source_address
from fakes import AtomicFakeRedis, RecordingRedis


class SourceAndLimitTests(unittest.TestCase):
    def test_untrusted_peer_cannot_spoof_forwarded_address(self) -> None:
        resolved = resolve_source_address(
            peer_address="203.0.113.7",
            forwarded_for="198.51.100.1",
            trusted_proxy_cidrs=("10.42.0.10/32",),
        )
        self.assertEqual(resolved, "203.0.113.7")

    def test_trusted_proxy_uses_last_untrusted_address(self) -> None:
        resolved = resolve_source_address(
            peer_address="10.42.0.10",
            forwarded_for="198.51.100.9, 10.42.0.11",
            trusted_proxy_cidrs=("10.42.0.0/24",),
        )
        self.assertEqual(resolved, "198.51.100.9")

    def test_limiter_keys_never_contain_raw_credential_or_network_address(self) -> None:
        backend = RecordingRedis()
        limiter = RateLimiter(backend, b"k" * 32)
        credential = "very-secret-access-code"
        address = "198.51.100.44"
        limiter.enforce(
            action=LimitAction.LOGIN,
            account_id=None,
            session_digest_value=None,
            source_address=address,
            credential_value=credential,
        )
        call = repr(backend.calls)
        self.assertNotIn(credential, call)
        self.assertNotIn(address, call)

    def test_account_limit_is_stable_across_session_rotation(self) -> None:
        backend = RecordingRedis()
        limiter = RateLimiter(backend, b"k" * 32)
        for session in ("session-a-digest", "session-b-digest"):
            limiter.enforce(
                action=LimitAction.ENTRY_WRITE,
                account_id="same-account",
                session_digest_value=session,
                source_address="198.51.100.2",
            )
        first_keys = backend.calls[0][2][: backend.calls[0][1]]
        second_keys = backend.calls[1][2][: backend.calls[1][1]]
        self.assertEqual(first_keys[0], second_keys[0])
        self.assertNotEqual(first_keys[1], second_keys[1])

    def test_shared_ip_keeps_independent_account_dimensions(self) -> None:
        backend = RecordingRedis()
        limiter = RateLimiter(backend, b"k" * 32)
        for account in ("student-a", "student-b"):
            limiter.enforce(
                action=LimitAction.ENTRY_WRITE,
                account_id=account,
                session_digest_value=f"{account}-session-digest",
                source_address="192.0.2.20",
            )
        first_keys = backend.calls[0][2][: backend.calls[0][1]]
        second_keys = backend.calls[1][2][: backend.calls[1][1]]
        self.assertNotEqual(first_keys[0], second_keys[0])
        self.assertEqual(first_keys[2], second_keys[2])

    def test_rate_limit_returns_retry_after(self) -> None:
        limiter = RateLimiter(RecordingRedis(result=[0, 2_500]), b"k" * 32)
        with self.assertRaises(SecurityError) as caught:
            limiter.enforce(
                action=LimitAction.STATUS_READ,
                account_id="account",
                session_digest_value="session",
                source_address="198.51.100.2",
            )
        self.assertEqual(caught.exception.code, "RATE_LIMITED")
        self.assertEqual(caught.exception.retry_after, 3)

    def test_redis_outage_allows_safe_reads_but_rejects_protected_writes(self) -> None:
        limiter = RateLimiter(RecordingRedis(error=ConnectionError("redis unavailable")), b"k" * 32)
        read = limiter.enforce(
            action=LimitAction.STATUS_READ,
            account_id="account",
            session_digest_value="session",
            source_address="198.51.100.2",
        )
        self.assertTrue(read.allowed)
        self.assertTrue(read.degraded)
        with self.assertRaises(SecurityError) as caught:
            limiter.enforce(
                action=LimitAction.ENTRY_WRITE,
                account_id="account",
                session_digest_value="session",
                source_address="198.51.100.2",
            )
        self.assertEqual(caught.exception.code, "TEMPORARILY_UNAVAILABLE")
        self.assertTrue(caught.exception.retryable)

    def test_concurrent_calls_share_one_atomic_budget(self) -> None:
        limiter = RateLimiter(AtomicFakeRedis(), b"k" * 32)

        def attempt(_):
            try:
                limiter.enforce(
                    action=LimitAction.ENTRY_WRITE,
                    account_id="same-account",
                    session_digest_value="same-session",
                    source_address="198.51.100.2",
                )
                return True
            except SecurityError as exc:
                self.assertEqual(exc.code, "RATE_LIMITED")
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(attempt, range(40)))
        self.assertEqual(sum(results), 5)


if __name__ == "__main__":
    unittest.main()
