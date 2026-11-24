/**
 * Continue with Google: the press records a random `state` and when this
 * tab arrived (so a stale or replayed callback is refused) before leaving
 * for Google, then `/sso-callback` reads it back exactly once.
 */

const STORAGE_KEY = "studio.google-sign-in"
/** Long enough to choose an account and approve; a record older than this is not trusted. */
export const GOOGLE_SIGN_IN_MAX_AGE_MS = 15 * 60 * 1000

export interface GoogleSignInStart {
  state: string
  startedAt: number
}

export function googleSignInEnabled(): boolean {
  return Boolean(import.meta.env.VITE_GOOGLE_CLIENT_ID)
}

export function newGoogleState(): string {
  return Array.from(crypto.getRandomValues(new Uint8Array(24)), (byte) => byte.toString(16).padStart(2, "0")).join("")
}

export function googleRedirectUri(): string {
  return `${window.location.origin}/sso-callback`
}

export function googleAuthUrl(state: string): string {
  return `https://accounts.google.com/o/oauth2/v2/auth?${new URLSearchParams({
    client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID ?? "",
    redirect_uri: googleRedirectUri(),
    response_type: "code",
    scope: "openid email profile",
    prompt: "consent",
    state,
  }).toString()}`
}

export function beginGoogleSignIn() {
  const start: GoogleSignInStart = { state: newGoogleState(), startedAt: Date.now() }
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(start))
  } catch {
    // Storage refused: the callback finds nothing and the person starts again.
  }
  window.location.href = googleAuthUrl(start.state)
}

/**
 * The record this tab made when Google was pressed, if Google sent back the
 * same `state` recently. Read once: it is forgotten whether or not it matches.
 */
export function takeGoogleSignIn(returnedState: string | null, now = Date.now()): GoogleSignInStart | null {
  let raw: string | null = null
  try {
    raw = sessionStorage.getItem(STORAGE_KEY)
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    return null
  }
  if (!raw || !returnedState) return null
  try {
    const start = JSON.parse(raw) as Partial<GoogleSignInStart>
    if (typeof start.state !== "string" || start.state.length < 32 || start.state !== returnedState) return null
    if (typeof start.startedAt !== "number" || now - start.startedAt > GOOGLE_SIGN_IN_MAX_AGE_MS || start.startedAt > now + 60_000) return null
    return { state: start.state, startedAt: start.startedAt }
  } catch {
    return null
  }
}
