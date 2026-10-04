import { useState } from "react";
import { Check, Loader2 } from "lucide-react";

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

interface CloudflareTurnstileProps {
  verified: boolean;
  onVerify: (token: string) => void;
  className?: string;
  label?: string;
}

export function CloudflareTurnstile({
  verified,
  onVerify,
  className = "",
  label = "Verify you are human",
}: CloudflareTurnstileProps) {
  const [verifying, setVerifying] = useState(false);

  const handleVerify = () => {
    if (verified || verifying) return;
    setVerifying(true);
    setTimeout(() => {
      setVerifying(false);
      const simulatedToken = "0.cf_" + Math.random().toString(36).substring(2) + "_" + Date.now();
      onVerify(simulatedToken);
    }, 850);
  };

  return (
    <div
      className={`rounded-[var(--radius-control)] border border-white/15 bg-[#121316] p-3.5 select-none transition-colors ${className}`}
    >
      <div className="flex items-center justify-between gap-4">
        <button
          type="button"
          onClick={handleVerify}
          disabled={verified || verifying}
          className="flex items-center gap-3.5 text-left focus:outline-none group cursor-pointer disabled:cursor-default"
          aria-label={label}
        >
          <div
            className={`relative flex h-7 w-7 shrink-0 items-center justify-center rounded-[6px] border transition-all duration-200 ${
              verified
                ? "border-emerald-500 bg-emerald-500/20 text-emerald-400"
                : verifying
                ? "border-[#F38020] bg-[#F38020]/10"
                : "border-white/30 bg-white/[0.04] group-hover:border-white/60"
            }`}
          >
            {verified ? (
              <Check className="h-4 w-4 stroke-[2.5]" />
            ) : verifying ? (
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
                  : verifying
                  ? "text-[#F38020]"
                  : "text-white/90 group-hover:text-white"
              }`}
            >
              {verified ? "Success!" : verifying ? "Verifying..." : label}
            </span>
            <span className="text-[11px] text-white/40">
              {verified ? "Human verification complete" : "Cloudflare challenge"}
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
    </div>
  );
}
