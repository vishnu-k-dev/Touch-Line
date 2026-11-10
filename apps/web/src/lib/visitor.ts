const KEY = "touchline.visitor";
const VALID = /^[A-Za-z0-9_-]{8,64}$/;
let inMemory: string | null = null;

function fresh(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return Array.from({ length: 24 }, () => Math.floor(Math.random() * 36).toString(36)).join("");
}

/**
 * A random, anonymous id kept in this browser so the analyst's history can be restored.
 * It is not an account and carries no personal data. Falls back to memory if storage is blocked.
 */
export function visitorId(): string {
  try {
    let id = window.localStorage.getItem(KEY);
    if (!id || !VALID.test(id)) {
      id = fresh();
      window.localStorage.setItem(KEY, id);
    }
    return id;
  } catch {
    inMemory ??= fresh();
    return inMemory;
  }
}

export const visitorHeaders = (): Record<string, string> => ({ "X-Visitor-Id": visitorId() });
