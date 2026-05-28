import { api, unwrap } from './api'

export const modelService = {
  list: async () =>
    unwrap(await api.get('/api/v1/models/')),

  active: async () =>
    unwrap(await api.get('/api/v1/models/active')),

  metrics: async (id) =>
    unwrap(await api.get(`/api/v1/models/${id}/metrics`)),

  acceptanceGraph: async (id) =>
    unwrap(await api.get(`/api/v1/models/${id}/acceptance-graph`)),

  setActive: async (id) =>
    unwrap(await api.post(`/api/v1/models/${id}/set-active`)),

  compare: async (ids) =>
    unwrap(await api.get(`/api/v1/models/compare?ids=${ids.join(',')}`)),

  upload: async (formData) => {
    const token = api.auth.getToken()
    const res = await fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/v1/models/`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    const payload = await res.json().catch(() => null)
    if (!res.ok) {
      const detail = payload?.detail || payload?.error
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail || res.statusText))
    }
    return unwrap(payload)
  },

  startPrediction: async () =>
    unwrap(await api.post('/api/v1/prediction/start')),

  stopPrediction: async () =>
    unwrap(await api.post('/api/v1/prediction/stop')),

  restartPrediction: async () =>
    unwrap(await api.post('/api/v1/prediction/restart')),

  predict: async () =>
    unwrap(await api.post('/api/v1/prediction/start')),
}
