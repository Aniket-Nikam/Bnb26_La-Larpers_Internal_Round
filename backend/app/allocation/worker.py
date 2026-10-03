"""P4 entrypoint: python -m app.allocation.worker [--once]."""

import argparse
import logging
import signal
from threading import Event

from app.allocation.lifecycle import tick
from app.core.config import get_settings
from app.persistence.database import session_factory

logger = logging.getLogger("fairdrop.worker")


def main():
    parser = argparse.ArgumentParser(description="Reconcile durable FairDrop lifecycle/allocation")
    parser.add_argument(
        "--once", action="store_true", help="One reconciliation pass (verification)"
    )
    args = parser.parse_args()
    cfg = get_settings()
    cfg.seed_key()  # Refuse to start without a stable, valid seed-protection key.
    stop = Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    logging.basicConfig(level=logging.INFO)
    while not stop.is_set():
        try:
            failures = tick(session_factory())
            for drop_id in failures:
                logger.warning("Reconciliation deferred for drop %s", drop_id)
            if args.once:
                return 1 if failures else 0
        except Exception:
            logger.warning("Reconciliation temporarily unavailable")
            if args.once:
                return 1
        stop.wait(cfg.worker_tick_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
