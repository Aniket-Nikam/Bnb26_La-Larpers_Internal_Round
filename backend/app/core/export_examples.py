"""Contract fixtures only. These are NOT measured reports or runtime fallback data."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.core import schemas as s

NOW = datetime(2026, 10, 3, 12, tzinfo=UTC)
ID = UUID("10000000-0000-4000-8000-000000000001")
DROP = UUID("20000000-0000-4000-8000-000000000001")
OUT = Path(__file__).resolve().parents[3] / "contracts" / "examples"


def save(name, model):
    OUT.mkdir(exist_ok=True)
    (OUT / f"{name}.json").write_text(model.model_dump_json(indent=2) + "\n")


def main():
    drop = s.DropDetail(
        id=DROP,
        title="Schema fixture",
        category="workshop",
        organizer=s.PublicOrganizer(
            public_id="organizer-example", display_name="Example organizer"
        ),
        location_type="venue",
        location_label="Example venue",
        starts_at=NOW,
        ends_at=NOW,
        capacity=1,
        phase="SCHEDULED",
        mode="LOTTERY",
        description="Contract example only.",
        confirmation_seconds=60,
        rules_version="v1.0",
        seed_commitment="0" * 64,
        server_time=NOW,
        cancellation_reason=None,
    )
    save("scheduled", drop)
    for status in s.EntryStatus:
        reservation = None
        if status in {"OFFERED", "CONFIRMED", "EXPIRED"}:
            reservation = s.Reservation(
                id=ID,
                seat_slot_id=ID,
                status=status,
                expires_at=NOW,
                confirmed_at=NOW if status == "CONFIRMED" else None,
            )
        entry = s.EntryState(
            entry_id=ID,
            public_entry_id="random-public-example",
            drop_id=DROP,
            status=status,
            joined_at=NOW,
            receipt_id="receipt-example",
            draw_id=None if status == "ENTERED" else ID,
            rank=None if status == "ENTERED" else 1,
            reservation=reservation,
            server_time=NOW,
        )
        save(status.lower(), entry)
    for code in (
        "SESSION_REQUIRED",
        "FORBIDDEN",
        "CSRF_REJECTED",
        "INVITATION_REQUIRED",
        "ENTRY_NOT_OPEN",
        "ENTRY_CLOSED",
        "OFFER_EXPIRED",
        "INVALID_STATE",
        "IDEMPOTENCY_CONFLICT",
        "VALIDATION_ERROR",
        "RATE_LIMITED",
        "TEMPORARILY_UNAVAILABLE",
        "INTERNAL_ERROR",
        "NOT_IMPLEMENTED",
        "NOT_FOUND",
    ):
        save(
            "error-" + code.lower(),
            s.ErrorResponse(
                error=s.ErrorInfo(
                    code=code,
                    message="Safe example explanation.",
                    request_id=ID,
                    retryable=code in {"RATE_LIMITED", "TEMPORARILY_UNAVAILABLE"},
                    fields=None,
                )
            ),
        )
    config = s.RunRequest(
        scenario="normal",
        human_actors=1,
        bot_actors=0,
        duration_seconds=1,
        target_rps=1,
        retries_per_actor=0,
        trials=1,
        drop_capacity=1,
    )
    report = s.RunReport(
        provenance=s.RunProvenance(
            source="supplied_unreproduced",
            timestamp=NOW,
            contract_version="v1.0",
            algorithm_version="hmac-sha256-v1",
            app_commit="fixture",
            environment="contract fixture",
            hardware="not measured",
        ),
        workload=s.Workload(
            provisioned_identity_count=1,
            actors_by_cohort=s.CohortCounts(human=1, bot=0),
            request_rate_target=1,
            scheduled_iterations=1,
            delivered_iterations=0,
            dropped_iterations=1,
            achieved_rps=None,
            peak_open_connections=None,
            peak_inflight_requests=None,
            generator_cpu_peak=None,
            generator_memory_peak=None,
        ),
        admission=s.Admission(
            human=s.AdmissionCohort(
                attempted_unique_identities=1, accepted_unique_identities=0, admission_rate=0
            ),
            bot=s.AdmissionCohort(
                attempted_unique_identities=0, accepted_unique_identities=0, admission_rate=None
            ),
        ),
        allocation=s.Allocation(
            human=s.AllocationCohort(
                eligible_identities=0,
                initial_offers=0,
                confirmed=0,
                expired=0,
                actor_credentials=1,
                win_rate=None,
            ),
            bot=s.AllocationCohort(
                eligible_identities=0,
                initial_offers=0,
                confirmed=0,
                expired=0,
                actor_credentials=0,
                win_rate=None,
            ),
            bot_advantage=None,
            undefined_reason="No observations in fixture.",
        ),
        integrity=s.Integrity(
            capacity=1,
            maximum_observed_owned_slots=0,
            duplicate_active_owners=0,
            oversell_count=0,
            audit_pass=False,
        ),
        performance=s.Performance(
            successful_request_latency_ms=s.Latency(p50=None, p95=None, p99=None),
            endpoint_status_breakdown=[],
            expected_429=0,
            expected_403=0,
            expected_409=0,
            unexpected_5xx=0,
            network_errors=0,
        ),
        statistics=s.Statistics(
            trials=1,
            sample_sizes=s.CohortCounts(human=1, bot=0),
            interval_method=None,
            intervals=None,
        ),
        limitations=["Schema example only; NOT a measured run."],
    )
    for status in ("RUNNING", "COMPLETED", "FAILED"):
        save(
            "lab-" + status.lower(),
            s.RunDetail(
                run_id=ID,
                status=status,
                scenario="normal",
                config=config,
                progress=s.RunProgress(
                    completed_steps=1 if status == "COMPLETED" else 0,
                    total_steps=1,
                    message="Fixture only",
                ),
                started_at=NOW,
                ended_at=None if status == "RUNNING" else NOW,
                error=s.ErrorInfo(
                    code="RUNNER_FAILED",
                    message="Safe example failure",
                    request_id=ID,
                    retryable=False,
                )
                if status == "FAILED"
                else None,
                report=report if status == "COMPLETED" else None,
                server_time=NOW,
            ),
        )
    print("Exported typed fixtures (examples only)")


if __name__ == "__main__":
    main()
