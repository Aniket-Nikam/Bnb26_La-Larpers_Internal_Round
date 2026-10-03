import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Ticket, Lock, UserPlus } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { TicketCard, TicketDivider } from "../components/Ticket";
import { ErrorMessage } from "../components/State";
import {
  api,
  time,
  useAction,
  useLogin,
  usePasswordLogin,
  useRegister,
  useSession,
} from "../lib/api/client";
import type { Drop, Entry, Page, Schema } from "../lib/api/client";

export function LandingPage() {
  const [q, setQ] = useState("");
  const [cursor, setCursor] = useState<string | null>(null);
  const drops = useQuery({
    queryKey: ["drops", q, cursor],
    queryFn: () =>
      api<Page<Schema["DropSummary"]>>(
        `/drops?q=${encodeURIComponent(q)}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`,
      ),
  });
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-12 pt-16"
    >
      <div className="space-y-8">
        <div className="inline-flex gap-2 text-sm">
          <ShieldCheck /> Provably fair lottery
        </div>
        <h1 className="text-6xl md:text-8xl font-bold tracking-tighter">
          Enter once.
          <br />
          <span className="text-white/40">Verify securely.</span>
        </h1>
        <p className="text-lg text-white/60 max-w-xl">
          Create an account or use an invitation credential, save one entry, and
          verify the published draw.
        </p>
      </div>
      <label className="block">
        Search drops
        <input
          aria-label="Search drops"
          className="field mt-2"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setCursor(null);
          }}
        />
      </label>
      <ErrorMessage error={drops.error} />
      {drops.isPending && <p role="status">Loading drops…</p>}
      {drops.data?.items.length === 0 && (
        <p>No published drops match this search.</p>
      )}
      <div className="grid gap-6 md:grid-cols-2">
        {drops.data?.items.map((drop) => (
          <Link key={drop.id} to={`/drops/${drop.id}`}>
            <TicketCard className="p-8 space-y-5 hover:bg-white/10">
              <Ticket />
              <h2 className="text-3xl font-bold">{drop.title}</h2>
              <p>
                {drop.organizer.display_name} · {drop.capacity} seats
              </p>
              <p className="text-white/60">
                {drop.phase} ·{" "}
                {drop.mode === "FCFS_DEMO" ? "Demo FCFS comparison" : "Lottery"}
              </p>
              <p>{time(drop.starts_at)}</p>
            </TicketCard>
          </Link>
        ))}
      </div>
      {drops.data?.next_cursor && (
        <button
          className="button"
          onClick={() => setCursor(drops.data!.next_cursor)}
        >
          Next page
        </button>
      )}
    </motion.div>
  );
}

function SavedEntry({ entry }: { entry: Entry }) {
  const action = useAction<Entry>();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  // Use server_time to correct the local countdown. The server decides the deadline.
  const [observed] = useState(() => Date.now());
  const remaining = entry.reservation
    ? Math.max(
        0,
        Math.ceil(
          (Date.parse(entry.reservation.expires_at) -
            (Date.parse(entry.server_time) + now - observed)) /
            1000,
        ),
      )
    : 0;
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">{entry.status}</h2>
      <p className="break-all">Receipt: {entry.receipt_id}</p>
      {entry.rank && <p>Draw rank: {entry.rank}</p>}
      {entry.status === "OFFERED" && entry.reservation && (
        <>
          <p>
            Confirm within {remaining} seconds. Deadline:{" "}
            {time(entry.reservation.expires_at)}
          </p>
          <button
            className="button"
            disabled={action.isPending || remaining === 0}
            onClick={() =>
              action.mutate({
                path: `/reservations/${entry.reservation!.id}/confirm`,
              })
            }
          >
            Confirm seat
          </button>
        </>
      )}
      {entry.status === "CONFIRMED" && <p>Your seat is confirmed.</p>}
      {entry.status === "WAITLISTED" && (
        <p>
          Your saved entry is on the waitlist. This view updates automatically.
        </p>
      )}
      {entry.status === "EXPIRED" && <p>The confirmation deadline passed.</p>}
      {entry.status === "CANCELLED" && (
        <p>The organizer cancelled this drop.</p>
      )}
      <Link className="underline" to={`/entries/${entry.entry_id}`}>
        View receipt
      </Link>
      <ErrorMessage error={action.error} />
    </div>
  );
}

export function DropDetail() {
  const { id } = useParams();
  const session = useSession();
  const action = useAction<Entry>();
  const drop = useQuery({
    queryKey: ["drop", id],
    queryFn: () => api<Drop>(`/drops/${id}`),
    refetchInterval: 5000,
  });
  const state = useQuery({
    queryKey: ["state", id, session.data?.principal.id],
    queryFn: () => api<Schema["MyDropState"]>(`/drops/${id}/me`),
    enabled: !!session.data && !!drop.data && drop.data.phase !== "DRAFT",
    refetchInterval: 3000,
  });
  if (drop.isPending) return <p role="status">Loading drop…</p>;
  if (!drop.data) return <ErrorMessage error={drop.error} />;
  const d = drop.data;
  return (
    <div className="max-w-2xl mx-auto pt-10 space-y-5">
      <TicketCard>
        <div className="p-10 space-y-6">
          <Ticket className="w-12 h-12" />
          <h1 className="text-4xl font-bold">{d.title}</h1>
          <p>{d.description}</p>
          <p>
            {d.phase} · {d.capacity} seats · {d.mode}
          </p>
          <p>
            {time(d.starts_at)} — {time(d.ends_at)}
          </p>
          <p>{d.location_label}</p>
          {d.cancellation_reason && <p>{d.cancellation_reason}</p>}
        </div>
        <TicketDivider />
        <div className="p-10 space-y-5">
          {session.isPending ? (
            <p>Checking session…</p>
          ) : !session.data ? (
            <Link className="button" to="/sign-in">
              Sign in to check your invitation
            </Link>
          ) : state.isPending ? (
            <p role="status">Checking invitation…</p>
          ) : state.data?.entry ? (
            <SavedEntry
              key={`${state.data.entry.entry_id}-${state.data.entry.server_time}`}
              entry={state.data.entry}
            />
          ) : (
            <>
              <p>
                {state.data?.eligibility.eligible
                  ? "Your invitation is eligible."
                  : "An invitation for this drop is required."}
              </p>
              <button
                className="button"
                disabled={
                  action.isPending ||
                  !state.data?.eligibility.eligible ||
                  d.phase !== "OPEN"
                }
                onClick={() => action.mutate({ path: `/drops/${id}/entries` })}
              >
                {action.isPending ? "Saving…" : "Enter drop"}
              </button>
            </>
          )}
          <ErrorMessage error={state.error ?? action.error ?? session.error} />
          <Link className="underline" to={`/drops/${id}/proof`}>
            View draw proof
          </Link>
          {d.seed_commitment && (
            <p className="break-all text-sm text-white/50">
              Seed commitment: {d.seed_commitment}
            </p>
          )}
        </div>
      </TicketCard>
    </div>
  );
}

export function SignInPage() {
  const [invitationMode, setInvitationMode] = useState(false);
  const [code, setCode] = useState("");
  const login = useLogin();
  const passwordLogin = usePasswordLogin();
  const navigate = useNavigate();
  return (
    <div className="max-w-md mx-auto pt-16">
      <TicketCard className="p-10 space-y-8">
        <Lock />
        <h1 className="text-3xl font-bold">Sign in</h1>
        <div className="flex gap-3">
          <button
            className={!invitationMode ? "button" : "underline"}
            type="button"
            onClick={() => setInvitationMode(false)}
          >
            Email
          </button>
          <button
            className={invitationMode ? "button" : "underline"}
            type="button"
            onClick={() => setInvitationMode(true)}
          >
            Invitation credential
          </button>
        </div>
        <form
          className="space-y-6"
          onSubmit={(e) => {
            e.preventDefault();
            const fields = new FormData(e.currentTarget);
            const options = {
              onSuccess: () => {
                setCode("");
                navigate("/drops");
              },
            };
            if (invitationMode) login.mutate(code, options);
            else
              passwordLogin.mutate(
                {
                  email: String(fields.get("email")),
                  password: String(fields.get("password")),
                },
                options,
              );
          }}
        >
          {invitationMode ? (
            <label className="block">
              Invitation credential
              <input
                className="field mt-3"
                type="password"
                autoComplete="off"
                required
                maxLength={256}
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </label>
          ) : (
            <>
              <label className="block">
                Email
                <input
                  className="field mt-3"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  maxLength={254}
                />
              </label>
              <label className="block">
                Password
                <input
                  className="field mt-3"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  minLength={8}
                  maxLength={128}
                />
              </label>
            </>
          )}
          <button
            className="button"
            disabled={login.isPending || passwordLogin.isPending}
          >
            Sign in
          </button>
          <ErrorMessage error={login.error ?? passwordLogin.error} />
        </form>
        <p>
          New visitor?{" "}
          <Link className="underline" to="/register">
            Create an account
          </Link>
        </p>
      </TicketCard>
    </div>
  );
}

export function RegisterPage() {
  const register = useRegister();
  const navigate = useNavigate();
  return (
    <div className="max-w-md mx-auto pt-16">
      <TicketCard className="p-10 space-y-8">
        <UserPlus />
        <h1 className="text-3xl font-bold">Create visitor account</h1>
        <form
          className="space-y-6"
          onSubmit={(event) => {
            event.preventDefault();
            const fields = new FormData(event.currentTarget);
            register.mutate(
              {
                display_name: String(fields.get("display_name")),
                email: String(fields.get("email")),
                password: String(fields.get("password")),
              },
              { onSuccess: () => navigate("/profile") },
            );
          }}
        >
          <label className="block">
            Display name
            <input
              className="field mt-3"
              name="display_name"
              required
              maxLength={100}
            />
          </label>
          <label className="block">
            Email
            <input
              className="field mt-3"
              name="email"
              type="email"
              autoComplete="email"
              required
              maxLength={254}
            />
          </label>
          <label className="block">
            Password
            <input
              className="field mt-3"
              name="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              maxLength={128}
            />
          </label>
          <button className="button" disabled={register.isPending}>
            Create account
          </button>
          <ErrorMessage error={register.error} />
        </form>
        <Link className="underline" to="/sign-in">
          Already have an account? Sign in
        </Link>
      </TicketCard>
    </div>
  );
}

export function ReceiptsPage() {
  const session = useSession();
  const receipts = useQuery({
    queryKey: ["receipts", session.data?.principal.id],
    queryFn: () => api<Page<Schema["Receipt"]>>("/entries"),
    enabled: !!session.data,
    refetchInterval: 5000,
  });
  if (!session.data) return <Link to="/sign-in">Sign in to view receipts</Link>;
  return (
    <div className="space-y-6 pt-10">
      <h1 className="text-3xl font-bold">My receipts</h1>
      <ErrorMessage error={receipts.error} />
      {receipts.isPending && <p>Loading receipts…</p>}
      {receipts.data?.items.length === 0 && (
        <p>You have no saved entries yet.</p>
      )}
      {receipts.data?.items.map((r) => (
        <TicketCard key={r.entry.entry_id} className="p-8">
          <Link className="underline" to={`/entries/${r.entry.entry_id}`}>
            {r.drop.title} · {r.entry.status}
          </Link>
        </TicketCard>
      ))}
    </div>
  );
}

export function ReceiptPage() {
  const { id } = useParams();
  const session = useSession();
  const receipt = useQuery({
    queryKey: ["receipt", id, session.data?.principal.id],
    queryFn: () => api<Schema["Receipt"]>(`/entries/${id}`),
    enabled: !!session.data,
    refetchInterval: 3000,
  });
  return (
    <div className="pt-10 space-y-6">
      <h1 className="text-3xl font-bold">Entry receipt</h1>
      <ErrorMessage error={receipt.error} />
      {!session.data && <Link to="/sign-in">Sign in to view this receipt</Link>}
      {receipt.data && (
        <TicketCard className="p-10 space-y-6">
          <h2>{receipt.data.drop.title}</h2>
          <SavedEntry
            key={receipt.data.entry.server_time}
            entry={receipt.data.entry}
          />
          <Link
            className="underline"
            to={`/drops/${receipt.data.drop.id}/proof`}
          >
            Verify draw proof
          </Link>
        </TicketCard>
      )}
    </div>
  );
}

export function ProofPage() {
  const { id } = useParams();
  const proof = useQuery({
    queryKey: ["proof", id],
    queryFn: () =>
      api<Schema["PublishedProof"] | Schema["PendingProof"]>(
        `/drops/${id}/proof`,
      ),
    refetchInterval: 5000,
  });
  return (
    <div className="space-y-6 pt-10">
      <h1 className="text-3xl font-bold">Public draw proof</h1>
      <ErrorMessage error={proof.error} />
      {proof.data && (
        <>
          <p>
            {proof.data.status === "pending"
              ? `Proof is pending (${proof.data.phase}).`
              : `${proof.data.entries.length} frozen entries · ${proof.data.algorithm_version}`}
          </p>
          {proof.data.status === "published" && (
            <a
              className="button"
              href={`/api/v1/drops/${id}/proof`}
              download="proof.json"
            >
              Download proof JSON
            </a>
          )}
          <pre className="overflow-auto rounded-3xl bg-white/5 p-6 text-sm">
            {JSON.stringify(proof.data, null, 2)}
          </pre>
        </>
      )}
    </div>
  );
}
