"use client";

import { useEffect, useState } from "react";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(`Cannot reach the API at ${API_URL}. Is it running?`, 0);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export const apiGet = <T,>(path: string, signal?: AbortSignal, headers?: Record<string, string>) =>
  request<T>(path, { signal, headers });

export const apiPost = <T,>(path: string, body: unknown, signal?: AbortSignal, headers?: Record<string, string>) =>
  request<T>(path, { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body), signal });

export const apiDelete = <T,>(path: string, headers?: Record<string, string>) => request<T>(path, { method: "DELETE", headers });

type Slot<T> = { path: string | null; data?: T; error?: string };

/** GET `path` (null = idle). State is keyed by path, so a stale response is never shown for a newer path. */
export function useApi<T>(path: string | null) {
  const [slot, setSlot] = useState<Slot<T>>({ path: null });
  useEffect(() => {
    if (!path) return;
    const ctl = new AbortController();
    apiGet<T>(path, ctl.signal).then(
      (data) => setSlot({ path, data }),
      (err: Error) => {
        if (!ctl.signal.aborted) setSlot({ path, error: err.message });
      },
    );
    return () => ctl.abort();
  }, [path]);
  const fresh = slot.path === path;
  return { data: fresh ? slot.data : undefined, error: fresh ? slot.error : undefined, loading: path !== null && !fresh };
}
