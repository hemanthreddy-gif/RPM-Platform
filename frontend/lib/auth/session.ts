export type AppRole = "patient" | "physician" | "admin";

export type AuthSession = {
  accessToken: string;
  refreshToken: string;
  role: AppRole;
  userId: string;
  expiresAt: number;
};

const SESSION_KEY = "rpm.synthetic.session.v1";

export function getSession(): AuthSession | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    window.localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function setSession(session: AuthSession): void {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function accessTokenExpired(session: AuthSession, now = Date.now()): boolean {
  // Refresh shortly before expiry so the UI does not retry a mutation with a known-expired token.
  return session.expiresAt <= now + 30_000;
}

export function clearSession(): void {
  window.localStorage.removeItem(SESSION_KEY);
}
