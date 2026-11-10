"use client";

import { useSyncExternalStore } from "react";

/** The URL hash as a string, kept in sync with the browser. The selected match and tab live here, so every view is linkable. */
export function useHash(): string {
  return useSyncExternalStore(
    (notify) => {
      window.addEventListener("hashchange", notify);
      return () => window.removeEventListener("hashchange", notify);
    },
    () => window.location.hash.slice(1),
    () => "",
  );
}

export function setHash(patch: Record<string, string | number>) {
  const params = new URLSearchParams(window.location.hash.slice(1));
  for (const [k, v] of Object.entries(patch)) params.set(k, String(v));
  window.location.hash = params.toString();
}
