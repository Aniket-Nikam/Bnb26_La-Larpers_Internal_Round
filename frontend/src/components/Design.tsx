import { Check, Copy, ShieldCheck } from "lucide-react";
import { useState } from "react";
import type { ReactNode } from "react";

export function StatusBadge({ value }: { value: string }) {
  const normalized = value.toUpperCase();
  const active = [
    "OPEN",
    "OFFERING",
    "RUNNING",
    "CONFIRMED",
    "COMPLETED",
    "READY",
    "VERIFIED",
  ];
  const success = ["CONFIRMED", "COMPLETED", "READY", "VERIFIED"];
  const danger = ["CANCELLED", "FAILED", "EXPIRED"];
  const tone = danger.includes(normalized)
    ? "danger"
    : active.includes(normalized)
      ? success.includes(normalized)
        ? "success"
        : "active"
      : "neutral";
  return (
    <span className="status-badge" data-tone={tone}>
      {normalized.replaceAll("_", " ")}
    </span>
  );
}

export function PageHeader({
  eyebrow,
  title,
  body,
  action,
}: {
  eyebrow?: string;
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-6 pb-8 pt-10 md:pb-12 md:pt-16">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <div className="flex flex-col items-start gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl space-y-4">
          <h1 className="page-title">{title}</h1>
          {body && (
            <p className="max-w-2xl text-base leading-relaxed muted sm:text-lg">
              {body}
            </p>
          )}
        </div>
        {action}
      </div>
    </header>
  );
}

export function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: ReactNode;
  detail?: string;
}) {
  return (
    <div className="min-w-0 py-4">
      <p className="text-sm font-medium muted">{label}</p>
      <p className="metric-number mt-2 break-words">{value}</p>
      {detail && <p className="mt-2 text-xs leading-relaxed muted">{detail}</p>}
    </div>
  );
}

export function LoadingBlock({ label = "Loading" }: { label?: string }) {
  return (
    <div
      className="surface-soft space-y-4 p-6"
      role="status"
      aria-label={label}
    >
      <div className="skeleton h-4 w-28" />
      <div className="skeleton h-8 w-3/4" />
      <div className="skeleton h-4 w-full" />
      <span className="sr-only">{label}</span>
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="surface-soft flex min-h-64 flex-col items-start justify-center p-8 sm:p-10">
      <ShieldCheck className="mb-6 h-8 w-8 accent" strokeWidth={1.6} />
      <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
      <p className="mt-3 max-w-lg leading-relaxed muted">{body}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

export function CopyButton({
  value,
  label = "Copy",
}: {
  value: string;
  label?: string;
}) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      className="button-secondary"
      type="button"
      onClick={async () => {
        await navigator.clipboard.writeText(value);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1800);
      }}
    >
      {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
      {copied ? "Copied" : label}
    </button>
  );
}
