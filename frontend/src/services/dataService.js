import { api, unwrap } from './api'

function parseMaybeJson(value) {
  if (typeof value !== 'string') return value
  try {
    return JSON.parse(value)
  } catch {
    return value
  }
}

function extractGeoJson(response) {
  const parsedResponse = parseMaybeJson(response)
  const payload = parseMaybeJson(unwrap(parsedResponse))
  const nestedData = parseMaybeJson(payload?.data)
  const nestedResponse = parseMaybeJson(payload?.response)

  if (payload?.type === 'FeatureCollection' && Array.isArray(payload.features)) {
    return payload
  }

  if (nestedData?.type === 'FeatureCollection' && Array.isArray(nestedData.features)) {
    return nestedData
  }

  if (nestedResponse?.type === 'FeatureCollection' && Array.isArray(nestedResponse.features)) {
    return nestedResponse
  }

  console.error('[GEOJSON ERROR] Invalid FeatureCollection', response)
  throw new Error('Invalid GeoJSON FeatureCollection')
}

export const dataService = {
  status: async () =>
    unwrap(await api.get('/api/v1/data/status')),

  geojson: async () =>
    extractGeoJson(await api.get('/api/v1/geojson/wards')),

  getWardsGeoJson: async () =>
    extractGeoJson(await api.get('/api/v1/geojson/wards')),

  uploadEnergy: (file) =>
    api.upload('/api/v1/data/upload-energy', file),

  uploadWardStats: (file) =>
    api.upload('/api/v1/data/upload-ward-stats', file),

  uploadHoliday: (file) =>
    api.upload('/api/v1/data/upload-holiday', file),
}
