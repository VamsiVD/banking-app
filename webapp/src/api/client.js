/**
 * The one place that talks to the API.
 *
 * Everything goes through `/api`, which the Vite dev server proxies to the
 * backend on :8000 (see vite.config.js). That keeps requests same-origin, so
 * the browser never runs a CORS preflight.
 *
 * The API answers with two different error shapes, and both are legitimate:
 *
 *   {"error": {"code": "...", "message": "..."}}   app/errors.py
 *   {"detail": "..."}                              the auth guard's HTTPException
 *
 * Callers should not have to know which one they are getting, so ApiError
 * flattens them into `message` and `code`.
 */

import { clearSession, loadSession } from '../auth.js'

const BASE = '/api'

export class ApiError extends Error {
  constructor(message, { status, code, cause } = {}) {
    super(message, { cause })
    this.name = 'ApiError'
    this.status = status
    // Branch on this, never on the message text — codes are a closed set.
    this.code = code
  }
}

function messageFrom(body, status) {
  if (body && body.error && body.error.message) {
    return body.error.message
  }
  if (body && typeof body.detail === 'string') {
    return body.detail
  }
  // FastAPI's 422 puts an array of field errors in `detail`.
  if (body && Array.isArray(body.detail)) {
    return body.detail.map((d) => d.msg).filter(Boolean).join('; ') || 'Invalid request'
  }
  return `Request failed (${status})`
}

async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  if (auth) {
    const session = loadSession()
    if (session) headers.Authorization = `Bearer ${session.token}`
  }

  let response
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (cause) {
    // No response at all: the API is down, or the dev server is running without
    // it. Worth saying plainly, because "failed to fetch" sends people hunting
    // in the wrong place.
    throw new ApiError('Cannot reach the server. Is the API running on :8000?', {
      status: 0,
      cause,
    })
  }

  // 204 and friends have no body to parse.
  const payload = response.status === 204 ? null : await response.json().catch(() => null)

  if (!response.ok) {
    if (response.status === 401) {
      // The token is gone, expired, or was never good. Drop it so the app
      // returns to the login screen instead of retrying with a dead token.
      clearSession()
      if (auth) {
        // `auth: false` requests (the login calls themselves) get a 401 for
        // bad credentials, not a dead session — nothing to kick anyone out of.
        window.dispatchEvent(new CustomEvent('session-expired'))
      }
    }
    throw new ApiError(messageFrom(payload, response.status), {
      status: response.status,
      code: payload && payload.error ? payload.error.code : undefined,
    })
  }

  return payload
}

export const api = {
  get: (path) => request(path),
  post: (path, body, options) => request(path, { method: 'POST', body, ...options }),
  patch: (path, body) => request(path, { method: 'PATCH', body }),
  delete: (path) => request(path, { method: 'DELETE' }),
}

// A 403 means the credentials were fine and the privileges were not — a
// different situation from 401, and the only one worth telling the user about
// in those words.
export const isForbidden = (error) => error instanceof ApiError && error.status === 403
