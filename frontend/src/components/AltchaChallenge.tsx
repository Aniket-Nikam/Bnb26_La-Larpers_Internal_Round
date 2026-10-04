import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Loader2 } from "lucide-react";

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

const SOLVER_WORKER_SCRIPT = `
self.onmessage = function(e) {
  const { salt, challenge, maxnumber } = e.data;
  const startTime = Date.now();

  function rightRotate(value, amount) {
    return (value >>> amount) | (value << (32 - amount));
  }

  function sha256_sync(ascii) {
    const lengthProperty = "length";
    let i, j;
    let result = "";
    const words = [];
    const asciiBitLength = ascii[lengthProperty] * 8;
    const hash = [
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    ];
    const k = [
      0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
      0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
      0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
      0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
      0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
      0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
      0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x3910c4f1, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
      0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    ];
    for (i = 0; i < asciiBitLength; i += 8) {
      words[i >> 5] |= (ascii.charCodeAt(i / 8) & 255) << (24 - (i % 32));
    }
    words[asciiBitLength >> 5] |= 0x80 << (24 - (asciiBitLength % 32));
    words[(((asciiBitLength + 64) >> 9) << 4) + 15] = asciiBitLength;
    const w = new Array(64);
    for (i = 0; i < words[lengthProperty]; i += 16) {
      let a = hash[0], b = hash[1], c = hash[2], d = hash[3], e = hash[4], f = hash[5], g = hash[6], h = hash[7];
      for (j = 0; j < 64; j++) {
        if (j < 16) w[j] = words[i + j] | 0;
        else {
          const s0 = rightRotate(w[j - 15], 7) ^ rightRotate(w[j - 15], 18) ^ (w[j - 15] >>> 3);
          const s1 = rightRotate(w[j - 2], 17) ^ rightRotate(w[j - 2], 19) ^ (w[j - 2] >>> 10);
          w[j] = (w[j - 16] + s0 + w[j - 7] + s1) | 0;
        }
        const t1 = (h + (rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25)) + ((e & f) ^ (~e & g)) + k[j] + w[j]) | 0;
        const t2 = ((rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) | 0;
        h = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
      }
      hash[0] = (hash[0] + a) | 0; hash[1] = (hash[1] + b) | 0;
      hash[2] = (hash[2] + c) | 0; hash[3] = (hash[3] + d) | 0;
      hash[4] = (hash[4] + e) | 0; hash[5] = (hash[5] + f) | 0;
      hash[6] = (hash[6] + g) | 0; hash[7] = (hash[7] + h) | 0;
    }
    for (i = 0; i < 8; i++) {
      for (j = 3; j >= 0; j--) {
        const byte = (hash[i] >> (j * 8)) & 255;
        result += (byte < 16 ? "0" : "") + byte.toString(16);
      }
    }
    return result;
  }

  const target = challenge.toLowerCase();
  for (let i = 0; i <= maxnumber; i++) {
    if (sha256_sync(salt + i) === target) {
      self.postMessage({ ok: true, number: i, took: Date.now() - startTime });
      return;
    }
  }
  self.postMessage({ ok: false, error: "Solution not found within range" });
};
`;

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
  const workerRef = useRef<Worker | null>(null);

  const handleSolve = useCallback(async () => {
    if (verified || solving) return;
    setSolving(true);
    setErrorMsg(null);

    try {
      // 1. Fetch challenge from self-hosted FastAPI backend
      const res = await fetch("/api/v1/security/altcha/challenge");
      if (!res.ok) {
        throw new Error(`Challenge fetch failed: HTTP ${res.status}`);
      }
      const data = await res.json();
      const { algorithm, challenge, salt, signature, maxnumber = 50000 } = data;

      // 2. Spawn Web Worker to solve Proof-of-Work off main thread
      const blob = new Blob([SOLVER_WORKER_SCRIPT], { type: "application/javascript" });
      const workerUrl = URL.createObjectURL(blob);
      const worker = new Worker(workerUrl);
      workerRef.current = worker;

      worker.onmessage = (event) => {
        URL.revokeObjectURL(workerUrl);
        worker.terminate();
        workerRef.current = null;

        if (event.data && event.data.ok) {
          const number = event.data.number;
          const took = event.data.took;
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
        } else {
          setSolving(false);
          setErrorMsg(event.data?.error || "Proof-of-work computation failed");
        }
      };

      worker.onerror = (err) => {
        URL.revokeObjectURL(workerUrl);
        worker.terminate();
        workerRef.current = null;
        setSolving(false);
        setErrorMsg("Web Worker error during verification: " + err.message);
      };

      worker.postMessage({ salt, challenge, maxnumber });
    } catch (err: any) {
      setSolving(false);
      setErrorMsg(err.message || "Failed to contact ALTCHA service");
    }
  }, [verified, solving, onVerify]);

  useEffect(() => {
    if (autoSolve && !verified && !solving) {
      handleSolve();
    }
    return () => {
      if (workerRef.current) {
        workerRef.current.terminate();
        workerRef.current = null;
      }
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
