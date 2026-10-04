import { useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "./generated";
export type Schema = components["schemas"];
export type Drop = Schema["DropDetail"];
export type Entry = Schema["EntryState"];
export type Session = Schema["SessionResponse"];
export type Page<T> = { items: T[]; next_cursor: string | null };
let csrf: string | null = null;

export class ApiError extends Error {
  code: string;
  status: number;
  retryAfter: number | null;
  constructor(
    code: string,
    message: string,
    status: number,
    retryAfter: number | null,
  ) {
    super(message);
    this.code = code;
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  operationKey?: string,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    if (csrf) headers["X-CSRF-Token"] = csrf;
    if (
      ![
        "/auth/session",
        "/auth/password-session",
        "/auth/phone-session",
        "/auth/register",
        "/auth/otp/send",
      ].includes(path)
    )
      headers["Idempotency-Key"] = operationKey ?? crypto.randomUUID();
  }
  const options = {
    method,
    credentials: "same-origin" as const,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  };
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, options);
  } catch {
    // The same operation key is retained when the write response is lost.
    response = await fetch(`/api/v1${path}`, options);
  }
  if (!response.ok) {
    const raw = await response.text();
    let result: Schema["ErrorResponse"] | null = null;
    if (raw) {
      try {
        result = JSON.parse(raw) as Schema["ErrorResponse"];
      } catch {
        // Gateways and stopped dev servers can return an empty or HTML body.
      }
    }
    const message =
      result?.error?.message ??
      (response.status >= 500
        ? "The FairDrop backend is unavailable. Start the backend and try again."
        : `Request failed (${response.status}).`);
    throw new ApiError(
      result?.error?.code ?? "BACKEND_UNAVAILABLE",
      message,
      response.status,
      response.headers.has("Retry-After")
        ? Number(response.headers.get("Retry-After"))
        : null,
    );
  }
  return response.status === 204
    ? (undefined as T)
    : ((await response.json()) as T);
}

export function useSession() {
  return useQuery({
    queryKey: ["session"],
    queryFn: async () => {
      try {
        const session = await api<Session>("/auth/me");
        csrf = session.csrf_token;
        return session;
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          csrf = null;
          return null;
        }
        throw error;
      }
    },
    retry: false,
  });
}

export function useAction<T = unknown>() {
  const cache = useQueryClient();
  const pending = useRef<{ fingerprint: string; key: string } | null>(null);
  return useMutation({
    mutationFn: (v: { path: string; method?: string; body?: unknown }) => {
      const fingerprint = JSON.stringify(v);
      if (pending.current?.fingerprint !== fingerprint)
        pending.current = { fingerprint, key: crypto.randomUUID() };
      return api<T>(
        v.path,
        v.method ?? "POST",
        v.body ?? {},
        pending.current.key,
      );
    },
    onSuccess: async () => {
      pending.current = null;
      await cache.invalidateQueries();
    },
  });
}

export function useLogin() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: (access_code: string) =>
      api<Session>("/auth/session", "POST", { access_code }),
    onSuccess: (session) => {
      csrf = session.csrf_token;
      cache.clear();
      cache.setQueryData(["session"], session);
    },
  });
}

export type OtpSendResponse = Schema["OtpSendResponse"];

function useAccountSession(
  path: "/auth/password-session" | "/auth/phone-session" | "/auth/register",
) {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: (body: unknown) => api<Session>(path, "POST", body),
    onSuccess: (session) => {
      csrf = session.csrf_token;
      cache.clear();
      cache.setQueryData(["session"], session);
    },
  });
}

export function useSendOtp() {
  return useMutation({
    mutationFn: (body: { phone_number: string; purpose: "register" | "login" }) =>
      api<OtpSendResponse>("/auth/otp/send", "POST", body),
  });
}

export function usePhoneLogin() {
  return useAccountSession("/auth/phone-session");
}

export function usePasswordLogin() {
  return useAccountSession("/auth/password-session");
}

export function useRegister() {
  return useAccountSession("/auth/register");
}

export function useLogout() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: () => api("/auth/session", "DELETE"),
    onSuccess: () => {
      csrf = null;
      cache.clear();
      cache.setQueryData(["session"], null);
    },
  });
}

export function time(value: string) {
  return new Date(value).toLocaleString();
}
