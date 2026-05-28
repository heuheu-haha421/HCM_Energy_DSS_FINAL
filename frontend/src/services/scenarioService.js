import { api, unwrap } from './api'

export const scenarioService = {
  list: async () =>
    unwrap(await api.get('/api/v1/scenarios/')),

  create: async (data) =>
    unwrap(await api.post('/api/v1/scenarios/', data)),

  update: async (id, data) =>
    unwrap(await api.put(`/api/v1/scenarios/${id}`, data)),

  delete: async (id) =>
    unwrap(await api.del(`/api/v1/scenarios/${id}`)),

  apply: async (id) =>
    unwrap(await api.post(`/api/v1/scenarios/${id}/apply`)),
}
