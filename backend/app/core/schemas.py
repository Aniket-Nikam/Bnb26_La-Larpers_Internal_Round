"""Normative v1.0 wire schemas shared by P1/P2/P3/P4."""

from datetime import UTC
from enum import StrEnum
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

UtcDatetime = Annotated[AwareDatetime, AfterValidator(lambda value: value.astimezone(UTC))]


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class DropPhase(StrEnum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    DRAWING = "DRAWING"
    OFFERING = "OFFERING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AllocationMode(StrEnum):
    LOTTERY = "LOTTERY"
    FCFS_DEMO = "FCFS_DEMO"


class EntryStatus(StrEnum):
    ENTERED = "ENTERED"
    WAITLISTED = "WAITLISTED"
    OFFERED = "OFFERED"
    CONFIRMED = "CONFIRMED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class RunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ErrorInfo(DTO):
    code: str
    message: str
    request_id: UUID
    retryable: bool
    fields: dict[str, list[str]] | None = None


class ErrorResponse(DTO):
    error: ErrorInfo


class EmptyInput(DTO):
    pass


class Principal(DTO):
    id: UUID
    public_id: str
    role: Literal["participant", "organizer", "admin"]
    display_name: str
    timezone: str


class SessionInput(DTO):
    access_code: str = Field(min_length=1, max_length=256)


class SessionResponse(DTO):
    principal: Principal
    csrf_token: str
    expires_at: UtcDatetime
    server_time: UtcDatetime


class ProfilePatch(DTO):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    timezone: str | None = None

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        if value is not None:
            try:
                ZoneInfo(value)
            except (ValueError, ZoneInfoNotFoundError):
                raise ValueError("Use a supported IANA timezone") from None
        return value


class ProfileResponse(DTO):
    principal: Principal
    server_time: UtcDatetime


class PublicOrganizer(DTO):
    public_id: str
    display_name: str


class DropSummary(DTO):
    id: UUID
    title: str
    category: str
    organizer: PublicOrganizer
    location_type: Literal["online", "venue"]
    location_label: str
    starts_at: UtcDatetime
    ends_at: UtcDatetime
    capacity: int
    phase: DropPhase
    mode: AllocationMode


class DropDetail(DropSummary):
    description: str
    confirmation_seconds: int
    rules_version: str
    eligibility_policy: Literal["invitation"] = "invitation"
    seed_commitment: str | None
    server_time: UtcDatetime
    cancellation_reason: str | None


class Reservation(DTO):
    id: UUID
    seat_slot_id: UUID
    status: Literal["OFFERED", "CONFIRMED", "EXPIRED"]
    expires_at: UtcDatetime
    confirmed_at: UtcDatetime | None


class EntryState(DTO):
    entry_id: UUID
    public_entry_id: str
    drop_id: UUID
    status: EntryStatus
    joined_at: UtcDatetime
    receipt_id: str
    draw_id: UUID | None
    rank: int | None = Field(ge=1)
    reservation: Reservation | None
    server_time: UtcDatetime


class Eligibility(DTO):
    eligible: bool
    reason: Literal["INVITATION_REQUIRED", "REVOKED"] | None


class MyDropState(DTO):
    entry: EntryState | None
    eligibility: Eligibility
    server_time: UtcDatetime


class Receipt(DTO):
    entry: EntryState
    drop: DropSummary
    rules_version: str
    proof_url: str


T = TypeVar("T")


class Page(DTO, Generic[T]):
    items: list[T]
    next_cursor: str | None


class InventoryMetrics(DTO):
    drop_id: UUID
    capacity: int
    entered_count: int
    eligible_count: int
    active_reservations: int
    confirmed_seats: int
    free_seats: int
    expired_reservations: int
    duplicate_active_owners: int
    integrity_ok: bool
    server_time: UtcDatetime


class AuditRecord(DTO):
    id: UUID
    event_type: str
    object_type: str
    object_id: UUID
    actor_public_id: str | None
    reason: str | None
    created_at: UtcDatetime


class DrawStatus(DTO):
    draw_id: UUID
    drop_id: UUID
    status: Literal["FROZEN", "COMPUTING", "PUBLISHED"]
    processed_entries: int
    total_entries: int
    recoverable_error: str | None
    server_time: UtcDatetime


class DraftInput(DTO):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=10000)
    category: str = Field(min_length=1, max_length=80)
    location_type: Literal["online", "venue"]
    location_label: str = Field(min_length=1, max_length=200)
    capacity: int = Field(ge=1, le=500)
    starts_at: UtcDatetime
    ends_at: UtcDatetime
    confirmation_seconds: int = Field(ge=1, le=604800)
    mode: AllocationMode = AllocationMode.LOTTERY

    @model_validator(mode="after")
    def dates(self):
        if self.starts_at >= self.ends_at:
            raise ValueError("starts_at must precede ends_at")
        return self


class DraftPatch(DTO):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    location_type: Literal["online", "venue"] | None = None
    location_label: str | None = Field(default=None, min_length=1, max_length=200)
    capacity: int | None = Field(default=None, ge=1, le=500)
    starts_at: UtcDatetime | None = None
    ends_at: UtcDatetime | None = None
    confirmation_seconds: int | None = Field(default=None, ge=1, le=604800)
    mode: AllocationMode | None = None

    @model_validator(mode="after")
    def nonnull_updates(self):
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Editable fields cannot be null")
        return self


class CancelInput(DTO):
    reason: str = Field(min_length=1, max_length=500)


class GrantInput(DTO):
    user_public_ids: list[Annotated[str, Field(min_length=1, max_length=64)]] = Field(
        min_length=1, max_length=500
    )


class GrantSummary(DTO):
    drop_id: UUID
    granted_count: int
    existing_count: int
    server_time: UtcDatetime


class PendingProof(DTO):
    status: Literal["pending"] = "pending"
    phase: DropPhase
    seed_commitment: str | None
    manifest_commitment: str | None
    server_time: UtcDatetime


class ProofEntry(DTO):
    public_entry_id: str
    score_hex: str | None
    rank: int = Field(ge=1)


class PublishedProof(DTO):
    status: Literal["published"] = "published"
    drop_id: UUID
    draw_id: UUID
    algorithm_version: str
    rules_version: str
    mode: AllocationMode
    seed: str | None
    seed_commitment: str | None
    manifest_commitment: str
    entries: list[ProofEntry] = Field(max_length=50000)
    server_time: UtcDatetime


ProofResponse = Annotated[PendingProof | PublishedProof, Field(discriminator="status")]
Scenario = Literal[
    "normal",
    "early_bot",
    "retry_flood",
    "credential_farm",
    "shared_ip",
    "reconnect",
    "worker_restart",
    "expiry_race",
    "redis_failure",
    "policy_compare",
]


class RunRequest(DTO):
    scenario: Scenario
    human_actors: int = Field(ge=0, le=50000)
    bot_actors: int = Field(ge=0, le=50000)
    duration_seconds: int = Field(ge=1, le=300)
    target_rps: float = Field(gt=0, le=2000, allow_inf_nan=False)
    retries_per_actor: int = Field(ge=0, le=20)
    trials: int = Field(ge=1, le=20)
    drop_capacity: int = Field(ge=1, le=500)

    @model_validator(mode="after")
    def actors(self):
        if not 1 <= self.human_actors + self.bot_actors <= 50000:
            raise ValueError("Total identities must be 1..50000")
        return self


class RunProgress(DTO):
    completed_steps: int
    total_steps: int
    message: str


class RunProvenance(DTO):
    source: Literal["measured", "supplied_unreproduced"]
    timestamp: UtcDatetime
    contract_version: str
    algorithm_version: str
    app_commit: str
    environment: str
    hardware: str


class CohortCounts(DTO):
    human: int
    bot: int


class Workload(DTO):
    provisioned_identity_count: int
    actors_by_cohort: CohortCounts
    request_rate_target: float
    scheduled_iterations: int
    delivered_iterations: int
    dropped_iterations: int
    achieved_rps: float | None
    peak_open_connections: int | None
    peak_inflight_requests: int | None
    generator_cpu_peak: float | None
    generator_memory_peak: int | None


class AdmissionCohort(DTO):
    attempted_unique_identities: int
    accepted_unique_identities: int
    admission_rate: float | None


class Admission(DTO):
    human: AdmissionCohort
    bot: AdmissionCohort


class AllocationCohort(DTO):
    eligible_identities: int
    initial_offers: int
    confirmed: int
    expired: int
    actor_credentials: int
    win_rate: float | None


class Allocation(DTO):
    human: AllocationCohort
    bot: AllocationCohort
    bot_advantage: float | None
    undefined_reason: str | None


class Integrity(DTO):
    capacity: int
    maximum_observed_owned_slots: int
    duplicate_active_owners: int
    oversell_count: int
    audit_pass: bool


class Latency(DTO):
    p50: float | None
    p95: float | None
    p99: float | None


class EndpointPerformance(DTO):
    endpoint: str
    status: int
    count: int
    latency_ms: Latency


class Performance(DTO):
    successful_request_latency_ms: Latency
    endpoint_status_breakdown: list[EndpointPerformance]
    expected_429: int
    expected_403: int
    expected_409: int
    unexpected_5xx: int
    network_errors: int


class Interval(DTO):
    metric: str
    lower: float
    upper: float
    confidence: float


class Statistics(DTO):
    trials: int
    sample_sizes: CohortCounts
    interval_method: str | None
    intervals: list[Interval] | None


class RunReport(DTO):
    provenance: RunProvenance
    workload: Workload
    admission: Admission
    allocation: Allocation
    integrity: Integrity
    performance: Performance
    statistics: Statistics
    limitations: list[str]


class RunSummary(DTO):
    run_id: UUID
    status: RunStatus
    scenario: Scenario
    started_at: UtcDatetime | None
    ended_at: UtcDatetime | None
    server_time: UtcDatetime


class RunDetail(RunSummary):
    config: RunRequest
    progress: RunProgress
    error: ErrorInfo | None
    report: RunReport | None


class RunAccepted(DTO):
    run_id: UUID
    status: Literal["QUEUED"]
    server_time: UtcDatetime


class RunStopped(DTO):
    run_id: UUID
    status: RunStatus
    server_time: UtcDatetime


class ReportPending(DTO):
    status: Literal["pending"] = "pending"
    run_id: UUID
    server_time: UtcDatetime


class LiveHealth(DTO):
    status: Literal["alive"] = "alive"


class Capabilities(DTO):
    safe_reads: bool
    protected_writes: bool
    lab: bool
    fcfs_demo: bool


class Dependencies(DTO):
    database: Literal["ready", "unavailable"]
    redis: Literal["ready", "unavailable"]
    security: Literal["ready", "not_implemented"]


class ReadyHealth(DTO):
    status: Literal["ready", "degraded", "unavailable"]
    dependencies: Dependencies
    capabilities: Capabilities
