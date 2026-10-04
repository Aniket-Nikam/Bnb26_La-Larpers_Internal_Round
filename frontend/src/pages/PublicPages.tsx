import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowRight,
  CalendarDays,
  Camera,
  Check,
  CheckCircle2,
  Clock3,
  Download,
  Fingerprint,
  KeyRound,
  Lock,
  MapPin,
  RefreshCw,
  ScanFace,
  Search,
  ShieldCheck,
  Sparkles,
  Ticket,
  UserPlus,
  Users,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { TicketCard, TicketDivider } from "../components/Ticket";
import {
  EmptyState,
  LoadingBlock,
  Metric,
  PageHeader,
  StatusBadge,
} from "../components/Design";
import { ErrorMessage } from "../components/State";
import heroImage from "../assets/fairdrop-crowd.webp";
import {
  api,
  time,
  useAction,
  useLogin,
  usePasswordLogin,
  useRegister,
  useSession,
} from "../lib/api/client";
import type { Drop, Entry, Page, Schema, Session } from "../lib/api/client";

const phases = ["ALL", "SCHEDULED", "OPEN", "OFFERING", "COMPLETED"] as const;

function DropCard({ drop }: { drop: Schema["DropSummary"] }) {
  return (
    <Link className="group block" to={"/drops/" + drop.id}>
      <article className="surface-soft h-full overflow-hidden p-6 transition duration-300 group-hover:-translate-y-1 group-hover:border-white/20 sm:p-8">
        <div className="flex items-start justify-between gap-5">
          <StatusBadge value={drop.phase} />
          <Ticket className="h-5 w-5 accent" strokeWidth={1.7} />
        </div>
        <h3 className="mt-8 text-2xl font-semibold tracking-[-0.035em] sm:text-3xl">
          {drop.title}
        </h3>
        <p className="mt-3 text-sm muted">{drop.organizer.display_name}</p>
        <div className="mt-8 grid grid-cols-2 gap-5 border-t border-white/10 pt-6 text-sm">
          <div>
            <p className="muted">Seats</p>
            <p className="mt-1 font-mono text-lg">{drop.capacity}</p>
          </div>
          <div>
            <p className="muted">Allocation</p>
            <p className="mt-1 font-medium">
              {drop.mode === "FCFS_DEMO" ? "FCFS demo" : "Fair lottery"}
            </p>
          </div>
          <div className="col-span-2 flex items-center gap-2 muted">
            <CalendarDays className="h-4 w-4" />
            {time(drop.starts_at)}
          </div>
          <div className="col-span-2 flex items-center gap-2 muted">
            <MapPin className="h-4 w-4" />
            {drop.location_label}
          </div>
        </div>
      </article>
    </Link>
  );
}

function Discovery({ featured = false }: { featured?: boolean }) {
  const [q, setQ] = useState("");
  const [phase, setPhase] = useState<(typeof phases)[number]>("ALL");
  const [cursor, setCursor] = useState<string | null>(null);
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (phase !== "ALL") params.set("phase", phase);
  if (cursor) params.set("cursor", cursor);
  if (featured) params.set("limit", "4");
  const drops = useQuery({
    queryKey: ["drops", q, phase, cursor, featured],
    queryFn: () =>
      api<Page<Schema["DropSummary"]>>("/drops?" + params.toString()),
  });
  return (
    <section className={featured ? "py-20 sm:py-28" : "pb-20"}>
      <div className="mb-8 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">
            {featured
              ? "Drops open to everyone who qualifies."
              : "Find your next event."}
          </h2>
          <p className="mt-3 max-w-xl muted">
            Entry time never changes lottery rank. Join once before the window
            closes.
          </p>
        </div>
        {featured && (
          <Link className="button-secondary" to="/drops">
            Browse all drops
            <ArrowRight className="h-4 w-4" />
          </Link>
        )}
      </div>
      {!featured && (
        <div className="surface-soft mb-8 grid gap-5 p-4 md:grid-cols-[1fr_auto] md:items-center">
          <label className="relative block">
            <span className="sr-only">Search drops</span>
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 muted" />
            <input
              aria-label="Search drops"
              className="field pl-11"
              placeholder="Search by event name"
              value={q}
              onChange={(event) => {
                setQ(event.target.value);
                setCursor(null);
              }}
            />
          </label>
          <div
            className="flex gap-2 overflow-x-auto"
            aria-label="Filter by status"
          >
            {phases.map((item) => (
              <button
                key={item}
                type="button"
                className={phase === item ? "button" : "button-ghost"}
                onClick={() => {
                  setPhase(item);
                  setCursor(null);
                }}
              >
                {item === "ALL" ? "All" : item.toLowerCase()}
              </button>
            ))}
          </div>
        </div>
      )}
      <ErrorMessage error={drops.error} />
      {drops.isPending && (
        <div className="grid gap-5 md:grid-cols-2">
          <LoadingBlock label="Loading drops" />
          <LoadingBlock label="Loading drops" />
        </div>
      )}
      {drops.data?.items.length === 0 && (
        <EmptyState
          title="No drops found"
          body="Try another search or return when a new event is published."
        />
      )}
      <div className="grid gap-5 md:grid-cols-2">
        {drops.data?.items.map((drop) => (
          <DropCard key={drop.id} drop={drop} />
        ))}
      </div>
      {!featured && drops.data?.next_cursor && (
        <button
          className="button-secondary mt-8"
          onClick={() => setCursor(drops.data!.next_cursor)}
        >
          Load more
        </button>
      )}
    </section>
  );
}

export function LandingPage() {
  const reduce = useReducedMotion();
  return (
    <>
      <section className="grid min-h-[calc(100dvh-72px)] items-center gap-10 py-12 md:grid-cols-[1.05fr_0.95fr] md:py-16">
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-3xl"
        >
          <p className="eyebrow">Fair entry. Verifiable outcome.</p>
          <h1 className="mt-5 text-5xl font-semibold leading-[0.94] tracking-[-0.065em] sm:text-6xl lg:text-7xl">
            Tickets without
            <br />
            <span className="muted">the speed race.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed muted">
            One identity gets one entry. Speed, retries, and expensive hardware
            never buy better odds.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link className="button" to="/drops">
              Explore live drops
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link className="button-secondary" to="/fairness">
              See how it works
            </Link>
          </div>
        </motion.div>
        <motion.figure
          initial={reduce ? false : { opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.9, delay: 0.08, ease: [0.16, 1, 0.3, 1] }}
          className="relative mx-auto w-full max-w-xl overflow-hidden rounded-[var(--radius-panel)]"
        >
          <img
            className="aspect-[4/5] w-full object-cover"
            src={heroImage}
            alt="A crowd represented as equal identities with selected seats highlighted"
            fetchPriority="high"
          />
          <figcaption className="absolute inset-x-4 bottom-4 rounded-[var(--radius-control)] border border-white/15 bg-[rgb(var(--canvas)/0.82)] p-4 backdrop-blur-xl">
            <div className="flex items-center gap-3">
              <ShieldCheck className="h-5 w-5 accent" />
              <div>
                <p className="text-sm font-semibold">
                  Request-independent ranking
                </p>
                <p className="mt-0.5 text-xs muted">
                  Accepted identities enter the same frozen pool.
                </p>
              </div>
            </div>
          </figcaption>
        </motion.figure>
      </section>

      <section className="grid border-y border-white/10 py-7 sm:grid-cols-3">
        <Metric label="Entry policy" value="One per identity" />
        <Metric label="Seat integrity" value="No overselling" />
        <Metric label="Public trust" value="Reproducible proof" />
      </section>

      <Discovery featured />

      <section className="grid gap-5 pb-20 md:grid-cols-[1.25fr_0.75fr]">
        <div className="surface relative overflow-hidden p-8 sm:p-10">
          <Fingerprint className="h-10 w-10 accent" strokeWidth={1.5} />
          <h2 className="mt-16 max-w-xl text-3xl font-semibold tracking-[-0.045em] sm:text-5xl">
            Repetition creates load, not extra chances.
          </h2>
          <p className="mt-5 max-w-xl leading-relaxed muted">
            Every accepted account maps to one durable entry. Lost responses,
            duplicate tabs, and retries recover the same receipt.
          </p>
          <Link
            className="link mt-8 inline-flex items-center gap-2"
            to="/fairness"
          >
            Explore the fairness model
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <div className="grid gap-5">
          <div className="surface-soft p-7">
            <Lock className="h-7 w-7 accent" />
            <h3 className="mt-8 text-xl font-semibold">
              State survives disruption
            </h3>
            <p className="mt-3 text-sm leading-relaxed muted">
              PostgreSQL stores entries, offers, confirmations, and audit
              events. Redis never owns a ticket.
            </p>
          </div>
          <div className="surface-soft bg-[rgb(var(--accent)/0.09)] p-7">
            <Sparkles className="h-7 w-7 accent" />
            <h3 className="mt-8 text-xl font-semibold">
              The draw can be checked
            </h3>
            <p className="mt-3 text-sm leading-relaxed muted">
              A committed seed, frozen manifest, disclosed algorithm, and public
              proof make the ranking reproducible.
            </p>
          </div>
        </div>
      </section>

      <section className="surface-soft mb-10 grid items-center gap-8 p-8 sm:p-12 md:grid-cols-[1fr_auto]">
        <div>
          <h2 className="text-3xl font-semibold tracking-[-0.04em]">
            Ready to enter without racing?
          </h2>
          <p className="mt-3 max-w-xl muted">
            Create an account, enter once during the open window, and keep one
            durable receipt.
          </p>
        </div>
        <Link className="button" to="/register">
          Create participant account
          <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </>
  );
}

export function DiscoveryPage() {
  return (
    <>
      <PageHeader
        eyebrow="Discovery"
        title="Every drop. No refresh race."
        body="Browse published events and enter at any point during the stated window."
      />
      <Discovery />
    </>
  );
}

export function FairnessPage() {
  const [botRequests, setBotRequests] = useState(12);
  const humans = 8;
  const bots = 2;
  const requestShare = Math.round(
    (bots * botRequests * 100) / (humans + bots * botRequests),
  );
  const identityShare = Math.round((bots * 100) / (humans + bots));
  return (
    <div className="pb-16">
      <PageHeader
        eyebrow="Fairness"
        title="Fast requests should not become extra tickets."
        body="FairDrop separates admission protection from allocation. Rate limits keep the service available, while the draw treats every accepted identity equally."
      />

      <section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="surface p-7 sm:p-9">
          <h2 className="text-2xl font-semibold tracking-tight">
            Try the request-volume model
          </h2>
          <p className="mt-3 text-sm leading-relaxed muted">
            This illustration uses eight people and two automated identities.
            Change how many requests each automated identity sends.
          </p>
          <label className="mt-10 block">
            <span className="field-label">
              Requests per automated identity: {botRequests}
            </span>
            <input
              className="w-full accent-[rgb(var(--accent))]"
              type="range"
              min="1"
              max="50"
              value={botRequests}
              onChange={(event) => setBotRequests(Number(event.target.value))}
            />
          </label>
          <p className="mt-8 text-xs leading-relaxed muted">
            Illustrative model only. It explains request influence, not measured
            allocation results.
          </p>
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="surface-soft p-7">
            <p className="text-sm font-semibold muted">Speed-based sale</p>
            <p className="metric-number mt-4">{requestShare}%</p>
            <p className="mt-2 text-sm muted">
              of request opportunities come from two automated identities
            </p>
            <p className="mt-10 text-sm leading-relaxed">
              More requests can dominate the race before legitimate participants
              are served.
            </p>
          </div>
          <div className="surface p-7 ring-1 ring-[rgb(var(--accent)/0.3)]">
            <p className="text-sm font-semibold accent">FairDrop lottery</p>
            <p className="metric-number mt-4">{identityShare}%</p>
            <p className="mt-2 text-sm muted">
              of accepted entries belong to those same two identities
            </p>
            <p className="mt-10 text-sm leading-relaxed">
              Duplicate attempts recover the original entry and never change its
              rank.
            </p>
          </div>
        </div>
      </section>

      <section className="py-20 sm:py-28">
        <h2 className="max-w-2xl text-3xl font-semibold tracking-[-0.04em] sm:text-5xl">
          A complete chain of custody for every seat.
        </h2>
        <div className="mt-10 grid gap-5 md:grid-cols-2">
          {(
            [
              [
                Users,
                "Accept",
                "One eligible identity commits one entry and receives a durable receipt.",
              ],
              [
                Lock,
                "Freeze",
                "The server seals the complete manifest when the entry window closes.",
              ],
              [
                Sparkles,
                "Rank",
                "A committed seed scores the frozen entries without using arrival time.",
              ],
              [
                CheckCircle2,
                "Confirm",
                "Timed offers own seats atomically. Expiry promotes the next original rank.",
              ],
            ] as const
          ).map(([Icon, title, body], index) => (
            <div
              className={
                index === 0 || index === 3
                  ? "surface p-7 sm:p-9"
                  : "surface-soft p-7 sm:p-9"
              }
              key={String(title)}
            >
              <Icon className="h-7 w-7 accent" strokeWidth={1.6} />
              <h3 className="mt-10 text-2xl font-semibold">{String(title)}</h3>
              <p className="mt-3 max-w-md leading-relaxed muted">
                {String(body)}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="surface-soft grid gap-8 p-8 sm:p-10 lg:grid-cols-[1fr_auto] lg:items-center">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight">
            Trust the proof, not the promise.
          </h2>
          <p className="mt-3 max-w-2xl muted">
            Published proofs contain pseudonymous entries, ranks, commitments,
            and the disclosed algorithm. Private identities stay private.
          </p>
        </div>
        <Link className="button" to="/drops">
          Choose a drop to verify
        </Link>
      </section>
    </div>
  );
}

function SavedEntry({ entry }: { entry: Entry }) {
  const action = useAction<Entry>();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
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
  const message = {
    ENTERED: "Your entry is saved. You can close this page and return later.",
    WAITLISTED:
      "Your place comes from the original published ranking. Expired offers promote the next rank.",
    OFFERED: "A seat is reserved for you until the server deadline.",
    CONFIRMED:
      "Your seat is secured and cannot be allocated to another participant.",
    EXPIRED:
      "The confirmation deadline passed and the seat moved to the next rank.",
    CANCELLED: "The organizer cancelled this drop before allocation completed.",
  }[entry.status];
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <StatusBadge value={entry.status} />
        {entry.rank && (
          <span className="font-mono text-sm muted">
            Draw rank {entry.rank}
          </span>
        )}
      </div>
      <div>
        <h2 className="text-3xl font-semibold tracking-tight">
          {entry.status === "CONFIRMED"
            ? "Your ticket is confirmed."
            : "Your entry is on record."}
        </h2>
        <p className="mt-3 leading-relaxed muted">{message}</p>
      </div>
      {entry.status === "OFFERED" && entry.reservation && (
        <div className="rounded-[var(--radius-control)] border border-[rgb(var(--accent)/0.28)] bg-[rgb(var(--accent)/0.08)] p-5">
          <p className="text-sm font-semibold accent">Confirmation deadline</p>
          <p className="mt-2 font-mono text-4xl">{remaining}s</p>
          <p className="mt-2 text-sm muted">
            {time(entry.reservation.expires_at)}
          </p>
          <button
            className="button mt-5"
            disabled={action.isPending || remaining === 0}
            onClick={() =>
              action.mutate({
                path: "/reservations/" + entry.reservation!.id + "/confirm",
              })
            }
          >
            <Check className="h-4 w-4" />
            Confirm my seat
          </button>
        </div>
      )}
      <div className="grid gap-4 border-t border-white/10 pt-5 sm:grid-cols-2">
        <div>
          <p className="text-xs muted">Receipt ID</p>
          <p className="mt-1 break-all font-mono text-sm">{entry.receipt_id}</p>
        </div>
        <div>
          <p className="text-xs muted">Public entry ID</p>
          <p className="mt-1 break-all font-mono text-sm">
            {entry.public_entry_id}
          </p>
        </div>
      </div>
      <Link className="link" to={"/entries/" + entry.entry_id}>
        Open full receipt
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
    queryFn: () => api<Drop>("/drops/" + id),
    refetchInterval: 5000,
  });
  const state = useQuery({
    queryKey: ["state", id, session.data?.principal.id],
    queryFn: () => api<Schema["MyDropState"]>("/drops/" + id + "/me"),
    enabled:
      session.data?.principal.role === "participant" &&
      !!drop.data &&
      drop.data.phase !== "DRAFT",
    refetchInterval: 3000,
  });
  if (drop.isPending)
    return (
      <div className="py-16">
        <LoadingBlock label="Loading drop" />
      </div>
    );
  if (!drop.data)
    return (
      <div className="py-16">
        <ErrorMessage error={drop.error} />
      </div>
    );
  const d = drop.data;
  const ownsDrop =
    ["organizer", "admin"].includes(session.data?.principal.role ?? "") &&
    (session.data?.principal.role === "admin" ||
      session.data?.principal.public_id === d.organizer.public_id);
  return (
    <div className="mx-auto max-w-5xl py-10 sm:py-16">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <Link className="button-ghost" to="/drops">
          Back to discovery
        </Link>
        <div className="flex items-center gap-3">
          {ownsDrop && (
            <Link className="button-secondary" to={`/organizer/drops/${id}`}>
              Manage this drop
            </Link>
          )}
          <StatusBadge value={d.phase} />
        </div>
      </div>
      <TicketCard>
        <div className="grid gap-10 p-7 sm:p-10 lg:grid-cols-[1.15fr_0.85fr]">
          <div>
            <p className="text-sm font-semibold accent">{d.category}</p>
            <h1 className="mt-4 text-4xl font-semibold tracking-[-0.05em] sm:text-6xl">
              {d.title}
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed muted">
              {d.description}
            </p>
            <p className="mt-8 text-sm muted">
              Hosted by {d.organizer.display_name}
            </p>
          </div>
          <div className="grid content-start gap-5 text-sm">
            <div className="flex gap-3">
              <CalendarDays className="mt-0.5 h-5 w-5 accent" />
              <div>
                <p className="font-semibold">Entry window</p>
                <p className="mt-1 muted">
                  {time(d.starts_at)} to {time(d.ends_at)}
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <MapPin className="mt-0.5 h-5 w-5 accent" />
              <div>
                <p className="font-semibold">
                  {d.location_type === "online" ? "Online event" : "Venue"}
                </p>
                <p className="mt-1 muted">{d.location_label}</p>
              </div>
            </div>
            <div className="flex gap-3">
              <Ticket className="mt-0.5 h-5 w-5 accent" />
              <div>
                <p className="font-semibold">{d.capacity} seats</p>
                <p className="mt-1 muted">
                  {d.mode === "LOTTERY"
                    ? "Verifiable lottery"
                    : "FCFS demo comparator"}
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <Clock3 className="mt-0.5 h-5 w-5 accent" />
              <div>
                <p className="font-semibold">Confirmation window</p>
                <p className="mt-1 muted">
                  {d.confirmation_seconds} seconds after an offer
                </p>
              </div>
            </div>
          </div>
        </div>
        <TicketDivider />
        <div className="p-7 sm:p-10">
          {ownsDrop ? (
            <div className="rounded-[var(--radius-control)] border border-[rgb(var(--accent)/0.24)] bg-[rgb(var(--accent)/0.07)] p-6 sm:p-7">
              <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold accent">
                    Organizer preview
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold">
                    This is the participant-facing event page.
                  </h2>
                  <p className="mt-2 max-w-2xl muted">
                    Your organizer account manages rules and allocation; it does
                    not receive a participant entry in its own drop.
                  </p>
                </div>
                <Link
                  className="button shrink-0"
                  to={`/organizer/drops/${id}`}
                >
                  Open control room
                </Link>
              </div>
            </div>
          ) : session.isPending ? (
            <LoadingBlock label="Checking session" />
          ) : !session.data ? (
            <div className="flex flex-col items-start gap-4">
              <h2 className="text-2xl font-semibold">Sign in to enter</h2>
              <p className="muted">
                Every authenticated participant can save one durable entry.
              </p>
              <Link className="button" to="/sign-in">
                Sign in to continue
              </Link>
            </div>
          ) : state.isPending ? (
            <LoadingBlock label="Checking entry status" />
          ) : state.data?.entry ? (
            <SavedEntry
              key={
                state.data.entry.entry_id + "-" + state.data.entry.server_time
              }
              entry={state.data.entry}
            />
          ) : (
            <div className="flex flex-col items-start gap-5">
              <div>
                <h2 className="text-2xl font-semibold">Ready to enter.</h2>
                <p className="mt-2 muted">
                  Your account may submit one durable entry during the open
                  window. Refreshes and retries return the same entry.
                </p>
              </div>
              <button
                className="button"
                disabled={
                  action.isPending || d.phase !== "OPEN"
                }
                onClick={() =>
                  action.mutate({ path: "/drops/" + id + "/entries" })
                }
              >
                {action.isPending
                  ? "Saving entry..."
                  : d.phase === "OPEN"
                    ? "Enter this drop"
                    : "Entry window is not open"}
              </button>
            </div>
          )}
          <ErrorMessage error={state.error ?? action.error ?? session.error} />
          <div className="mt-8 border-t border-white/10 pt-6">
            <Link className="link" to={"/drops/" + id + "/proof"}>
              Inspect the draw proof
            </Link>
            {d.seed_commitment && (
              <p className="mt-4 break-all font-mono text-xs muted">
                Seed commitment: {d.seed_commitment}
              </p>
            )}
          </div>
        </div>
      </TicketCard>
      {d.cancellation_reason && (
        <div className="mt-5 rounded-[var(--radius-control)] border border-red-400/30 bg-red-400/[0.06] p-5 text-red-200">
          {d.cancellation_reason}
        </div>
      )}
    </div>
  );
}

function AuthAside() {
  return (
    <aside className="surface-soft hidden min-h-[600px] flex-col p-9 lg:flex">
      <ShieldCheck className="h-9 w-9 accent" />
      <div className="mt-20">
        <h2 className="text-3xl font-semibold tracking-[-0.04em]">
          Your state belongs to you.
        </h2>
        <div className="mt-8 space-y-5 text-sm">
          {[
            "One account keeps one identity across devices.",
            "Refreshes recover your receipt from the server.",
            "Protected writes require your session and CSRF token.",
          ].map((item) => (
            <div className="flex gap-3" key={item}>
              <CheckCircle2 className="h-5 w-5 shrink-0 accent" />
              <p className="muted">{item}</p>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

export function SignInPage() {
  const [invitationMode, setInvitationMode] = useState(false);
  const [code, setCode] = useState("");
  const login = useLogin();
  const passwordLogin = usePasswordLogin();
  const navigate = useNavigate();
  return (
    <div className="mx-auto grid max-w-5xl gap-5 py-12 lg:grid-cols-[0.8fr_1.2fr] lg:py-20">
      <AuthAside />
      <TicketCard className="p-7 sm:p-10">
        <KeyRound className="h-8 w-8 accent" />
        <h1 className="mt-8 text-4xl font-semibold tracking-[-0.045em]">
          Welcome back.
        </h1>
        <p className="mt-3 muted">
          Use your account or a private invitation credential.
        </p>
        <div className="mt-8 inline-flex rounded-full border border-white/10 bg-white/[0.04] p-1">
          <button
            className={
              !invitationMode
                ? "button min-h-9 px-4 py-1.5"
                : "button-ghost min-h-9 px-4 py-1.5"
            }
            type="button"
            onClick={() => setInvitationMode(false)}
          >
            Email
          </button>
          <button
            className={
              invitationMode
                ? "button min-h-9 px-4 py-1.5"
                : "button-ghost min-h-9 px-4 py-1.5"
            }
            type="button"
            onClick={() => setInvitationMode(true)}
          >
            Invitation
          </button>
        </div>
        <form
          className="mt-8 space-y-5"
          onSubmit={(event) => {
            event.preventDefault();
            const fields = new FormData(event.currentTarget);
            const options = {
              onSuccess: (authenticated: Session) => {
                setCode("");
                navigate(
                  ["organizer", "admin"].includes(
                    authenticated.principal.role,
                  )
                    ? "/organizer"
                    : "/drops",
                );
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
              <span className="field-label">Invitation credential</span>
              <input
                className="field"
                type="password"
                autoComplete="off"
                required
                maxLength={256}
                value={code}
                onChange={(event) => setCode(event.target.value)}
              />
            </label>
          ) : (
            <>
              <label className="block">
                <span className="field-label">Email</span>
                <input
                  className="field"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  maxLength={254}
                />
              </label>
              <label className="block">
                <span className="field-label">Password</span>
                <input
                  className="field"
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
            className="button w-full"
            disabled={login.isPending || passwordLogin.isPending}
          >
            {login.isPending || passwordLogin.isPending
              ? "Signing in..."
              : "Sign in"}
          </button>
          <ErrorMessage error={login.error ?? passwordLogin.error} />
        </form>
        <p className="mt-7 text-sm muted">
          New participant?{" "}
          <Link className="link text-[rgb(var(--ink))]" to="/register">
            Create an account
          </Link>
        </p>
      </TicketCard>
    </div>
  );
}

function FaceScanner({
  value,
  onChange,
  disabled,
}: {
  value: string | null;
  onChange: (image: string | null) => void;
  disabled?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const stop = () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      if (videoRef.current) videoRef.current.srcObject = null;
    };
    if (value) {
      stop();
      setCameraActive(false);
      return stop;
    }
    const start = async () => {
      setCameraError(null);
      try {
        stop();
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "user",
            width: { ideal: 640 },
            height: { ideal: 640 },
          },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          try {
            await videoRef.current.play();
          } catch (error) {
            if (!(error instanceof Error && error.name === "AbortError")) throw error;
          }
        }
        if (!cancelled) setCameraActive(true);
      } catch (error) {
        if (cancelled || (error instanceof Error && error.name === "AbortError")) return;
        setCameraError(
          error instanceof Error && error.name === "NotAllowedError"
            ? "Camera access was denied. Allow camera access and retry."
            : "The camera is unavailable. Check the device and retry.",
        );
        setCameraActive(false);
      }
    };
    void start();
    return () => {
      cancelled = true;
      stop();
    };
  }, [retryKey, value]);

  const capture = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth || !video.videoHeight) return;
    const size = Math.min(video.videoWidth, video.videoHeight, 640);
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const context = canvas.getContext("2d");
    if (!context) return;
    const sourceSize = Math.min(video.videoWidth, video.videoHeight);
    const sourceX = (video.videoWidth - sourceSize) / 2;
    const sourceY = (video.videoHeight - sourceSize) / 2;
    context.translate(size, 0);
    context.scale(-1, 1);
    context.drawImage(
      video,
      sourceX,
      sourceY,
      sourceSize,
      sourceSize,
      0,
      0,
      size,
      size,
    );
    onChange(canvas.toDataURL("image/jpeg", 0.82));
  };

  return (
    <div className="overflow-hidden rounded-[var(--radius-control)] border border-white/10 bg-white/[0.025]">
      <div className="grid gap-0 sm:grid-cols-[minmax(0,1fr)_13rem]">
        <div className="relative aspect-[4/3] overflow-hidden bg-black/30">
          {value ? (
            <img
              alt="Captured face verification preview"
              className="h-full w-full object-cover"
              src={value}
            />
          ) : (
            <video
              autoPlay
              className="h-full w-full scale-x-[-1] object-cover"
              muted
              playsInline
              ref={videoRef}
            />
          )}
          {!value && !cameraActive && !cameraError && (
            <div className="absolute inset-0 grid place-items-center bg-[rgb(var(--canvas)/0.88)]">
              <div className="text-center">
                <Camera className="mx-auto h-7 w-7 accent" />
                <p className="mt-3 text-sm muted">Starting camera...</p>
              </div>
            </div>
          )}
          {!value && cameraError && (
            <div className="absolute inset-0 grid place-items-center bg-[rgb(var(--canvas)/0.94)] p-6 text-center">
              <div>
                <Camera className="mx-auto h-7 w-7 text-red-300" />
                <p className="mt-3 text-sm text-red-200" role="alert">
                  {cameraError}
                </p>
              </div>
            </div>
          )}
          <div className="pointer-events-none absolute inset-[12%] rounded-[42%] border border-[rgb(var(--accent)/0.55)]" />
        </div>
        <div className="flex flex-col justify-between border-t border-white/10 p-5 sm:border-l sm:border-t-0">
          <div>
            <ScanFace className="h-6 w-6 accent" />
            <p className="mt-4 font-semibold">
              {value ? "Face captured" : "Center your face"}
            </p>
            <p className="mt-2 text-xs leading-relaxed muted">
              Use even lighting and keep only one person in frame.
            </p>
          </div>
          {value ? (
            <button
              className="button-secondary mt-5 w-full"
              disabled={disabled}
              onClick={() => onChange(null)}
              type="button"
            >
              <RefreshCw className="h-4 w-4" /> Retake
            </button>
          ) : cameraError ? (
            <button
              className="button-secondary mt-5 w-full"
              disabled={disabled}
              onClick={() => setRetryKey((key) => key + 1)}
              type="button"
            >
              <RefreshCw className="h-4 w-4" /> Retry camera
            </button>
          ) : (
            <button
              className="button mt-5 w-full"
              disabled={disabled || !cameraActive}
              onClick={capture}
              type="button"
            >
              <Camera className="h-4 w-4" /> Capture
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function RegisterPage() {
  const [role, setRole] = useState<"participant" | "organizer" | "admin">(
    "participant",
  );
  const [faceImage, setFaceImage] = useState<string | null>(null);
  const [faceError, setFaceError] = useState<string | null>(null);
  const register = useRegister();
  const navigate = useNavigate();
  return (
    <div className="mx-auto grid max-w-5xl gap-5 py-12 lg:grid-cols-[0.8fr_1.2fr] lg:py-20">
      <AuthAside />
      <TicketCard className="p-7 sm:p-10">
        <UserPlus className="h-8 w-8 accent" />
        <h1 className="mt-8 text-4xl font-semibold tracking-[-0.045em]">
          Create your account.
        </h1>
        <p className="mt-3 muted">
          Registration creates the identity used to enforce one account, one
          durable entry per drop.
        </p>

        <div className="mt-6 rounded-[var(--radius-control)] border border-white/10 bg-white/[0.03] p-4 text-xs leading-relaxed muted space-y-1">
          <div className="flex items-center gap-2 font-semibold text-[rgb(var(--accent))]">
            <ShieldCheck className="h-4 w-4" />
            <span>Anti-Sybil Uniqueness Guarantee</span>
          </div>
          <p>
            To prevent fraud and duplicate accounts, each account requires a unique <strong>Email</strong>, <strong>Phone Number</strong>, and <strong>Facial Identity Scan</strong>.
          </p>
        </div>

        <form
          className="mt-8 space-y-5"
          onSubmit={(event) => {
            event.preventDefault();
            setFaceError(null);
            if (!faceImage) {
              setFaceError("Capture one clear face scan before creating your account.");
              return;
            }
            const fields = new FormData(event.currentTarget);
            const phoneNumber = String(fields.get("phone_number") || "").trim();
            if (!phoneNumber) {
              setFaceError("A phone number is required.");
              return;
            }
            const selectedRole =
              (fields.get("role") as "participant" | "organizer" | "admin") ||
              role;
            register.mutate(
              {
                display_name: String(fields.get("display_name")),
                email: String(fields.get("email")).trim().toLowerCase(),
                phone_number: phoneNumber,
                password: String(fields.get("password")),
                role: selectedRole,
                face_image: faceImage,
              },
              {
                onSuccess: () => {
                  if (selectedRole === "admin" || selectedRole === "organizer") {
                    navigate("/organizer");
                  } else {
                    navigate("/profile");
                  }
                },
              },
            );
          }}
        >
          <label className="block">
            <span className="field-label">Account type</span>
            <select
              className="field"
              name="role"
              value={role}
              onChange={(e) =>
                setRole(e.target.value as "participant" | "organizer" | "admin")
              }
            >
              <option value="participant">Participant (Enter drops, verify proofs)</option>
              <option value="organizer">Organizer (Create drops, manage draws)</option>
              <option value="admin">Admin (Administrative &amp; Attack Lab access)</option>
            </select>
          </label>
          <label className="block">
            <span className="field-label">Display name</span>
            <input
              className="field"
              name="display_name"
              autoComplete="name"
              required
              maxLength={100}
              placeholder="Alex Johnson"
            />
          </label>
          <label className="block">
            <span className="field-label">Email</span>
            <input
              className="field"
              name="email"
              type="email"
              autoComplete="email"
              required
              maxLength={254}
              placeholder="alex@example.com"
            />
          </label>
          <label className="block">
            <span className="field-label">Phone number</span>
            <input
              className="field"
              name="phone_number"
              type="tel"
              autoComplete="tel"
              placeholder="+14155552671"
              required
            />
            <span className="mt-2 block text-xs muted">
              Include country code (e.g. +14155552671 or +919876543210). Every account requires a unique phone number.
            </span>
          </label>
          <label className="block">
            <span className="field-label">Password</span>
            <input
              className="field"
              name="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              maxLength={128}
              placeholder="At least 8 characters"
            />
            <span className="mt-2 block text-xs muted">
              Use at least 8 characters.
            </span>
          </label>
          <div>
            <span className="field-label">Facial Identity Scan</span>
            <p className="mb-4 mt-2 text-sm leading-relaxed muted">
              This guarantees 1 Person = 1 Account. The server checks 1:N uniqueness and stores an irreversible numeric embedding, never raw imagery.
            </p>
            <FaceScanner
              value={faceImage}
              disabled={register.isPending}
              onChange={(image) => {
                setFaceImage(image);
                if (image) setFaceError(null);
              }}
            />
            {faceError && (
              <p className="mt-3 text-sm text-red-300" role="alert">
                {faceError}
              </p>
            )}
          </div>
          <button className="button w-full" disabled={register.isPending}>
            {register.isPending ? "Verifying identity & creating account..." : "Create account"}
          </button>
          <ErrorMessage error={register.error} />
        </form>
        <p className="mt-7 text-sm muted">
          Already registered?{" "}
          <Link className="link text-[rgb(var(--ink))]" to="/sign-in">
            Sign in
          </Link>
        </p>
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
  if (!session.data)
    return (
      <div className="py-16">
        <EmptyState
          title="Sign in to recover your receipts"
          body="Accepted entries and confirmed tickets are stored on the server, not only in this browser."
          action={
            <Link className="button" to="/sign-in">
              Sign in
            </Link>
          }
        />
      </div>
    );
  return (
    <>
      <PageHeader
        eyebrow="My tickets"
        title={"Welcome back, " + session.data.principal.display_name + "."}
        body="Every accepted entry, offer, and confirmed seat appears here across refreshes and devices."
      />
      <ErrorMessage error={receipts.error} />
      {receipts.isPending && <LoadingBlock label="Loading receipts" />}
      {receipts.data?.items.length === 0 && (
        <EmptyState
          title="No entries yet"
          body="Browse published drops and save one entry during an open window."
          action={
            <Link className="button" to="/drops">
              Browse drops
            </Link>
          }
        />
      )}
      <div className="grid gap-5 md:grid-cols-2">
        {receipts.data?.items.map((receipt) => (
          <Link
            key={receipt.entry.entry_id}
            to={"/entries/" + receipt.entry.entry_id}
          >
            <TicketCard className="h-full p-7">
              <div className="flex items-start justify-between gap-5">
                <StatusBadge value={receipt.entry.status} />
                <Ticket className="h-5 w-5 accent" />
              </div>
              <h2 className="mt-10 text-2xl font-semibold">
                {receipt.drop.title}
              </h2>
              <p className="mt-3 text-sm muted">
                {receipt.drop.location_label}
              </p>
              <div className="mt-7 flex items-center justify-between border-t border-white/10 pt-5 text-sm">
                <span className="muted">{time(receipt.entry.joined_at)}</span>
                <span className="font-semibold">Open receipt</span>
              </div>
            </TicketCard>
          </Link>
        ))}
      </div>
    </>
  );
}

export function ReceiptPage() {
  const { id } = useParams();
  const session = useSession();
  const receipt = useQuery({
    queryKey: ["receipt", id, session.data?.principal.id],
    queryFn: () => api<Schema["Receipt"]>("/entries/" + id),
    enabled: !!session.data,
    refetchInterval: 3000,
  });
  return (
    <div className="mx-auto max-w-3xl py-12 sm:py-16">
      <div className="mb-6 flex items-center justify-between gap-4">
        <Link className="button-ghost" to="/entries">
          All receipts
        </Link>
        {receipt.data && <StatusBadge value={receipt.data.entry.status} />}
      </div>
      <ErrorMessage error={receipt.error} />
      {!session.data && (
        <EmptyState
          title="This receipt is private"
          body="Sign in with the account that created the entry."
          action={
            <Link className="button" to="/sign-in">
              Sign in
            </Link>
          }
        />
      )}
      {receipt.isPending && session.data && (
        <LoadingBlock label="Loading receipt" />
      )}
      {receipt.data && (
        <TicketCard>
          <div className="p-7 sm:p-10">
            <p className="text-sm font-semibold accent">
              {receipt.data.drop.category}
            </p>
            <h1 className="mt-4 text-4xl font-semibold tracking-[-0.045em]">
              {receipt.data.drop.title}
            </h1>
            <p className="mt-3 muted">{receipt.data.drop.location_label}</p>
          </div>
          <TicketDivider />
          <div className="p-7 sm:p-10">
            <SavedEntry
              key={receipt.data.entry.server_time}
              entry={receipt.data.entry}
            />
            <Link
              className="button-secondary mt-7"
              to={"/drops/" + receipt.data.drop.id + "/proof"}
            >
              <ShieldCheck className="h-4 w-4" />
              Verify draw proof
            </Link>
          </div>
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
        "/drops/" + id + "/proof",
      ),
    refetchInterval: 5000,
  });
  return (
    <div className="pb-16">
      <PageHeader
        eyebrow="Public verification"
        title="Check the draw independently."
        body="The proof contains pseudonymous entries, commitments, ranks, and the disclosed algorithm. It never exposes private identities."
      />
      <ErrorMessage error={proof.error} />
      {proof.isPending && <LoadingBlock label="Loading proof" />}
      {proof.data && (
        <div className="grid gap-5 lg:grid-cols-[0.75fr_1.25fr]">
          <div className="surface-soft p-7">
            <ShieldCheck className="h-8 w-8 accent" />
            <h2 className="mt-8 text-2xl font-semibold">
              {proof.data.status === "pending"
                ? "Proof is not published yet."
                : "Proof package is published."}
            </h2>
            <p className="mt-3 leading-relaxed muted">
              {proof.data.status === "pending"
                ? "The manifest and seed remain sealed until ranking is complete."
                : String(proof.data.entries.length) +
                  " frozen entries use " +
                  proof.data.algorithm_version +
                  "."}
            </p>
            {proof.data.status === "published" && (
              <a
                className="button mt-7"
                href={"/api/v1/drops/" + id + "/proof"}
                download="proof.json"
              >
                <Download className="h-4 w-4" />
                Download proof JSON
              </a>
            )}
          </div>
          <details className="surface-soft overflow-hidden p-6" open>
            <summary className="cursor-pointer font-semibold">
              Inspect proof payload
            </summary>
            <pre className="mt-5 max-h-[600px] overflow-auto rounded-[var(--radius-control)] bg-black/25 p-5 font-mono text-xs leading-relaxed muted">
              {JSON.stringify(proof.data, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
