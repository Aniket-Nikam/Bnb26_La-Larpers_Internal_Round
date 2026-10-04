import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Camera,
  CheckCircle2,
  Lock,
  Phone,
  RefreshCw,
  ScanFace,
  ShieldCheck,
  Ticket,
  UserPlus,
} from "lucide-react";
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
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

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
            Email &amp; Password
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
            const options = {
              onSuccess: () => {
                setCode("");
                setPassword("");
                navigate("/drops");
              },
            };
            if (invitationMode) {
              login.mutate(code, options);
            } else {
              passwordLogin.mutate(
                {
                  email: email.trim().toLowerCase(),
                  password,
                },
                options,
              );
            }
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
                Email address
                <input
                  className="field mt-3"
                  type="email"
                  autoComplete="email"
                  required
                  maxLength={254}
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </label>
              <label className="block">
                Password
                <input
                  className="field mt-3"
                  type="password"
                  autoComplete="current-password"
                  required
                  maxLength={128}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
            </>
          )}
          <button
            className="button"
            disabled={
              login.isPending ||
              passwordLogin.isPending ||
              (!invitationMode && (!email.trim() || !password))
            }
          >
            {passwordLogin.isPending || login.isPending ? "Signing in..." : "Sign in"}
          </button>
          <ErrorMessage error={invitationMode ? login.error : passwordLogin.error} />
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
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const cleanupStream = () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
      setCameraActive(false);
    };

    if (value) {
      cleanupStream();
      return;
    }

    const startCamera = async () => {
      setCameraError(null);
      try {
        cleanupStream();

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
          } catch (playErr: unknown) {
            if (playErr instanceof Error && playErr.name === "AbortError") {
              return;
            }
            throw playErr;
          }
        }
        if (!cancelled) {
          setCameraActive(true);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        const isAbort =
          (err as { name?: string })?.name === "AbortError" ||
          String(err).includes("AbortError");
        if (isAbort) return;
        console.error("Camera access error:", err);
        const msg =
          err instanceof Error && err.name === "NotAllowedError"
            ? "Camera permission denied. Please allow camera access in your browser settings to verify your face."
            : "Could not access camera. Please check camera connection and permissions.";
        setCameraError(msg);
        setCameraActive(false);
      }
    };

    startCamera();

    return () => {
      cancelled = true;
      cleanupStream();
    };
  }, [value, retryKey]);

  const captureFace = () => {
    if (!videoRef.current) return;
    setIsScanning(true);
    setTimeout(() => {
      try {
        const video = videoRef.current;
        if (!video) return;
        const canvas = canvasRef.current || document.createElement("canvas");
        const videoW = video.videoWidth || 480;
        const videoH = video.videoHeight || 480;
        const minDim = Math.min(videoW, videoH);
        const targetDim = Math.min(minDim, 400);
        canvas.width = targetDim;
        canvas.height = targetDim;
        const ctx = canvas.getContext("2d");
        if (ctx) {
          const sx = (videoW - minDim) / 2;
          const sy = (videoH - minDim) / 2;
          ctx.drawImage(video, sx, sy, minDim, minDim, 0, 0, targetDim, targetDim);
          const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
          onChange(dataUrl);
        }
      } catch (e) {
        console.error("Capture failed:", e);
      } finally {
        setIsScanning(false);
      }
    }, 400);
  };

  const handleRetake = () => {
    onChange(null);
  };

  return (
    <div className="flex flex-col items-center space-y-4">
      <div className="relative flex items-center justify-center">
        <div
          className={`relative w-48 h-48 sm:w-56 sm:h-56 rounded-full overflow-hidden transition-all duration-300 flex items-center justify-center bg-black/40 shadow-inner ${
            value
              ? "ring-4 ring-emerald-500 shadow-[0_0_24px_rgba(16,185,129,0.35)]"
              : cameraError
              ? "ring-4 ring-rose-500/80"
              : "ring-2 ring-emerald-400/50"
          }`}
        >
          {value ? (
            <img
              src={value}
              alt="Face scan preview"
              className="w-full h-full object-cover rounded-full"
            />
          ) : (
            <>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className={`w-full h-full object-cover scale-x-[-1] transition-opacity duration-300 ${
                  cameraActive ? "opacity-100" : "opacity-0"
                }`}
              />
              {!cameraActive && !cameraError && (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-white/50 space-y-2 p-4 text-center text-xs">
                  <Camera className="w-8 h-8 animate-pulse text-emerald-400" />
                  <span>Starting camera…</span>
                </div>
              )}
              {cameraError && (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-rose-300 space-y-1 p-4 text-center text-xs bg-black/80">
                  <ScanFace className="w-8 h-8 text-rose-400 mb-1" />
                  <span className="font-semibold">Camera Error</span>
                  <span className="text-[11px] leading-tight text-white/70">
                    {cameraError}
                  </span>
                </div>
              )}
              {cameraActive && (
                <motion.div
                  className="absolute inset-x-0 h-1 bg-gradient-to-r from-transparent via-emerald-400 to-transparent shadow-[0_0_12px_#34d399]"
                  animate={{
                    top: ["10%", "85%", "10%"],
                  }}
                  transition={{
                    duration: 2.4,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                />
              )}
            </>
          )}

          <div className="absolute inset-0 pointer-events-none rounded-full border border-dashed border-white/20" />
          <div className="absolute top-2 w-6 h-[2px] bg-emerald-400/70 rounded-full" />
          <div className="absolute bottom-2 w-6 h-[2px] bg-emerald-400/70 rounded-full" />
          <div className="absolute left-2 h-6 w-[2px] bg-emerald-400/70 rounded-full" />
          <div className="absolute right-2 h-6 w-[2px] bg-emerald-400/70 rounded-full" />
        </div>

        {value && (
          <div className="absolute bottom-1 right-2 bg-emerald-600 text-white rounded-full p-1.5 shadow-lg border border-black/40">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        )}
      </div>

      <canvas ref={canvasRef} className="hidden" />

      <div className="w-full text-center space-y-2">
        {value ? (
          <div className="flex flex-col items-center space-y-2">
            <p className="text-sm font-medium text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 inline" /> Face ID Captured
            </p>
            <button
              type="button"
              className="text-xs text-white/70 hover:text-white flex items-center gap-1 border border-white/20 rounded-full px-3 py-1.5 transition-colors"
              onClick={handleRetake}
              disabled={disabled}
            >
              <RefreshCw className="w-3.5 h-3.5 inline" /> Retake Face Scan
            </button>
          </div>
        ) : cameraActive ? (
          <div className="flex flex-col items-center space-y-2">
            <p className="text-xs text-white/60">
              Center your face inside the circular viewfinder
            </p>
            <button
              type="button"
              className="button bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center gap-2 py-2 px-5 text-sm"
              onClick={captureFace}
              disabled={isScanning || disabled}
            >
              <ScanFace className="w-4 h-4" />
              {isScanning ? "Scanning…" : "Capture Face ID"}
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center space-y-2">
            <button
              type="button"
              className="text-xs text-emerald-400 hover:underline flex items-center gap-1 py-1"
              onClick={() => setRetryKey((k) => k + 1)}
            >
              <Camera className="w-3.5 h-3.5 inline" /> Retry Camera Access
            </button>
          </div>
        )}
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
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [password, setPassword] = useState("");

  const register = useRegister();
  const navigate = useNavigate();

  return (
    <div className="max-w-md mx-auto pt-16">
      <TicketCard className="p-10 space-y-8">
        <UserPlus />
        <h1 className="text-3xl font-bold">
          Create {role === "admin" ? "admin" : role === "organizer" ? "organizer" : "visitor"} account
        </h1>

        <div className="rounded-xl bg-white/5 border border-white/10 p-3.5 text-xs text-white/70 space-y-1">
          <div className="flex items-center gap-1.5 font-semibold text-emerald-400">
            <ShieldCheck className="w-4 h-4" />
            <span>Anti-Sybil Uniqueness Protection</span>
          </div>
          <p>
            To prevent fraud and duplicate accounts, each user must register with a unique <strong>Email</strong>, <strong>Phone Number</strong>, and <strong>Facial Identity Scan</strong>.
          </p>
        </div>

        <form
          className="space-y-6"
          onSubmit={(event) => {
            event.preventDefault();
            setFaceError(null);
            if (!faceImage) {
              setFaceError(
                "Please scan and capture your face before creating an account.",
              );
              return;
            }
            if (!phoneNumber.trim()) {
              setFaceError("A phone number is required.");
              return;
            }
            register.mutate(
              {
                display_name: displayName.trim(),
                email: email.trim().toLowerCase(),
                phone_number: phoneNumber.trim(),
                password,
                role,
                face_image: faceImage,
              },
              {
                onSuccess: () => {
                  if (role === "admin" || role === "organizer") {
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
            Account type
            <select
              className="field mt-3"
              name="role"
              value={role}
              onChange={(e) =>
                setRole(e.target.value as "participant" | "organizer" | "admin")
              }
            >
              <option value="participant">Participant (Enter drops, verify proofs)</option>
              <option value="organizer">Organizer (Create drops, grant invitations)</option>
              <option value="admin">Admin (Full administrative &amp; Attack Lab access)</option>
            </select>
          </label>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-white/70">
              <span className="flex items-center gap-1.5">
                <ScanFace className="w-4 h-4 text-emerald-400" />
                Facial Identity Scan
              </span>
              <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-500/30">
                Mandatory · 1 Face = 1 Account
              </span>
            </div>
            <FaceScanner
              value={faceImage}
              onChange={(img) => {
                setFaceImage(img);
                if (img) setFaceError(null);
              }}
              disabled={register.isPending}
            />
            {faceError && (
              <p
                role="alert"
                className="text-xs text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-lg p-2.5"
              >
                {faceError}
              </p>
            )}
          </div>

          <label className="block">
            Display name
            <input
              className="field mt-3"
              name="display_name"
              type="text"
              required
              maxLength={100}
              placeholder="Alex Johnson"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </label>

          <label className="block">
            Email address
            <input
              className="field mt-3"
              name="email"
              type="email"
              autoComplete="email"
              required
              maxLength={254}
              placeholder="alex@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>

          <label className="block">
            <span className="flex items-center gap-1.5">
              <Phone className="w-4 h-4 text-emerald-400" />
              Phone number
            </span>
            <input
              className="field mt-3"
              name="phone_number"
              type="tel"
              placeholder="+14155552671"
              autoComplete="tel"
              required
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
            />
            <span className="text-[11px] text-white/50 block mt-1">
              Include country code (e.g. +14155552671 or +919876543210). Must be unique across all accounts.
            </span>
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
              placeholder="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>

          <button
            className="button"
            disabled={
              register.isPending ||
              !faceImage ||
              !phoneNumber.trim() ||
              !email.trim() ||
              password.length < 8
            }
          >
            {register.isPending ? "Creating account…" : "Create account"}
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
