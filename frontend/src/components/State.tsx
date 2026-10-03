import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ApiError, useSession } from "../lib/api/client";
export function ErrorMessage({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <p
      role="alert"
      className="rounded-2xl border border-red-400/40 p-4 text-red-200"
    >
      {error instanceof Error ? error.message : "Unable to load this view."}
      {error instanceof ApiError && error.retryAfter
        ? ` Retry in ${error.retryAfter} seconds.`
        : ""}
    </p>
  );
}
export function OrganizerGuard({ children }: { children: ReactNode }) {
  const session = useSession();
  if (session.isPending) return <p role="status">Checking session…</p>;
  if (session.error) return <ErrorMessage error={session.error} />;
  if (!session.data)
    return (
      <p>
        Sign in to manage drops.{" "}
        <Link className="underline" to="/sign-in">
          Sign in
        </Link>
      </p>
    );
  if (!["organizer", "admin"].includes(session.data.principal.role))
    return <p>Organizer access is required.</p>;
  return children;
}
