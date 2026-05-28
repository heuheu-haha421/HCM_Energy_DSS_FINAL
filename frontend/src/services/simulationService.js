import { api, unwrap } from './api'

async function logRequest(endpoint, payload, request) {
  console.log('[API REQUEST]', endpoint, payload)
  try {
    const response = await request()
    console.log('[API RESPONSE]', endpoint, response)
    return response
  } catch (error) {
    console.error('[API ERROR]', endpoint, error)
    throw error
  }
}

export const simulationService = {
  getCurrentLoad: async () =>
    unwrap(await logRequest(
      '/api/v1/simulation/current-load',
      null,
      () => api.get('/api/v1/simulation/current-load')
    )),

  allocate: async ({ year, weights }) => {
    const endpoint = `/api/v1/simulation/allocate?year=${encodeURIComponent(year)}`
    const payload = {
      year,
      weights,
    }

    return unwrap(await logRequest(endpoint, payload, () => api.post(endpoint, payload)))
  },

  gridStressPriorities: async ({ year, limit = 10 }) => {
    const endpoint = `/api/v1/simulation/grid-stress-priorities?year=${encodeURIComponent(year)}&limit=${limit}`
    return unwrap(await logRequest(endpoint, { year, limit }, () => api.get(endpoint)))
  },

  topRisks: async ({ year, limit = 10 }) =>
    simulationService.gridStressPriorities({ year, limit }),

  toggleDemo: async (isDemo, intervalSeconds) => {
    const endpoint = '/api/v1/demo/toggle'
    const payload = {
      is_demo: isDemo,
      interval_seconds: intervalSeconds,
    }

    return unwrap(await logRequest(endpoint, payload, () => api.post(endpoint, payload)))
  },
}
