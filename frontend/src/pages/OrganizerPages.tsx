import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { TicketCard } from "../components/Ticket";
import { ErrorMessage } from "../components/State";
import { api, time, useAction, useSession } from "../lib/api/client";
import type { Drop, Page, Schema } from "../lib/api/client";

export function OrganizerDashboard() {
  const drops = useQuery({
    queryKey: ["admin-drops"],
    queryFn: () => api<Page<Schema["DropSummary"]>>("/admin/drops"),
  });
  return (
    <div className="space-y-10 pt-10">
      <div className="flex flex-wrap gap-6 justify-between">
        <div>
          <h1 className="text-4xl font-bold">Organizer dashboard</h1>
          <p className="text-white/60 mt-3">
            Manage invitations, draw proofs, and seat inventory.
          </p>
        </div>
        <Link className="button" to="/organizer/new">
          Create drop
        </Link>
      </div>
      <ErrorMessage error={drops.error} />
      {drops.isPending && <p>Loading your drops…</p>}
      {drops.data?.items.length === 0 && (
        <p>Create your first drop to invite participants.</p>
      )}
      <div className="grid gap-6 md:grid-cols-2">
        {drops.data?.items.map((d) => (
          <TicketCard className="p-8 space-y-4" key={d.id}>
            <h2 className="text-2xl font-bold">{d.title}</h2>
            <p>
              {d.phase} · {d.capacity} seats · {d.mode}
            </p>
            <Link className="underline" to={`/organizer/drops/${d.id}`}>
              Manage drop
            </Link>
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
    <div className="pt-10 max-w-2xl space-y-8">
      <h1 className="text-4xl font-bold">Create drop</h1>
      <form
        className="grid gap-5"
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
        <label>
          Title
          <input className="field mt-2" name="title" required maxLength={200} />
        </label>
        <label>
          Description
          <textarea
            className="field mt-2"
            name="description"
            maxLength={10000}
          />
        </label>
        <label>
          Category
          <input
            className="field mt-2"
            name="category"
            required
            maxLength={80}
            defaultValue="workshop"
          />
        </label>
        <label>
          Location type
          <select className="field mt-2" name="location_type">
            <option value="venue">Venue</option>
            <option value="online">Online</option>
          </select>
        </label>
        <label>
          Location
          <input
            className="field mt-2"
            name="location_label"
            required
            maxLength={200}
          />
        </label>
        <label>
          Seats
          <input
            className="field mt-2"
            name="capacity"
            type="number"
            min={1}
            max={500}
            defaultValue={10}
            required
          />
        </label>
        <label>
          Entry start (your local time)
          <input
            className="field mt-2"
            name="starts_at"
            type="datetime-local"
            required
          />
        </label>
        <label>
          Entry end (your local time)
          <input
            className="field mt-2"
            name="ends_at"
            type="datetime-local"
            required
          />
        </label>
        <label>
          Confirmation window (seconds)
          <input
            className="field mt-2"
            name="confirmation_seconds"
            type="number"
            min={1}
            max={604800}
            defaultValue={300}
            required
          />
        </label>
        <button className="button" disabled={action.isPending}>
          Save draft
        </button>
        <ErrorMessage error={action.error} />
      </form>
    </div>
  );
}

function DropEditor({ drop }: { drop: Drop }) {
  const action = useAction();
  return (
    <details className="rounded-3xl border border-white/20 p-6">
      <summary>Edit drop details</summary>
      <form
        className="space-y-4 mt-6"
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
        <label>
          Title
          <input
            className="field mt-2"
            name="title"
            required
            maxLength={200}
            defaultValue={drop.title}
          />
        </label>
        <label>
          Description
          <textarea
            className="field mt-2"
            name="description"
            maxLength={10000}
            defaultValue={drop.description}
          />
        </label>
        <label>
          Location
          <input
            className="field mt-2"
            name="location_label"
            required
            maxLength={200}
            defaultValue={drop.location_label}
          />
        </label>
        {drop.phase === "DRAFT" && (
          <>
            <label>
              Seats
              <input
                className="field mt-2"
                name="capacity"
                required
                type="number"
                min={1}
                max={500}
                defaultValue={drop.capacity}
              />
            </label>
            <label>
              Confirmation window (seconds)
              <input
                className="field mt-2"
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
        <button className="button" disabled={action.isPending}>
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
  return (
    <div className="space-y-8 pt-10">
      <ErrorMessage error={drop.error ?? action.error ?? metrics.error} />
      {drop.data && (
        <>
          <h1 className="text-4xl font-bold">{drop.data.title}</h1>
          <p>
            {drop.data.phase} · {time(drop.data.starts_at)} —{" "}
            {time(drop.data.ends_at)}
          </p>
          {drop.data.phase === "DRAFT" && (
            <TicketCard className="p-8 space-y-5">
              <h2 className="text-xl font-bold">Invite existing accounts</h2>
              <label>
                Public account IDs (one per line)
                <textarea
                  className="field mt-3"
                  value={ids}
                  onChange={(e) => setIds(e.target.value)}
                />
              </label>
              <div className="flex flex-wrap gap-4">
                <button
                  className="button"
                  disabled={action.isPending || !ids.trim()}
                  onClick={() =>
                    command("eligibility", {
                      user_public_ids: ids.split(/[\s,]+/).filter(Boolean),
                    })
                  }
                >
                  Grant invitations
                </button>
                <button
                  className="button"
                  disabled={action.isPending}
                  onClick={() => command("publish")}
                >
                  Publish drop
                </button>
              </div>
              <button
                className="button"
                disabled={
                  action.isPending ||
                  ids
                    .trim()
                    .split(/[\s,]+/)
                    .filter(Boolean).length !== 1
                }
                onClick={() =>
                  action.mutate({
                    path: `/admin/drops/${id}/eligibility/${encodeURIComponent(ids.trim())}`,
                    method: "DELETE",
                  })
                }
              >
                Revoke this invitation
              </button>
              <p>Invitations and allocation rules are locked at publication.</p>
            </TicketCard>
          )}
          <DropEditor key={drop.data.id} drop={drop.data} />
          <div className="flex flex-wrap gap-4">
            {drop.data.phase === "SCHEDULED" && (
              <button
                className="button"
                disabled={action.isPending}
                onClick={() => command("open")}
              >
                Open when scheduled
              </button>
            )}
            {drop.data.phase === "OPEN" && (
              <button
                className="button"
                disabled={action.isPending}
                onClick={() => command("close")}
              >
                Close after deadline
              </button>
            )}
            {["CLOSED", "DRAWING"].includes(drop.data.phase) && (
              <button
                className="button"
                disabled={action.isPending}
                onClick={() => command("draw")}
              >
                Start / resume draw
              </button>
            )}
            <Link className="button" to={`/drops/${id}/proof`}>
              Draw proof
            </Link>
            <a
              className="button"
              href={`/api/v1/admin/drops/${id}/entries/export`}
            >
              Export entries CSV
            </a>
          </div>
          {metrics.data && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                ["Entries", metrics.data.entered_count],
                ["Offered", metrics.data.active_reservations],
                ["Confirmed", metrics.data.confirmed_seats],
                ["Free", metrics.data.free_seats],
              ].map(([label, n]) => (
                <TicketCard className="p-6" key={label}>
                  <p>{label}</p>
                  <p className="text-4xl mt-3">{n}</p>
                </TicketCard>
              ))}
              <p className="col-span-full">
                Inventory audit:{" "}
                {metrics.data.integrity_ok
                  ? "Passing"
                  : "Requires investigation"}
              </p>
            </div>
          )}
          {!["COMPLETED", "CANCELLED"].includes(drop.data.phase) && (
            <form
              className="flex flex-wrap gap-4"
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
                placeholder="Cancellation reason"
                onChange={(e) => setReason(e.target.value)}
              />
              <button className="button" disabled={action.isPending}>
                Cancel drop
              </button>
            </form>
          )}
          <h2 className="text-2xl font-bold">Recent entries</h2>
          {entries.data?.items.map((e) => (
            <p key={e.entry_id} className="break-all">
              {e.public_entry_id} · {e.status} · Rank {e.rank ?? "pending"}
            </p>
          ))}
          <ErrorMessage error={entries.error} />
          <h2 className="text-2xl font-bold">Audit events</h2>
          {audit.data?.items.map((e) => (
            <p key={e.id}>
              {time(e.created_at)} · {e.event_type}
            </p>
          ))}
          <ErrorMessage error={audit.error} />
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
  return (
    <div className="space-y-8 pt-10">
      <h1 className="text-4xl font-bold">Attack lab</h1>
      <p className="text-white/60">
        Measured invitation and allocation workloads against this isolated demo
        deployment.
      </p>
      {health.isPending ? (
        <p>Checking lab availability…</p>
      ) : !health.data?.capabilities.lab ? (
        <p>The lab is available only in an enabled demo deployment.</p>
      ) : (
        <>
          <form
            className="grid md:grid-cols-2 gap-5"
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
            <label>
              Scenario
              <select className="field mt-2" name="scenario">
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
                {label}
                <input
                  className="field mt-2"
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
              className="button"
              disabled={
                action.isPending ||
                runs.data?.items.some((r) =>
                  ["QUEUED", "RUNNING", "STOPPING"].includes(r.status),
                )
              }
            >
              Run simulation
            </button>
          </form>
          <ErrorMessage
            error={action.error ?? run.error ?? runs.error ?? stop.error}
          />
          {run.data && (
            <TicketCard className="p-8 space-y-5">
              <h2 className="text-3xl font-bold">{run.data.status}</h2>
              <p>
                {run.data.progress.message} ·{" "}
                {run.data.progress.completed_steps}/
                {run.data.progress.total_steps}
              </p>
              {run.data.error && (
                <ErrorMessage error={new Error(run.data.error.message)} />
              )}
              {["QUEUED", "RUNNING"].includes(run.data.status) && (
                <button
                  className="button"
                  disabled={stop.isPending}
                  onClick={() =>
                    stop.mutate({ path: `/admin/lab/runs/${selected}/stop` })
                  }
                >
                  Stop run
                </button>
              )}
              {run.data.report && (
                <>
                  <a
                    className="button"
                    href={`/api/v1/admin/lab/runs/${selected}/export`}
                    download="report.json"
                  >
                    Export measured report
                  </a>
                  <p>
                    Initial offer rates: humans{" "}
                    {run.data.report.allocation.human.win_rate ?? "undefined"},
                    bots{" "}
                    {run.data.report.allocation.bot.win_rate ?? "undefined"}
                  </p>
                  <p>
                    Bot advantage:{" "}
                    {run.data.report.allocation.bot_advantage ??
                      run.data.report.allocation.undefined_reason}
                  </p>
                  <p>
                    Inventory audit:{" "}
                    {run.data.report.integrity.audit_pass
                      ? "Passing"
                      : "Requires investigation"}
                  </p>
                  <p>
                    Achieved HTTP RPS:{" "}
                    {run.data.report.workload.achieved_rps?.toFixed(1) ??
                      "unmeasured"}{" "}
                    · Dropped iterations:{" "}
                    {run.data.report.workload.dropped_iterations}
                  </p>
                  <p>
                    Successful request p95:{" "}
                    {run.data.report.performance.successful_request_latency_ms.p95?.toFixed(
                      1,
                    ) ?? "unmeasured"}{" "}
                    ms
                  </p>
                  <ul className="space-y-2 text-sm text-white/60">
                    {run.data.report.limitations.map((l) => (
                      <li key={l}>{l}</li>
                    ))}
                  </ul>
                  <details>
                    <summary>Full measured report</summary>
                    <pre className="overflow-auto text-sm mt-4">
                      {JSON.stringify(run.data.report, null, 2)}
                    </pre>
                  </details>
                </>
              )}
            </TicketCard>
          )}
          <h2 className="text-xl font-bold">Run history</h2>
          {runs.data?.items.map((r) => (
            <button
              className="block underline"
              key={r.run_id}
              onClick={() => setRunId(r.run_id)}
            >
              {r.scenario} · {r.status} · {r.run_id}
            </button>
          ))}
        </>
      )}
    </div>
  );
}

export function ProfilePage() {
  const session = useSession();
  const action = useAction();
  if (!session.data)
    return <Link to="/sign-in">Sign in to edit your profile</Link>;
  return (
    <div className="pt-10 max-w-lg space-y-6">
      <h1 className="text-3xl font-bold">My profile</h1>
      <p className="break-all">
        Public account ID: {session.data.principal.public_id}
      </p>
      <form
        className="space-y-5"
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
          Display name
          <input
            className="field mt-2"
            name="display_name"
            required
            maxLength={100}
            defaultValue={session.data.principal.display_name}
          />
        </label>
        <label>
          IANA timezone
          <input
            className="field mt-2"
            name="timezone"
            required
            defaultValue={session.data.principal.timezone}
          />
        </label>
        <button className="button" disabled={action.isPending}>
          Save profile
        </button>
        <ErrorMessage error={action.error} />
        {action.isSuccess && <p role="status">Profile saved.</p>}
      </form>
    </div>
  );
}
