import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { ApiError, useSession } from "../lib/api/client";
export function ErrorMessage({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-[var(--radius-control)] border border-red-400/30 bg-red-400/[0.06] p-4 text-sm text-red-200"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <p>
        {error instanceof Error ? error.message : "Unable to load this view."}
        {error instanceof ApiError && error.retryAfter
          ? ` Retry in ${error.retryAfter} seconds.`
          : ""}
      </p>
    </div>
  );
}
export function OrganizerGuard({ children }: { children: ReactNode }) {
  const session = useSession();
  if (session.isPending)
    return (
      <p role="status" className="py-16 muted">
        Checking session...
      </p>
    );
  if (session.error) return <ErrorMessage error={session.error} />;
  if (!session.data)
    return (
      <div className="surface-soft my-16 p-8">
        <p>
          Sign in to manage drops.{" "}
          <Link className="link" to="/sign-in">
            Sign in
          </Link>
        </p>
      </div>
    );
  if (!["organizer", "admin"].includes(session.data.principal.role))
    return (
      <div className="surface-soft my-16 p-8">
        Organizer access is required.
      </div>
    );
  return children;
}
