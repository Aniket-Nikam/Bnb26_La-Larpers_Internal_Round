import { useEffect, useRef, useState } from "react";
import { Check, Loader2 } from "lucide-react";

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: HTMLElement | string,
        params: {
          sitekey: string;
          callback?: (token: string) => void;
          "error-callback"?: (code?: string) => void;
          "expired-callback"?: () => void;
          theme?: "light" | "dark" | "auto";
          size?: "normal" | "compact" | "flexible";
          action?: string;
          cData?: string;
          retry?: "auto" | "never";
          "refresh-expired"?: "auto" | "manual" | "never";
        }
      ) => string;
      reset: (widgetId?: string) => void;
      remove: (widgetId?: string) => void;
      getResponse: (widgetId?: string) => string | undefined;
    };
  }
}

export function CloudflareLogo({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M18.8 10.3C18.4 6.8 15.5 4 12 4C9.1 4 6.6 6 5.5 8.7C4.1 9.1 3 10.4 3 12C3 13.9 4.6 15.5 6.5 15.5H18.5C20.4 15.5 22 13.9 22 12C22 10.3 20.6 8.9 18.8 10.3Z"
        fill="#F38020"
      />
      <path
        d="M19.2 11.2C18.9 10.2 18.2 9.4 17.2 9C17 9 16.8 9.3 16.9 9.5C17.4 10.2 17.6 11.1 17.5 12H7C6.7 12 6.5 12.2 6.5 12.5C6.5 12.8 6.7 13 7 13H18.5C19.9 13 21 11.9 21 10.5C21 10.2 20.9 9.9 20.8 9.7C20.6 9.6 20.4 9.8 20.4 10C20.3 10.5 19.8 10.9 19.2 11.2Z"
        fill="#FAAD3F"
      />
    </svg>
  );
}

// Ensure Cloudflare Turnstile script is loaded
let scriptLoadPromise: Promise<boolean> | null = null;
function ensureTurnstileScript(): Promise<boolean> {
  if (typeof window === "undefined") return Promise.resolve(false);
  if (window.turnstile) return Promise.resolve(true);
  if (scriptLoadPromise) return scriptLoadPromise;

  scriptLoadPromise = new Promise<boolean>((resolve) => {
    // If script already exists in document
    const existing = document.querySelector('script[src*="challenges.cloudflare.com/turnstile"]');
    if (existing) {
      let elapsed = 0;
      const interval = setInterval(() => {
        elapsed += 100;
        if (window.turnstile) {
          clearInterval(interval);
          resolve(true);
        } else if (elapsed > 4000) {
          clearInterval(interval);
          resolve(false);
        }
      }, 100);
      return;
    }

    const script = document.createElement("script");
    script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
    script.async = true;
    script.defer = true;

    script.onload = () => {
      let elapsed = 0;
      const interval = setInterval(() => {
        elapsed += 50;
        if (window.turnstile) {
          clearInterval(interval);
          resolve(true);
        } else if (elapsed > 3000) {
          clearInterval(interval);
          resolve(false);
        }
      }, 50);
    };

    script.onerror = () => {
      console.warn("Could not load Cloudflare Turnstile API; falling back to offline mode.");
      resolve(false);
    };

    document.head.appendChild(script);
  });

  return scriptLoadPromise;
}

interface CloudflareTurnstileProps {
  verified: boolean;
  onVerify: (token: string) => void;
  className?: string;
  label?: string;
  action?: string;
}

export function CloudflareTurnstile({
  verified,
  onVerify,
  className = "",
  label = "Verify you are human",
  action,
}: CloudflareTurnstileProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const [cfLoaded, setCfLoaded] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [fallbackVerifying, setFallbackVerifying] = useState(false);

  // Cloudflare official test key: 2x00000000000000000000AB forces interactive verification (checkbox)
  // or user-provided VITE_CLOUDFLARE_SITEKEY
  const siteKey =
    (import.meta.env.VITE_CLOUDFLARE_SITEKEY as string | undefined) ||
    "2x00000000000000000000AB";

  useEffect(() => {
    let isCancelled = false;

    ensureTurnstileScript()
      .then((ready) => {
        if (isCancelled) return;
        if (!ready || !window.turnstile || !containerRef.current) {
          setLoadError(true);
          return;
        }

        try {
          // Clean up any existing widget in container before re-rendering
          if (widgetIdRef.current && window.turnstile) {
            window.turnstile.remove(widgetIdRef.current);
            widgetIdRef.current = null;
          }
          containerRef.current.innerHTML = "";

          const id = window.turnstile.render(containerRef.current, {
            sitekey: siteKey,
            theme: "dark",
            size: "normal",
            action: action || "challenge",
            callback: (token: string) => {
              if (!isCancelled) {
                onVerify(token);
              }
            },
            "error-callback": (errCode) => {
              console.warn("Cloudflare Turnstile challenge error:", errCode);
            },
            "expired-callback": () => {
              console.info("Cloudflare Turnstile token expired; re-verifying.");
            },
          });

          widgetIdRef.current = id;
          setCfLoaded(true);
        } catch (err) {
          console.warn("Failed to render Cloudflare Turnstile widget:", err);
          if (!isCancelled) {
            setLoadError(true);
          }
        }
      })
      .catch(() => {
        if (!isCancelled) setLoadError(true);
      });

    return () => {
      isCancelled = true;
      if (widgetIdRef.current && window.turnstile) {
        try {
          window.turnstile.remove(widgetIdRef.current);
        } catch {
          // ignore cleanup errors
        }
        widgetIdRef.current = null;
      }
    };
  }, [siteKey, action, onVerify]);

  const handleFallbackVerify = () => {
    if (verified || fallbackVerifying) return;
    setFallbackVerifying(true);
    setTimeout(() => {
      setFallbackVerifying(false);
      const simulatedToken = "0.cf_test_" + Math.random().toString(36).substring(2) + "_" + Date.now();
      onVerify(simulatedToken);
    }, 700);
  };

  return (
    <div
      className={`rounded-[var(--radius-control)] border border-white/15 bg-[#121316] p-3 select-none transition-colors ${className}`}
    >
      {/* Real Cloudflare Turnstile Widget Mount Point */}
      <div
        ref={containerRef}
        className={`min-h-[65px] flex items-center justify-center ${loadError ? "hidden" : "block"}`}
      />

      {/* Loading state before Turnstile iframe appears */}
      {!cfLoaded && !loadError && (
        <div className="flex h-[65px] items-center justify-center gap-2.5 text-xs text-white/50">
          <Loader2 className="h-4 w-4 animate-spin text-[#F38020]" />
          <span>Connecting to Cloudflare Turnstile...</span>
        </div>
      )}

      {/* Fallback button if Turnstile script is blocked by ad-blocker or offline */}
      {loadError && (
        <div className="flex items-center justify-between gap-4">
          <button
            type="button"
            onClick={handleFallbackVerify}
            disabled={verified || fallbackVerifying}
            className="flex items-center gap-3.5 text-left focus:outline-none group cursor-pointer disabled:cursor-default"
            aria-label={label}
          >
            <div
              className={`relative flex h-7 w-7 shrink-0 items-center justify-center rounded-[6px] border transition-all duration-200 ${
                verified
                  ? "border-emerald-500 bg-emerald-500/20 text-emerald-400"
                  : fallbackVerifying
                  ? "border-[#F38020] bg-[#F38020]/10"
                  : "border-white/30 bg-white/[0.04] group-hover:border-white/60"
              }`}
            >
              {verified ? (
                <Check className="h-4 w-4 stroke-[2.5]" />
              ) : fallbackVerifying ? (
                <Loader2 className="h-4 w-4 animate-spin text-[#F38020]" />
              ) : (
                <div className="h-2 w-2 rounded-sm bg-transparent group-hover:bg-white/10" />
              )}
            </div>
            <div className="flex flex-col">
              <span
                className={`text-sm font-medium transition-colors ${
                  verified
                    ? "text-emerald-300"
                    : fallbackVerifying
                    ? "text-[#F38020]"
                    : "text-white/90 group-hover:text-white"
                }`}
              >
                {verified ? "Success!" : fallbackVerifying ? "Verifying..." : label}
              </span>
              <span className="text-[11px] text-white/40">
                {verified ? "Verification complete" : "Cloudflare challenge (offline mode)"}
              </span>
            </div>
          </button>

          <div className="flex flex-col items-end shrink-0 pl-2">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold tracking-tight text-white/80">
              <CloudflareLogo className="h-3.5 w-3.5" />
              <span>Cloudflare</span>
            </div>
            <div className="mt-0.5 flex gap-1.5 text-[9px] text-white/40">
              <span className="hover:underline hover:text-white/60 cursor-pointer">Privacy</span>
              <span>•</span>
              <span className="hover:underline hover:text-white/60 cursor-pointer">Terms</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
