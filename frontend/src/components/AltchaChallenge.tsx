import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { createSHA256 } from "hash-wasm";

export function AltchaLogo({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 2.5L4 6V11.5C4 16.8 7.4 21.8 12 23C16.6 21.8 20 16.8 20 11.5V6L12 2.5Z"
        fill="currentColor"
        fillOpacity="0.12"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M9 12.2L11.2 14.5L15.5 9.8"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

interface AltchaChallengeProps {
  verified: boolean;
  onVerify: (payloadBase64: string) => void;
  className?: string;
  label?: string;
  autoSolve?: boolean;
}

export function AltchaChallenge({
  verified,
  onVerify,
  className = "",
  label = "Verify you are human",
  autoSolve = false,
}: AltchaChallengeProps) {
  const [solving, setSolving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [tookMs, setTookMs] = useState<number | null>(null);
  const cancelledRef = useRef(false);

  const solveChallenge = async (
    salt: string,
    challenge: string,
    maxnumber: number,
    onProgress?: (current: number) => void
  ): Promise<number> => {
    const target = challenge.toLowerCase();
    const batchSize = 2500;

    // Prefer high-performance WebAssembly SHA-256 (hash-wasm)
    try {
      const hasher = await createSHA256();
      for (let i = 0; i <= maxnumber; i += batchSize) {
        if (cancelledRef.current) throw new Error("Cancelled");
        const end = Math.min(i + batchSize, maxnumber + 1);

        for (let j = i; j < end; j++) {
          hasher.init();
          hasher.update(salt + j);
          if (hasher.digest("hex") === target) {
            return j;
          }
        }

        if (onProgress) onProgress(end);
        // Yield to browser UI thread
        await new Promise((r) => setTimeout(r, 0));
      }
    } catch (err: any) {
      if (err.message === "Cancelled") throw err;
      // Fallback to native Web Crypto API if WebAssembly unavailable
      const encoder = new TextEncoder();
      for (let i = 0; i <= maxnumber; i += 200) {
        if (cancelledRef.current) throw new Error("Cancelled");
        const end = Math.min(i + 200, maxnumber + 1);

        for (let j = i; j < end; j++) {
          const buf = await crypto.subtle.digest("SHA-256", encoder.encode(salt + j));
          const hex = Array.from(new Uint8Array(buf))
            .map((b) => b.toString(16).padStart(2, "0"))
            .join("");
          if (hex === target) {
            return j;
          }
        }
        await new Promise((r) => setTimeout(r, 0));
      }
    }

    throw new Error("Solution not found within challenge range");
  };

  const handleSolve = useCallback(async () => {
    if (verified || solving) return;
    setSolving(true);
    setErrorMsg(null);
    cancelledRef.current = false;
    const startTime = Date.now();

    try {
      // 1. Fetch fresh signed challenge from FastAPI backend
      const res = await fetch("/api/v1/security/altcha/challenge");
      if (!res.ok) {
        throw new Error(`Challenge fetch failed: HTTP ${res.status}`);
      }
      const data = await res.json();
      const { algorithm, challenge, salt, signature, maxnumber = 50000 } = data;

      // 2. Solve Proof-of-Work
      const number = await solveChallenge(salt, challenge, maxnumber);
      const took = Date.now() - startTime;
      setTookMs(took);

      // 3. Format official ALTCHA payload
      const payload = {
        algorithm: algorithm || "SHA-256",
        challenge,
        number,
        salt,
        signature,
        took,
      };

      const payloadBase64 = btoa(JSON.stringify(payload));
      setSolving(false);
      onVerify(payloadBase64);
    } catch (err: any) {
      if (!cancelledRef.current) {
        setSolving(false);
        setErrorMsg(err.message || "Failed to solve ALTCHA challenge");
      }
    }
  }, [verified, solving, onVerify]);

  useEffect(() => {
    if (autoSolve && !verified && !solving) {
      handleSolve();
    }
    return () => {
      cancelledRef.current = true;
    };
  }, [autoSolve, verified, solving, handleSolve]);

  return (
    <div
      className={`rounded-[var(--radius-control)] border border-white/15 bg-[#121316] p-3.5 select-none transition-colors ${className}`}
    >
      <div className="flex items-center justify-between gap-4">
        <button
          type="button"
          onClick={handleSolve}
          disabled={verified || solving}
          className="flex items-center gap-3.5 text-left focus:outline-none group cursor-pointer disabled:cursor-default"
          aria-label={label}
        >
          <div
            className={`relative flex h-7 w-7 shrink-0 items-center justify-center rounded-[6px] border transition-all duration-200 ${
              verified
                ? "border-emerald-500 bg-emerald-500/20 text-emerald-400"
                : solving
                ? "border-emerald-500/80 bg-emerald-500/10 text-emerald-400"
                : "border-white/30 bg-white/[0.04] group-hover:border-white/60"
            }`}
          >
            {verified ? (
              <Check className="h-4 w-4 stroke-[2.5]" />
            ) : solving ? (
              <Loader2 className="h-4 w-4 animate-spin text-emerald-400" />
            ) : (
              <div className="h-2 w-2 rounded-sm bg-transparent group-hover:bg-white/10" />
            )}
          </div>
          <div className="flex flex-col">
            <span
              className={`text-sm font-medium transition-colors ${
                verified
                  ? "text-emerald-300"
                  : solving
                  ? "text-emerald-400"
                  : "text-white/90 group-hover:text-white"
              }`}
            >
              {verified ? "Verified" : solving ? "Solving cryptographic proof-of-work..." : label}
            </span>
            <span className="text-[11px] text-white/40">
              {verified
                ? tookMs != null
                  ? `Proof-of-work verified in ${tookMs}ms`
                  : "Human identity confirmed"
                : "FOSS Proof-of-Work • No cookies or tracking"}
            </span>
          </div>
        </button>

        <div className="flex flex-col items-end shrink-0 pl-2">
          <a
            href="https://altcha.org"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 text-[11px] font-semibold tracking-tight text-white/80 hover:text-white transition-colors"
          >
            <AltchaLogo className="h-3.5 w-3.5 text-emerald-400" />
            <span>ALTCHA</span>
          </a>
          <div className="mt-0.5 flex gap-1.5 text-[9px] text-white/40">
            <span>FOSS</span>
            <span>•</span>
            <span>Self-Hosted</span>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="mt-2.5 flex items-center justify-between text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2.5 py-1.5 rounded">
          <span>{errorMsg}</span>
          <button
            type="button"
            onClick={handleSolve}
            className="text-xs text-white underline hover:no-underline ml-2"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
