/**
 * The signed-in session, as the browser remembers it.
 *
 * localStorage can throw outright — private windows, browsers set to block site
 * data — so every access is wrapped. A session we cannot read is the same thing
 * as no session: the user signs in again. It is never worth a crash.
 */

const KEY = 'banking-app.session'

/** @returns {{token: string, role: string, email: string} | null} */
export function loadSession() {
  try {
    const raw = window.localStorage.getItem(KEY)
    if (!raw) return null

    const session = JSON.parse(raw)
    // A half-written or hand-edited entry is not a session.
    return session && session.token ? session : null
  } catch {
    return null
  }
}

export function saveSession(session) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(session))
  } catch {
    // Storage is unavailable. The session still lives in React state, so this
    // costs the user a re-login on refresh and nothing else.
  }
}

export function clearSession() {
  try {
    window.localStorage.removeItem(KEY)
  } catch {
    // Nothing stored means nothing to clear.
  }
}
