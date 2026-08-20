const API_BASE_URL = (import.meta.env.VITE_PROPERTY_OPS_API_URL ?? 'http://127.0.0.1:8080').replace(/\/$/, '')

interface ApiErrorPayload {
  detail?: unknown
}

export class ApiError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function errorDetail(payload: ApiErrorPayload | null): string | null {
  if (typeof payload?.detail === 'string') return payload.detail
  if (Array.isArray(payload?.detail)) {
    const messages = payload.detail
      .map((item) => {
        if (!item || typeof item !== 'object') return null
        return 'msg' in item && typeof item.msg === 'string' ? item.msg : null
      })
      .filter((message): message is string => Boolean(message))
    return messages.length ? messages.join('; ') : null
  }
  return null
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
      },
    })
  } catch {
    throw new ApiError(`Cannot reach the PropertyOps API at ${API_BASE_URL}.`)
  }

  if (!response.ok) {
    let payload: ApiErrorPayload | null = null
    try {
      payload = await response.json() as ApiErrorPayload
    } catch {
      // The fallback below is more useful than exposing an invalid response body.
    }
    throw new ApiError(errorDetail(payload) ?? `API request failed (${response.status}).`, response.status)
  }

  return response.json() as Promise<T>
}
