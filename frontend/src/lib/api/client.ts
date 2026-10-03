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
    if (!(path === "/auth/session"))
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
    const result = (await response.json()) as Schema["ErrorResponse"];
    throw new ApiError(
      result.error.code,
      result.error.message,
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
