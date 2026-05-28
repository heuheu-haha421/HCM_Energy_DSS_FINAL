import { api, unwrap } from './api'

function normalizeAuthPayload(response) {
  const payload = unwrap(response)
  const data = payload?.access_token
    ? payload
    : payload?.data?.access_token
      ? payload.data
      : payload

  if (!data?.access_token) {
    throw new Error('Login response did not include access_token')
  }

  return data
}

export const authService = {
  login: async (username, password) =>
    normalizeAuthPayload(await api.post('/api/v1/auth/login', { username, password })),

  me: async () =>
    unwrap(await api.get('/api/v1/auth/me')),
}
