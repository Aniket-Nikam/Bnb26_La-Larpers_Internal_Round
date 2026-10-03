import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  Download,
  FileUp,
  FlaskConical,
  Plus,
  ShieldCheck,
  Ticket,
  Users,
} from "lucide-react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TicketCard } from "../components/Ticket";
import {
  CopyButton,
  EmptyState,
  LoadingBlock,
  Metric,
  PageHeader,
  StatusBadge,
} from "../components/Design";
import { ErrorMessage } from "../components/State";
import { api, time, useAction, useSession } from "../lib/api/client";
import type { Drop, Page, Schema } from "../lib/api/client";

export function OrganizerDashboard() {
  const drops = useQuery({
    queryKey: ["admin-drops"],
    queryFn: () => api<Page<Schema["DropSummary"]>>("/admin/drops"),
  });
  return (
    <div className="pb-16">
      <PageHeader
        eyebrow="Organizer command center"
        title="Build trust before the queue arrives."
        body="Create drops, grant eligibility, monitor inventory, publish proofs, and challenge the system under controlled attack traffic."
        action={
          <Link className="button" to="/organizer/new">
            <Plus className="h-4 w-4" />
            Create drop
          </Link>
        }
      />
      <ErrorMessage error={drops.error} />
      {drops.isPending && <LoadingBlock label="Loading organizer drops" />}
      {drops.data?.items.length === 0 && (
        <EmptyState
          title="Create your first fair drop"
          body="Configure the entry window, capacity, and confirmation policy before inviting participants."
          action={
            <Link className="button" to="/organizer/new">
              Create drop
            </Link>
          }
        />
      )}
      <div className="grid gap-5 md:grid-cols-2">
        {drops.data?.items.map((d) => (
          <TicketCard className="p-7 sm:p-8" key={d.id}>
            <div className="flex items-start justify-between gap-5">
              <StatusBadge value={d.phase} />
              <Ticket className="h-5 w-5 accent" />
            </div>
            <h2 className="mt-8 text-2xl font-semibold tracking-tight">
              {d.title}
            </h2>
            <p className="mt-3 text-sm muted">
              {d.capacity} seats,{" "}
              {d.mode === "LOTTERY" ? "fair lottery" : "FCFS demo"}
            </p>
            <div className="mt-7 flex items-center justify-between border-t border-white/10 pt-5 text-sm">
              <span className="flex items-center gap-2 muted">
                <CalendarDays className="h-4 w-4" />
                {time(d.starts_at)}
              </span>
              <Link
                className="link inline-flex items-center gap-2"
                to={`/organizer/drops/${d.id}`}
              >
                Manage <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </TicketCard>
        ))}
      </div>
    </div>
  );
}

export function CreateDrop() {
  const action = useAction<Drop>();
  const navigate = useNavigate();
  return (
    <div className="mx-auto max-w-4xl pb-16">
      <PageHeader
        eyebrow="New drop"
        title="Set the rules before anyone enters."
        body="Capacity, timing, eligibility, and confirmation policy lock at publication to prevent favorable edits after entries arrive."
      />
      <form
        className="surface grid gap-6 p-7 sm:grid-cols-2 sm:p-10"
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          action.mutate(
            {
              path: "/admin/drops",
              body: {
                title: f.get("title"),
                description: f.get("description"),
                category: f.get("category"),
                location_type: f.get("location_type"),
                location_label: f.get("location_label"),
                capacity: Number(f.get("capacity")),
                starts_at: new Date(String(f.get("starts_at"))).toISOString(),
                ends_at: new Date(String(f.get("ends_at"))).toISOString(),
                confirmation_seconds: Number(f.get("confirmation_seconds")),
                mode: "LOTTERY",
              },
            },
            { onSuccess: (d) => navigate(`/organizer/drops/${d.id}`) },
          );
        }}
      >
        <label className="sm:col-span-2">
          <span className="field-label">Title</span>
          <input
            className="field"
            name="title"
            required
            maxLength={200}
            placeholder="Example: Robotics workshop seats"
          />
        </label>
        <label className="sm:col-span-2">
          <span className="field-label">Description</span>
          <textarea className="field" name="description" maxLength={10000} />
        </label>
        <label>
          <span className="field-label">Category</span>
          <input
            className="field"
            name="category"
            required
            maxLength={80}
            defaultValue="workshop"
          />
        </label>
        <label>
          <span className="field-label">Location type</span>
          <select className="field" name="location_type">
            <option value="venue">Venue</option>
            <option value="online">Online</option>
          </select>
        </label>
        <label className="sm:col-span-2">
          <span className="field-label">Location</span>
          <input
            className="field"
            name="location_label"
            required
            maxLength={200}
          />
        </label>
        <label>
          <span className="field-label">Seats</span>
          <input
            className="field"
            name="capacity"
            type="number"
            min={1}
            max={500}
            defaultValue={10}
            required
          />
        </label>
        <label>
          <span className="field-label">Entry start (your local time)</span>
          <input
            className="field"
            name="starts_at"
            type="datetime-local"
            required
          />
        </label>
        <label>
          <span className="field-label">Entry end (your local time)</span>
          <input
            className="field"
            name="ends_at"
            type="datetime-local"
            required
          />
        </label>
        <label>
          <span className="field-label">Confirmation window (seconds)</span>
          <input
            className="field"
            name="confirmation_seconds"
            type="number"
            min={1}
            max={604800}
            defaultValue={300}
            required
          />
        </label>
        <div className="sm:col-span-2 flex flex-wrap items-center gap-4 border-t border-white/10 pt-6">
          <button className="button" disabled={action.isPending}>
            {action.isPending ? "Saving draft..." : "Save secure draft"}
          </button>
          <Link className="button-ghost" to="/organizer">
            Cancel
          </Link>
        </div>
        <ErrorMessage error={action.error} />
      </form>
    </div>
  );
}

function DropEditor({ drop }: { drop: Drop }) {
  const action = useAction();
  return (
    <details className="surface-soft p-6 sm:p-8">
      <summary className="cursor-pointer font-semibold">
        Edit drop details
      </summary>
      <form
        className="mt-6 grid gap-5 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          const body: Record<string, unknown> = {
            title: f.get("title"),
            description: f.get("description"),
            location_label: f.get("location_label"),
          };
          if (drop.phase === "DRAFT") {
            body.capacity = Number(f.get("capacity"));
            body.confirmation_seconds = Number(f.get("confirmation_seconds"));
          }
          action.mutate({
            path: `/admin/drops/${drop.id}`,
            method: "PATCH",
            body,
          });
        }}
      >
        <label className="sm:col-span-2">
          <span className="field-label">Title</span>
          <input
            className="field"
            name="title"
            required
            maxLength={200}
            defaultValue={drop.title}
          />
        </label>
        <label className="sm:col-span-2">
          <span className="field-label">Description</span>
          <textarea
            className="field"
            name="description"
            maxLength={10000}
            defaultValue={drop.description}
          />
        </label>
        <label className="sm:col-span-2">
          <span className="field-label">Location</span>
          <input
            className="field"
            name="location_label"
            required
            maxLength={200}
            defaultValue={drop.location_label}
          />
        </label>
        {drop.phase === "DRAFT" && (
          <>
            <label>
              <span className="field-label">Seats</span>
              <input
                className="field"
                name="capacity"
                required
                type="number"
                min={1}
                max={500}
                defaultValue={drop.capacity}
              />
            </label>
            <label>
              <span className="field-label">Confirmation window (seconds)</span>
              <input
                className="field"
                name="confirmation_seconds"
                required
                type="number"
                min={1}
                max={604800}
                defaultValue={drop.confirmation_seconds}
              />
            </label>
          </>
        )}
        <button
          className="button sm:col-span-2 sm:justify-self-start"
          disabled={action.isPending}
        >
          Save changes
        </button>
        <ErrorMessage error={action.error} />
        {action.isSuccess && <p role="status">Changes saved.</p>}
      </form>
    </details>
  );
}

export function ManageDrop() {
  const { id } = useParams();
  const [ids, setIds] = useState("");
  const [importName, setImportName] = useState("");
  const [reason, setReason] = useState("");
  const action = useAction();
  const drop = useQuery({
    queryKey: ["drop", id],
    queryFn: () => api<Drop>(`/drops/${id}`),
    refetchInterval: 5000,
  });
  const metrics = useQuery({
    queryKey: ["metrics", id],
    queryFn: () =>
      api<Schema["InventoryMetrics"]>(`/admin/drops/${id}/metrics`),
    refetchInterval: 5000,
  });
  const audit = useQuery({
    queryKey: ["audit", id],
    queryFn: () => api<Page<Schema["AuditRecord"]>>(`/admin/drops/${id}/audit`),
    refetchInterval: 5000,
  });
  const entries = useQuery({
    queryKey: ["admin-entries", id],
    queryFn: () =>
      api<Page<Schema["EntryState"]>>(`/admin/drops/${id}/entries`),
    refetchInterval: 5000,
  });
  const command = (name: string, body: unknown = {}) =>
    action.mutate({ path: `/admin/drops/${id}/${name}`, body });
  const inviteIds = [
    ...new Set(
      ids
        .split(/[\s,]+/)
        .map((value) => value.trim())
        .filter(Boolean),
    ),
  ];
  return (
    <div className="pb-16">
      <ErrorMessage error={drop.error ?? action.error ?? metrics.error} />
      {drop.isPending && (
        <div className="pt-12">
          <LoadingBlock label="Loading drop management" />
        </div>
      )}
      {drop.data && (
        <>
          <PageHeader
            eyebrow="Drop operations"
            title={drop.data.title}
            body={time(drop.data.starts_at) + " to " + time(drop.data.ends_at)}
            action={<StatusBadge value={drop.data.phase} />}
          />
          {drop.data.phase === "DRAFT" && (
            <TicketCard className="mb-6 p-7 sm:p-9">
              <div className="grid gap-8 lg:grid-cols-[1fr_0.7fr]">
                <div>
                  <div className="flex items-center gap-3">
                    <Users className="h-6 w-6 accent" />
                    <h2 className="text-2xl font-semibold">
                      Grant participant eligibility
                    </h2>
                  </div>
                  <p className="mt-3 text-sm leading-relaxed muted">
                    Paste public account IDs or import a CSV/text file.
                    Duplicate IDs are removed before submission.
                  </p>
                  <label className="mt-6 block">
                    <span className="field-label">Public account IDs</span>
                    <textarea
                      className="field min-h-44 font-mono text-sm"
                      placeholder="One public ID per line"
                      value={ids}
                      onChange={(e) => setIds(e.target.value)}
                    />
                  </label>
                  <div className="mt-5 flex flex-wrap gap-3">
                    <button
                      className="button"
                      disabled={action.isPending || inviteIds.length === 0}
                      onClick={() =>
                        command("eligibility", {
                          user_public_ids: inviteIds,
                        })
                      }
                    >
                      Grant {inviteIds.length || ""} invitation
                      {inviteIds.length === 1 ? "" : "s"}
                    </button>
                    <label className="button-secondary cursor-pointer">
                      <FileUp className="h-4 w-4" /> Import CSV
                      <input
                        className="sr-only"
                        type="file"
                        accept=".csv,.txt,text/csv,text/plain"
                        onChange={async (event) => {
                          const file = event.target.files?.[0];
                          if (!file) return;
                          const values = (await file.text())
                            .split(/[\s,]+/)
                            .map((value) => value.trim())
                            .filter(Boolean);
                          setIds([...new Set(values)].join("\n"));
                          setImportName(file.name);
                        }}
                      />
                    </label>
                  </div>
                  {importName && (
                    <p className="mt-3 text-xs muted">Imported {importName}</p>
                  )}
                  <button
                    className="button-danger mt-3"
                    disabled={action.isPending || inviteIds.length !== 1}
                    onClick={() =>
                      action.mutate({
                        path: `/admin/drops/${id}/eligibility/${encodeURIComponent(inviteIds[0] ?? "")}`,
                        method: "DELETE",
                      })
                    }
                  >
                    Revoke selected invitation
                  </button>
                </div>
                <aside className="rounded-[var(--radius-control)] border border-[rgb(var(--accent)/0.24)] bg-[rgb(var(--accent)/0.07)] p-6">
                  <ShieldCheck className="h-7 w-7 accent" />
                  <h3 className="mt-8 text-xl font-semibold">
                    Ready to publish?
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed muted">
                    Publication locks invitations, capacity, timing,
                    confirmation policy, and lottery mode.
                  </p>
                  <button
                    className="button mt-6 w-full"
                    disabled={action.isPending}
                    onClick={() => command("publish")}
                  >
                    Publish locked drop
                  </button>
                </aside>
              </div>
            </TicketCard>
          )}
          <div className="mb-6">
            <DropEditor key={drop.data.id} drop={drop.data} />
          </div>
          <div className="mb-8 flex flex-wrap gap-3">
            {drop.data.phase === "SCHEDULED" && (
              <button
                className="button-secondary"
                disabled={action.isPending}
                onClick={() => command("open")}
              >
                Open when scheduled
              </button>
            )}
            {drop.data.phase === "OPEN" && (
              <button
                className="button-secondary"
                disabled={action.isPending}
                onClick={() => command("close")}
              >
                Close after deadline
              </button>
            )}
            {["CLOSED", "DRAWING"].includes(drop.data.phase) && (
              <button
                className="button-secondary"
                disabled={action.isPending}
                onClick={() => command("draw")}
              >
                Start / resume draw
              </button>
            )}
            <Link className="button-secondary" to={`/drops/${id}/proof`}>
              <ShieldCheck className="h-4 w-4" /> Draw proof
            </Link>
            <a
              className="button-secondary"
              href={`/api/v1/admin/drops/${id}/entries/export`}
            >
              <Download className="h-4 w-4" /> Export entries
            </a>
          </div>
          {metrics.data && (
            <section className="surface mb-8 p-7 sm:p-9">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-semibold">
                    Live allocation health
                  </h2>
                  <p className="mt-2 text-sm muted">
                    Authoritative values from PostgreSQL.
                  </p>
                </div>
                <span
                  className="status-badge"
                  data-tone={metrics.data.integrity_ok ? "success" : "danger"}
                >
                  {metrics.data.integrity_ok
                    ? "Inventory verified"
                    : "Investigation required"}
                </span>
              </div>
              <div className="mt-7 grid grid-cols-2 gap-x-6 border-t border-white/10 md:grid-cols-4">
                <Metric
                  label="Accepted entries"
                  value={metrics.data.entered_count}
                />
                <Metric
                  label="Active offers"
                  value={metrics.data.active_reservations}
                />
                <Metric
                  label="Confirmed seats"
                  value={metrics.data.confirmed_seats}
                />
                <Metric
                  label="Seats available"
                  value={metrics.data.free_seats}
                />
              </div>
              <p className="mt-3 text-xs muted">
                Duplicate active owners: {metrics.data.duplicate_active_owners}.
                Expired offers: {metrics.data.expired_reservations}.
              </p>
            </section>
          )}
          {metrics.isPending && (
            <div className="mb-8">
              <LoadingBlock label="Loading inventory metrics" />
            </div>
          )}
          {!["COMPLETED", "CANCELLED"].includes(drop.data.phase) && (
            <details className="surface-soft mb-8 p-6">
              <summary className="cursor-pointer font-semibold text-red-200">
                Cancellation controls
              </summary>
              <form
                className="mt-5 grid gap-3 md:grid-cols-[1fr_auto]"
                onSubmit={(e) => {
                  e.preventDefault();
                  command("cancel", { reason });
                }}
              >
                <input
                  aria-label="Cancellation reason"
                  className="field"
                  value={reason}
                  required
                  maxLength={500}
                  placeholder="State a clear cancellation reason"
                  onChange={(e) => setReason(e.target.value)}
                />
                <button className="button-danger" disabled={action.isPending}>
                  Cancel drop
                </button>
              </form>
            </details>
          )}
          <div className="grid gap-5 lg:grid-cols-2">
            <section className="surface-soft p-6 sm:p-8">
              <div className="flex items-center justify-between gap-4">
                <h2 className="text-xl font-semibold">Recent entries</h2>
                <Users className="h-5 w-5 accent" />
              </div>
              <div className="mt-6 space-y-3">
                {entries.data?.items.slice(0, 8).map((entry) => (
                  <div
                    key={entry.entry_id}
                    className="grid gap-2 rounded-[var(--radius-control)] bg-white/[0.035] p-4 sm:grid-cols-[1fr_auto] sm:items-center"
                  >
                    <p className="truncate font-mono text-xs muted">
                      {entry.public_entry_id}
                    </p>
                    <div className="flex items-center gap-3">
                      <StatusBadge value={entry.status} />
                      <span className="text-xs muted">
                        Rank {entry.rank ?? "pending"}
                      </span>
                    </div>
                  </div>
                ))}
                {entries.data?.items.length === 0 && (
                  <p className="text-sm muted">No accepted entries yet.</p>
                )}
              </div>
              <ErrorMessage error={entries.error} />
            </section>
            <section className="surface-soft p-6 sm:p-8">
              <div className="flex items-center justify-between gap-4">
                <h2 className="text-xl font-semibold">Audit trail</h2>
                <ShieldCheck className="h-5 w-5 accent" />
              </div>
              <div className="mt-6 space-y-5">
                {audit.data?.items.slice(0, 8).map((event) => (
                  <div
                    className="grid grid-cols-[auto_1fr] gap-4"
                    key={event.id}
                  >
                    <CheckCircle2 className="mt-0.5 h-4 w-4 accent" />
                    <div>
                      <p className="text-sm font-semibold">
                        {event.event_type.replaceAll("_", " ")}
                      </p>
                      <p className="mt-1 text-xs muted">
                        {time(event.created_at)}
                      </p>
                    </div>
                  </div>
                ))}
                {audit.data?.items.length === 0 && (
                  <p className="text-sm muted">No audit events yet.</p>
                )}
              </div>
              <ErrorMessage error={audit.error} />
            </section>
          </div>
        </>
      )}
    </div>
  );
}

export function AttackLab() {
  const [runId, setRunId] = useState<string | null>(null);
  const action = useAction<Schema["RunAccepted"]>();
  const stop = useAction();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: async () =>
      (await (
        await fetch("/api/health/ready")
      ).json()) as Schema["ReadyHealth"],
  });
  const runs = useQuery({
    queryKey: ["lab-runs"],
    queryFn: () => api<Page<Schema["RunSummary"]>>("/admin/lab/runs"),
    enabled: !!health.data?.capabilities.lab,
    refetchInterval: 3000,
  });
  const selected = runId ?? runs.data?.items[0]?.run_id;
  const run = useQuery({
    queryKey: ["lab-run", selected],
    queryFn: () => api<Schema["RunDetail"]>(`/admin/lab/runs/${selected}`),
    enabled: !!selected,
    refetchInterval: 2000,
  });
  const report = run.data?.report;
  const offerData = report
    ? [
        {
          cohort: "People",
          rate: Math.round((report.allocation.human.win_rate ?? 0) * 100),
        },
        {
          cohort: "Automated",
          rate: Math.round((report.allocation.bot.win_rate ?? 0) * 100),
        },
      ]
    : [];
  return (
    <div className="pb-16">
      <PageHeader
        eyebrow="Adversarial evidence"
        title="Break the rush before users do."
        body="Run bounded, measured traffic through ordinary authentication, entry, allocation, and confirmation paths. The lab is isolated to demo deployments."
        action={<FlaskConical className="h-9 w-9 accent" strokeWidth={1.5} />}
      />
      {health.isPending ? (
        <LoadingBlock label="Checking lab availability" />
      ) : !health.data?.capabilities.lab ? (
        <EmptyState
          title="Lab is safely disabled"
          body="Attack traffic can run only when the server uses the isolated demo profile and lab capability."
        />
      ) : (
        <>
          <form
            className="surface grid gap-5 p-7 sm:p-9 md:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              const body = Object.fromEntries(
                [...f.entries()].map(([k, v]) => [
                  k,
                  k === "scenario" ? v : Number(v),
                ]),
              );
              action.mutate(
                { path: "/admin/lab/runs", body },
                { onSuccess: (result) => setRunId(result.run_id) },
              );
            }}
          >
            <div className="md:col-span-2">
              <h2 className="text-2xl font-semibold">
                Configure measured workload
              </h2>
              <p className="mt-2 text-sm muted">
                Every run is capped and records delivered traffic separately
                from requested traffic.
              </p>
            </div>
            <label>
              <span className="field-label">Scenario</span>
              <select className="field" name="scenario">
                {[
                  "normal",
                  "early_bot",
                  "retry_flood",
                  "credential_farm",
                  "reconnect",
                  "expiry_race",
                  "policy_compare",
                ].map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </label>
            {(
              [
                ["human_actors", "Human identities", 5, 0, 50000],
                ["bot_actors", "Bot identities", 5, 0, 50000],
                ["target_rps", "Target HTTP requests / second", 5, 1, 2000],
                ["duration_seconds", "Duration (seconds)", 10, 1, 300],
                ["retries_per_actor", "Retries per identity", 2, 0, 20],
                ["trials", "Independent trials", 1, 1, 20],
                ["drop_capacity", "Seats per trial", 3, 1, 500],
              ] as const
            ).map(([name, label, value, min, max]) => (
              <label key={name}>
                <span className="field-label">{label}</span>
                <input
                  className="field"
                  name={name}
                  type="number"
                  required
                  min={min}
                  max={max}
                  defaultValue={value}
                />
              </label>
            ))}
            <button
              className="button md:col-span-2 md:justify-self-start"
              disabled={
                action.isPending ||
                runs.data?.items.some((r) =>
                  ["QUEUED", "RUNNING", "STOPPING"].includes(r.status),
                )
              }
            >
              {action.isPending
                ? "Queueing run..."
                : "Run controlled simulation"}
            </button>
          </form>
          <ErrorMessage
            error={action.error ?? run.error ?? runs.error ?? stop.error}
          />
          {run.data && (
            <TicketCard className="mt-6 p-7 sm:p-9">
              <div className="flex flex-wrap items-start justify-between gap-5">
                <div>
                  <StatusBadge value={run.data.status} />
                  <h2 className="mt-5 text-3xl font-semibold tracking-tight">
                    {run.data.scenario.replaceAll("_", " ")}
                  </h2>
                  <p className="mt-2 text-sm muted">
                    {run.data.progress.message} (
                    {run.data.progress.completed_steps}/
                    {run.data.progress.total_steps} steps)
                  </p>
                </div>
                <span className="mono text-xs muted">{run.data.run_id}</span>
              </div>
              {run.data.error && (
                <ErrorMessage error={new Error(run.data.error.message)} />
              )}
              {["QUEUED", "RUNNING"].includes(run.data.status) && (
                <button
                  className="button-danger mt-6"
                  disabled={stop.isPending}
                  onClick={() =>
                    stop.mutate({ path: `/admin/lab/runs/${selected}/stop` })
                  }
                >
                  Stop run
                </button>
              )}
              {report && (
                <div className="mt-8 space-y-6 border-t border-white/10 pt-8">
                  <div className="grid grid-cols-2 gap-x-5 md:grid-cols-4">
                    <Metric
                      label="Achieved RPS"
                      value={
                        report.workload.achieved_rps?.toFixed(1) ?? "Unmeasured"
                      }
                    />
                    <Metric
                      label="Successful p95"
                      value={
                        report.performance.successful_request_latency_ms.p95 ==
                        null
                          ? "Unmeasured"
                          : `${report.performance.successful_request_latency_ms.p95.toFixed(0)} ms`
                      }
                    />
                    <Metric
                      label="Dropped iterations"
                      value={report.workload.dropped_iterations}
                    />
                    <Metric
                      label="Unexpected 5xx"
                      value={report.performance.unexpected_5xx}
                    />
                  </div>

                  <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
                    <section className="surface-soft p-6">
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <p className="text-sm font-semibold">
                            Initial offer rate
                          </p>
                          <p className="mt-1 text-xs muted">
                            Measured per eligible identity cohort.
                          </p>
                        </div>
                        <BarChart3 className="h-5 w-5 accent" />
                      </div>
                      <div className="mt-6 h-60">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={offerData}
                            margin={{ top: 8, right: 8, left: -16, bottom: 0 }}
                          >
                            <XAxis
                              dataKey="cohort"
                              axisLine={false}
                              tickLine={false}
                              tick={{ fill: "#a6aa9e", fontSize: 12 }}
                            />
                            <YAxis
                              domain={[0, 100]}
                              unit="%"
                              axisLine={false}
                              tickLine={false}
                              tick={{ fill: "#a6aa9e", fontSize: 12 }}
                            />
                            <Tooltip
                              cursor={{ fill: "rgba(255,255,255,0.04)" }}
                              contentStyle={{
                                background: "#171915",
                                border: "1px solid rgba(255,255,255,0.12)",
                                borderRadius: 14,
                              }}
                              formatter={(value) => [`${value}%`, "Offer rate"]}
                            />
                            <Bar
                              dataKey="rate"
                              fill="#c9ff4a"
                              radius={[8, 8, 0, 0]}
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </section>

                    <section className="surface-soft flex flex-col justify-between p-6">
                      <div>
                        <div className="flex items-center justify-between gap-4">
                          <p className="text-sm font-semibold">
                            Inventory integrity
                          </p>
                          <StatusBadge
                            value={
                              report.integrity.audit_pass
                                ? "verified"
                                : "failed"
                            }
                          />
                        </div>
                        <p className="mt-6 text-4xl font-semibold tracking-tight">
                          {report.integrity.audit_pass
                            ? "Audit passed"
                            : "Review required"}
                        </p>
                        <p className="mt-3 text-sm muted">
                          Oversold seats: {report.integrity.oversell_count}.
                          Duplicate active owners:{" "}
                          {report.integrity.duplicate_active_owners}.
                        </p>
                        <p className="mt-4 text-sm muted">
                          Bot advantage:{" "}
                          {report.allocation.bot_advantage ??
                            report.allocation.undefined_reason ??
                            "Not measurable"}
                          .
                        </p>
                      </div>
                      <a
                        className="button mt-8 self-start"
                        href={`/api/v1/admin/lab/runs/${selected}/export`}
                        download="fairdrop-report.json"
                      >
                        <Download className="h-4 w-4" /> Export evidence
                      </a>
                    </section>
                  </div>

                  <details className="surface-soft p-6">
                    <summary className="cursor-pointer font-semibold">
                      Method notes and raw evidence
                    </summary>
                    <ul className="mt-5 space-y-2 text-sm muted">
                      {report.limitations.map((limitation) => (
                        <li key={limitation}>- {limitation}</li>
                      ))}
                    </ul>
                    <pre className="mt-6 max-h-96 overflow-auto rounded-[var(--radius-control)] bg-black/20 p-4 text-xs muted">
                      {JSON.stringify(report, null, 2)}
                    </pre>
                  </details>
                </div>
              )}
            </TicketCard>
          )}
          <section className="mt-8 surface p-7 sm:p-9">
            <h2 className="text-xl font-semibold">Run history</h2>
            <div className="mt-5 space-y-2">
              {runs.data?.items.map((item) => (
                <button
                  className="flex w-full items-center justify-between gap-4 rounded-[var(--radius-control)] border border-white/8 bg-white/[0.025] p-4 text-left transition-colors hover:bg-white/[0.05]"
                  key={item.run_id}
                  onClick={() => setRunId(item.run_id)}
                >
                  <span>
                    <span className="block font-semibold">
                      {item.scenario.replaceAll("_", " ")}
                    </span>
                    <span className="mt-1 block font-mono text-[11px] muted">
                      {item.run_id}
                    </span>
                  </span>
                  <StatusBadge value={item.status} />
                </button>
              ))}
              {runs.data?.items.length === 0 && (
                <p className="text-sm muted">No lab runs yet.</p>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

export function ProfilePage() {
  const session = useSession();
  const action = useAction();
  if (!session.data) {
    return (
      <EmptyState
        title="Sign in to edit your profile"
        body="Your durable session reconnects entries, offers, and receipts across refreshes."
        action={
          <Link className="button" to="/sign-in">
            Sign in
          </Link>
        }
      />
    );
  }
  return (
    <div className="mx-auto max-w-4xl pb-16">
      <PageHeader
        eyebrow="Identity"
        title="Your durable participant profile."
        body="One verified identity carries your entries, offer state, and confirmations across refreshes and temporary failures."
      />
      <section className="surface mb-5 grid gap-6 p-7 sm:grid-cols-[1fr_auto] sm:items-center sm:p-9">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-2xl font-semibold">
              {session.data.principal.display_name}
            </h2>
            <StatusBadge value={session.data.principal.role} />
          </div>
          <p className="mt-3 text-sm muted">Public account ID</p>
          <p className="mt-1 break-all font-mono text-xs">
            {session.data.principal.public_id}
          </p>
        </div>
        <CopyButton
          value={session.data.principal.public_id}
          label="Copy account ID"
        />
      </section>
      <form
        className="surface-soft space-y-5 p-7 sm:p-9"
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          action.mutate({
            path: "/profile",
            method: "PATCH",
            body: Object.fromEntries(f),
          });
        }}
      >
        <label>
          <span className="field-label">Display name</span>
          <input
            className="field"
            name="display_name"
            required
            maxLength={100}
            defaultValue={session.data.principal.display_name}
          />
        </label>
        <label>
          <span className="field-label">IANA timezone</span>
          <input
            className="field"
            name="timezone"
            required
            defaultValue={session.data.principal.timezone}
          />
        </label>
        <button className="button" disabled={action.isPending}>
          {action.isPending ? "Saving..." : "Save profile"}
        </button>
        <ErrorMessage error={action.error} />
        {action.isSuccess && (
          <p className="text-sm accent" role="status">
            Profile saved.
          </p>
        )}
      </form>
    </div>
  );
}
