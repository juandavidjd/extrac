const SESSION_KEY = "odi_session_id";

export function getSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(SESSION_KEY);
}

export function setSessionId(id: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(SESSION_KEY, id);
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SESSION_KEY);
}
