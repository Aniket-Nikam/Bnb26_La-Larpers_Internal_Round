"""Connect P4's isolated runner to P1's durable domain and measured outcomes."""

import json
import os
import platform
import random
import secrets
import time
from collections import Counter, defaultdict
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.allocation.lifecycle import tick
from app.audit.router import proof
from app.audit.verifier import verify
from app.core import schemas as s
from app.core.clock import db_now
from app.core.config import get_settings
from app.drops import service
from app.lab.reports import build_run_report, performance_from_k6_summary
from app.lab.runner import LabRunner
from app.persistence import models as m
from app.persistence.database import session_factory
from app.security.provisioning import _credential_digest


def write_private(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # No raw access codes in API responses, DB rows, logs, or public reports.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as out:
        json.dump(value, out)


class IntegratedRunner(LabRunner):
    def _subprocess_env(self, config, fixture, run_id):
        return {
            **super()._subprocess_env(config, fixture, run_id),
            "LAB_PUBLIC_ORIGIN": get_settings().public_origin,
        }

    def prepare_trial(self, record, trial, fixture):
        maker = session_factory()
        config = record.config
        mapping = []
        with maker.begin() as db:
            job = db.get(m.LabRun, UUID(record.run_id))
            principal = s.Principal.model_validate(db.get(m.User, job.owner_id))
            for cohort, count in (("human", config["human_actors"]), ("bot", config["bot_actors"])):
                for index in range(count):
                    user = m.User(
                        id=uuid4(),
                        public_id=m.public_id(),
                        display_name=f"Lab {cohort} {trial}-{index}",
                        role="participant",
                    )
                    raw = secrets.token_urlsafe(32)
                    db.add(user)
                    actor_id = f"{cohort}-{index}"
                    if config["scenario"] == "credential_farm" and cohort == "bot":
                        actor_id = "farming-bot"
                    mapping.append(
                        {
                            "actor_id": actor_id,
                            "cohort": cohort,
                            "user_id": str(user.id),
                            "public_id": user.public_id,
                            "credentials": [{"access_code": raw, "public_id": user.public_id}],
                        }
                    )
                    if len(mapping) % 1000 == 0:
                        db.flush()
            db.flush()
            for actor in mapping:
                db.add(
                    m.AccessCredential(
                        user_id=UUID(actor["user_id"]),
                        digest=_credential_digest(actor["credentials"][0]["access_code"]),
                        label=f"lab:{record.run_id}",
                    )
                )
            db.flush()
            now = db_now(db)
            modes = (
                ["LOTTERY", "FCFS_DEMO"] if config["scenario"] == "policy_compare" else ["LOTTERY"]
            )
            if config["scenario"] == "expiry_race":
                modes = ["FCFS_DEMO"]
            drops = {}
            for mode in modes:
                payload = s.DraftInput(
                    title=f"Lab {record.run_id[:8]} trial {trial} {mode}",
                    description="Isolated measured workload; provisioned accounts are synthetic.",
                    category="lab",
                    location_type="online",
                    location_label="Attack lab",
                    capacity=config["drop_capacity"],
                    starts_at=now + timedelta(seconds=2),
                    ends_at=now + timedelta(seconds=config["duration_seconds"] + 7),
                    confirmation_seconds=2 if config["scenario"] == "expiry_race" else 300,
                    mode=mode,
                )
                drop = service.create(db, principal, payload)
                for actor in mapping:
                    db.add(
                        m.EligibilityGrant(
                            drop_id=drop.id, user_id=UUID(actor["user_id"]), granted_by=principal.id
                        )
                    )
                db.flush()
                drops[mode] = str(drop.id)
            now = db_now(db)
            for drop_id in drops.values():
                drop = db.get(m.Drop, UUID(drop_id))
                drop.starts_at = now + timedelta(seconds=2)
                drop.ends_at = now + timedelta(seconds=config["duration_seconds"] + 7)
                service.publish(db, drop, principal)
        value = {
            "drop_id": drops.get("LOTTERY", drops.get("FCFS_DEMO")),
            "actors": mapping,
            "policy_drop_ids": {
                "lottery": drops.get("LOTTERY"),
                "fcfs_demo": drops.get("FCFS_DEMO"),
            },
        }
        trial_fixture = self.private_fixture_root / record.run_id / f"trial-{trial}.json"
        write_private(trial_fixture, value)
        # Genuine scheduled opening; no mutation of published deadlines or clocks.
        for _ in range(40):
            tick(maker)
            with maker() as db:
                opened = all(
                    db.get(m.Drop, UUID(value)).phase == "OPEN" for value in drops.values()
                )
            if opened:
                return trial_fixture
            if self.store.get(record.run_id).status == "STOPPING":
                raise RuntimeError("Run stopped during preparation")
            time.sleep(0.1)
        raise TimeoutError("Scheduled lab drops did not open")

    def complete_trial(self, record, trial, fixture, stdout_path):
        value = json.loads(fixture.read_text())
        drop_ids = {UUID(v) for v in value["policy_drop_ids"].values() if v}
        maker = session_factory()
        # Let the ordinary allocation worker close, freeze, rank and offer. Calling
        # tick uses exactly that worker's idempotent transactions; it never chooses winners.
        for _ in range(600):
            tick(maker)
            with maker() as db:
                done = all(
                    (run := db.scalar(select(m.DrawRun).where(m.DrawRun.drop_id == d)))
                    and run.status == "PUBLISHED"
                    and db.get(m.Drop, d).phase in {"OFFERING", "COMPLETED"}
                    for d in drop_ids
                )
                if done:
                    expected = all(
                        len(
                            list(
                                db.scalars(select(m.Reservation).where(m.Reservation.drop_id == d))
                            )
                        )
                        >= min(
                            db.get(m.Drop, d).capacity,
                            db.scalar(
                                select(m.DrawRun.total_entries).where(m.DrawRun.drop_id == d)
                            ),
                        )
                        for d in drop_ids
                    )
                    if expected:
                        break
            if self.store.get(record.run_id).status == "STOPPING":
                return
            time.sleep(0.1)
        else:
            raise TimeoutError("Allocation reconciliation did not finish")
        measurements = read_measurements(stdout_path)
        policies = {}
        best_latency = {}
        for r in measurements:
            if r["endpoint"] == "entry" and r["status"] in {200, 201}:
                key = (r["drop_id"], r["public_id"])
                best_latency[key] = min(best_latency.get(key, float("inf")), r["latency_ms"])
        with maker() as db:
            for drop_id in drop_ids:
                drop = db.get(m.Drop, drop_id)
                run = db.scalar(select(m.DrawRun).where(m.DrawRun.drop_id == drop_id))
                entries = {
                    e.user_id: e
                    for e in db.scalars(select(m.Entry).where(m.Entry.drop_id == drop_id))
                }
                reservations = {
                    r.user_id: r
                    for r in db.scalars(
                        select(m.Reservation).where(m.Reservation.drop_id == drop_id)
                    )
                }
                ranks = dict(
                    db.execute(
                        select(m.Entry.user_id, m.DrawRank.rank)
                        .join(m.DrawRank, m.DrawRank.entry_id == m.Entry.id)
                        .where(m.DrawRank.draw_id == run.id)
                    ).all()
                )
                attempts = {
                    r["public_id"]
                    for r in measurements
                    if r["endpoint"] == "entry" and r["drop_id"] == str(drop_id)
                }
                identities = []
                for actor in value["actors"]:
                    user_id = UUID(actor["user_id"])
                    reservation = reservations.get(user_id)
                    identities.append(
                        {
                            "identity_id": actor["public_id"],
                            "actor_id": actor["actor_id"],
                            "cohort": actor["cohort"],
                            "attempted": actor["public_id"] in attempts,
                            "accepted": user_id in entries,
                            "initial_offer": ranks.get(user_id, drop.capacity + 1) <= drop.capacity,
                            "confirmed": bool(reservation and reservation.status == "CONFIRMED"),
                            "expired": bool(reservation and reservation.status == "EXPIRED"),
                            "entry_latency_ms": best_latency.get(
                                (str(drop_id), actor["public_id"])
                            ),
                        }
                    )
                events = list(
                    db.scalars(
                        select(m.AuditEvent)
                        .where(m.AuditEvent.drop_id == drop_id)
                        .order_by(m.AuditEvent.created_at, m.AuditEvent.id)
                    )
                )
                live, maximum = 0, 0
                for event in events:
                    if event.event_type == "RESERVATION_OFFERED":
                        live += 1
                        maximum = max(maximum, live)
                    elif event.event_type == "RESERVATION_EXPIRED":
                        live -= 1
                active = [r for r in reservations.values() if r.status in {"OFFERED", "CONFIRMED"}]
                duplicate = sum(n - 1 for n in Counter(r.user_id for r in active).values() if n > 1)
                slots_duplicate = sum(
                    n - 1 for n in Counter(r.seat_slot_id for r in active).values() if n > 1
                )
                public_proof = proof(drop_id, db).model_dump(mode="json")
                verified = verify(public_proof)
                integrity = {
                    "capacity": drop.capacity,
                    "maximum_observed_owned_slots": maximum,
                    "duplicate_active_owners": duplicate,
                    "oversell_count": max(0, maximum - drop.capacity),
                    "audit_pass": not duplicate
                    and not slots_duplicate
                    and maximum <= drop.capacity
                    and bool(verified),
                }
                policies[drop.mode] = {"identities": identities, "integrity": integrity}
        path = self.store.run_dir(record.run_id) / f"outcomes-{trial}.json"
        path.write_text(
            json.dumps({"policies": policies, "measurements": measurements}), encoding="utf-8"
        )

    def _write_partial_report(self, run_dir, record, summary_paths, app_commit):
        outcomes = [json.loads(p.read_text()) for p in sorted(run_dir.glob("outcomes-*.json"))]
        if not outcomes:
            raise RuntimeError("No reconciled trial outcomes are available")
        summaries = [json.loads(p.read_text()) for p in summary_paths]
        data = measured_report(record.config, outcomes, summaries, app_commit)
        path = run_dir / "report.json"
        path.write_text(
            s.RunReport.model_validate(data).model_dump_json(indent=2), encoding="utf-8"
        )
        return path


def read_measurements(path):
    result = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("FD_MEASURE "):
                result.append(json.loads(line[len("FD_MEASURE ") :]))
    return result


def percentiles(values):
    values = sorted(values)

    def percentile(q):
        if not values:
            return None
        index = (len(values) - 1) * q
        lo = int(index)
        return values[lo] + (values[min(lo + 1, len(values) - 1)] - values[lo]) * (index - lo)

    return {"p50": percentile(0.5), "p95": percentile(0.95), "p99": percentile(0.99)}


def measured_report(config, outcomes, summaries, app_commit):
    observations = [r for trial in outcomes for r in trial["measurements"]]
    grouped = defaultdict(list)
    for observation in observations:
        grouped[(observation["endpoint"], observation["status"])].append(observation["latency_ms"])
    counts = Counter(r["status"] for r in observations)
    per_trial = [
        performance_from_k6_summary(summary, target_rps=config["target_rps"])
        for summary in summaries
    ]
    workload = {
        "provisioned_identity_count": (config["human_actors"] + config["bot_actors"])
        * len(outcomes),
        "actors_by_cohort": {
            "human": config["human_actors"] * len(outcomes),
            "bot": config["bot_actors"] * len(outcomes),
        },
        "request_rate_target": config["target_rps"],
        "scheduled_iterations": sum(p["workload"]["scheduled_iterations"] for p in per_trial),
        "delivered_iterations": sum(p["workload"]["delivered_iterations"] for p in per_trial),
        "dropped_iterations": sum(p["workload"]["dropped_iterations"] for p in per_trial),
        "achieved_rps": sum(p["workload"]["achieved_rps"] for p in per_trial) / len(per_trial),
        "peak_open_connections": None,
        "peak_inflight_requests": None,
        "generator_cpu_peak": None,
        "generator_memory_peak": None,
    }
    performance = {
        "successful_request_latency_ms": percentiles(
            [r["latency_ms"] for r in observations if 200 <= r["status"] < 400]
        ),
        "endpoint_status_breakdown": [
            {
                "endpoint": endpoint,
                "status": status,
                "count": len(values),
                "latency_ms": percentiles(values),
            }
            for (endpoint, status), values in sorted(grouped.items())
        ],
        "expected_429": counts[429],
        "expected_403": counts[403],
        "expected_409": counts[409],
        "unexpected_5xx": sum(count for status, count in counts.items() if status >= 500),
        "network_errors": counts[0],
    }
    primary = "LOTTERY" if "LOTTERY" in outcomes[0]["policies"] else "FCFS_DEMO"
    limitations = [
        "Synthetic provisioned identities; no claim of real-world personhood or bot detection.",
        "Allocation observations are taken after draw publication and initial offering; later confirmations and expiries may change live inventory.",
        "Generator CPU, memory, connection and inflight peaks were not instrumented and are null.",
        "Arrival rates are calibrated to expected HTTP requests per healthy iteration. Admission failures, retries, and short-run boundary effects can change achieved HTTP RPS.",
    ]
    policies = {}
    for mode in outcomes[0]["policies"]:
        trial_rows = [trial["policies"][mode]["identities"] for trial in outcomes]
        rows = [row for trial in trial_rows for row in trial]
        integrity_trials = [trial["policies"][mode]["integrity"] for trial in outcomes]
        integrity = {
            "capacity": config["drop_capacity"],
            "maximum_observed_owned_slots": max(
                t["maximum_observed_owned_slots"] for t in integrity_trials
            ),
            "duplicate_active_owners": sum(t["duplicate_active_owners"] for t in integrity_trials),
            "oversell_count": sum(t["oversell_count"] for t in integrity_trials),
            "audit_pass": all(t["audit_pass"] for t in integrity_trials),
        }
        aggregate = build_run_report(
            config=config,
            identities=rows,
            performance={"workload": workload, "performance": performance},
            integrity=integrity,
            provenance={
                "contract_version": "v1.0",
                "algorithm_version": "hmac-sha256-v1" if mode == "LOTTERY" else "fcfs-admission-v1",
                "app_commit": app_commit,
                "environment": "isolated demo",
                "hardware": f"{platform.system()} {platform.machine()}",
            },
            limitations=limitations,
        )
        allocation = {
            "human": {},
            "bot": {},
            "bot_advantage": aggregate["allocation"]["bot_advantage"],
            "undefined_reason": aggregate["allocation"]["bot_advantage_undefined_reason"],
        }
        for cohort in ("human", "bot"):
            c = aggregate["allocation"]["cohorts"][cohort]
            allocation[cohort] = {
                key: c[key]
                for key in (
                    "eligible_identities",
                    "initial_offers",
                    "confirmed",
                    "expired",
                    "win_rate",
                )
            }
            allocation[cohort]["actor_credentials"] = c["credential_count"]
        intervals = bootstrap_intervals(trial_rows)
        statistics = {
            "trials": len(outcomes),
            "sample_sizes": aggregate["statistics"]["sample_sizes"],
            "interval_method": "paired trial bootstrap, 2000 resamples, 95%" if intervals else None,
            "intervals": intervals,
        }
        policies[mode] = {
            "admission": aggregate["admission"],
            "allocation": allocation,
            "integrity": integrity,
            "statistics": statistics,
        }
        if mode == primary:
            result = {
                "provenance": aggregate["provenance"],
                "workload": workload,
                "performance": performance,
                **policies[mode],
                "limitations": list(limitations),
            }
    if len(outcomes) == 1:
        result["limitations"].append(
            "One trial does not support a trial-level confidence interval."
        )
    if len(outcomes) < config["trials"]:
        result["limitations"].append("Partial report: fewer trials completed than requested.")
    if len(policies) > 1:
        result["policy_comparison"] = policies
        result["limitations"].append(
            "Top-level allocation describes LOTTERY; policy_comparison separates FCFS_DEMO and LOTTERY outcomes for the same provisioned trial identities."
        )
    return result


def bootstrap_intervals(trials):
    if len(trials) < 2:
        return None
    rng = random.Random(73120491)  # statistical reproducibility, unrelated to draw entropy
    trial_counts = []
    for rows in trials:
        counts = {}
        for cohort in ("human", "bot"):
            accepted = [r for r in rows if r["cohort"] == cohort and r["accepted"]]
            counts[cohort] = (len(accepted), sum(r["initial_offer"] for r in accepted))
        trial_counts.append(counts)
    rates = {"human_initial_offer_rate": [], "bot_initial_offer_rate": []}
    for _ in range(2000):
        sample = [rng.choice(trial_counts) for _ in trial_counts]
        for cohort in ("human", "bot"):
            total = sum(t[cohort][0] for t in sample)
            if total:
                rates[f"{cohort}_initial_offer_rate"].append(
                    sum(t[cohort][1] for t in sample) / total
                )
    intervals = []
    for metric, values in rates.items():
        if values:
            values.sort()
            intervals.append(
                {
                    "metric": metric,
                    "lower": values[int((len(values) - 1) * 0.025)],
                    "upper": values[int((len(values) - 1) * 0.975)],
                    "confidence": 0.95,
                }
            )
    return intervals or None
