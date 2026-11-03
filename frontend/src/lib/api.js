const API_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD
    ? 'https://cintac-comexcontrol-1.onrender.com'
    : 'http://127.0.0.1:8000')

function getToken() {
  return sessionStorage.getItem('comex_token')
}

function setSession(token) {
  sessionStorage.setItem('comex_token', token)
}

function clearSession() {
  sessionStorage.removeItem('comex_token')
}

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {})
  const token = getToken()

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })

  let data = null

  try {
    data = await response.json()
  } catch {
    data = null
  }

  if (response.status === 401) {
    clearSession()
    window.dispatchEvent(new Event('comex:unauthorized'))
  }

  if (!response.ok) {
    throw new Error(
      data?.detail || 'No fue posible completar la solicitud'
    )
  }

  return data
}

export {
  API_URL,
  apiFetch,
  clearSession,
  getToken,
  setSession,
}