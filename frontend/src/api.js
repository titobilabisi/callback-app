// Thin wrapper around fetch for the Flask backend. Every call goes to /api
// on the same address the app is served from (Vite proxies it in
// development), and the login session is an HttpOnly cookie.
export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

export async function api(path, { method = 'GET', body } = {}) {
  let res
  try {
    res = await fetch(`/api${path}`, {
      method,
      credentials: 'same-origin',
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError("Can't reach the server. Check your connection and try again.", 0)
  }

  let data = null
  try {
    data = await res.json()
  } catch {
    // Empty or non-JSON body; fall through to the status check below.
  }

  if (!res.ok) {
    throw new ApiError(data?.error || 'Something went wrong. Please try again.', res.status)
  }
  return data
}
