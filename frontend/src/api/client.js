// One place for every call to the backend.
// Adds the JWT from localStorage and turns API errors into readable messages.

// Backend address comes from the VITE_API_URL env variable, with a local default
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
// localStorage key where the login token is kept
export const TOKEN_KEY = 'campusbite_token'

// Builds the full request URL and adds query params, skipping empty ones so unused filters are not sent
function buildUrl(path, params) {
  const url = new URL(API_URL + path)
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      const isEmpty = value === undefined || value === null || value === ''
      if (!isEmpty) url.searchParams.set(key, value)
    })
  }
  return url
}

// Turns the backend's error body into one message that can be shown to the user
function errorMessage(data, status) {
  if (!data || !data.detail) return `Request failed (${status})`
  // FastAPI validation errors come back as a list, one entry per bad field
  if (Array.isArray(data.detail)) {
    const messages = data.detail.map((issue) => {
      // loc is the path to the bad value, like ["body", "email"]; its last part is the field name
      const fieldName = issue.loc?.slice(-1)[0] ?? 'field'
      return `${fieldName}: ${issue.msg}`
    })
    return messages.join(', ')
  }
  return data.detail
}

// Sends a request to the backend and returns the parsed JSON, or throws an Error with a readable message
export async function api(path, { method = 'GET', body, params } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem(TOKEN_KEY)
  // Attach the saved login token so the backend knows who is calling
  if (token) headers.Authorization = `Bearer ${token}`

  // Only requests that carry data (like POST) have a body to send
  let jsonBody
  if (body !== undefined) jsonBody = JSON.stringify(body)

  let response
  try {
    response = await fetch(buildUrl(path, params), { method, headers, body: jsonBody })
  } catch {
    // fetch only throws on network failures, not on error status codes
    throw new Error("Can't reach the server. Check that the backend is running.")
  }

  // Some responses have no JSON body, so fall back to null instead of failing
  const data = await response.json().catch(() => null)

  if (response.status === 401 && token) {
    // Token expired or invalid: AuthContext listens for this and logs the user out
    window.dispatchEvent(new Event('auth:logout'))
  }
  if (!response.ok) {
    const error = new Error(errorMessage(data, response.status))
    // Keep the status code so callers can react to specific errors
    error.status = response.status
    throw error
  }
  return data
}
