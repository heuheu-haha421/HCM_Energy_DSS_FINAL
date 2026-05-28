/**
 * api.js — Toàn bộ API calls cho Energy DSS Frontend (React + Vite)
 *
 * Cách dùng:
 *   import api from '@/services/api'
 *
 * Cấu hình URL trong file .env của Vite:
 *   VITE_API_URL=http://localhost:8000
 *   VITE_WS_URL=ws://localhost:8000
 */

const DEFAULT_WS_URL = typeof window === 'undefined'
  ? 'ws://localhost:8000'
  : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`

const BASE_URL = import.meta.env.VITE_API_URL ?? ''
const WS_URL   = import.meta.env.VITE_WS_URL   ?? DEFAULT_WS_URL

// ─────────────────────────────────────────────
// TOKEN HELPERS
// ─────────────────────────────────────────────
export const normalizeToken = (value) => {
  if (typeof value !== 'string') return null

  const token = value.replace(/^Bearer\s+/i, '').trim()
  if (!token || token === 'undefined' || token === 'null') return null

  return token
}

const getToken = () => (
  normalizeToken(localStorage.getItem('access_token')) ||
  normalizeToken(sessionStorage.getItem('access_token'))
)

const saveToken = (value) => {
  const token = normalizeToken(value)
  if (!token) {
    clearToken()
    return null
  }

  localStorage.setItem('access_token', token)
  return token
}

const clearToken = () => {
  localStorage.removeItem('access_token')
  sessionStorage.removeItem('access_token')
}

const authHeader = () => {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// ─────────────────────────────────────────────
// CORE FETCH WRAPPER
// ─────────────────────────────────────────────
async function request(method, path, body = null, isFormData = false) {
  const headers = isFormData
    ? authHeader()
    : {
        'Content-Type': 'application/json',
        ...authHeader()
      }

  const options = {
    method,
    headers,
    ...(body !== null ? { body: isFormData ? body : JSON.stringify(body) } : {})
  }

  const res = await fetch(`${BASE_URL}${path}`, options)
  const contentType = res.headers.get('content-type') ?? ''
  const payload = contentType.includes('application/json')
    ? await res.json().catch(() => null)
    : await res.text().catch(() => '')

  if (!res.ok) {
    const err = payload && typeof payload === 'object'
      ? payload
      : { error: payload || res.statusText }
    const message =
      typeof err.detail === 'string' ? err.detail :
      typeof err.error === 'string' ? err.error :
      JSON.stringify(err.detail ?? err.error)
    throw Object.assign(new Error(message || 'Request failed'), {
      status: res.status,
      data: err
    })
  }

  return payload
}

export const unwrap = (response) => response?.data ?? response

const get    = (path)        => request('GET',    path)
const post   = (path, body)  => request('POST',   path, body)
const put    = (path, body)  => request('PUT',    path, body)
const del    = (path)        => request('DELETE', path)
const upload = (path, file, field = 'file') => {
  const fd = new FormData()
  fd.append(field, file)
  return request('POST', path, fd, true)
}

// ─────────────────────────────────────────────
// GROUP 0 — AUTH
// ─────────────────────────────────────────────
export const auth = {
  /**
   * POST /api/v1/auth/login
   * body: { username, password }
   * → { access_token, token_type, role }
   */
  login: ({ username, password }) =>
    post('/api/v1/auth/login', { username, password }),

  /**
   * GET /api/v1/auth/me
   * → { username, role }
   */
  me: () => get('/api/v1/auth/me'),

  saveToken,
  clearToken,
  getToken,
  isLoggedIn: () => !!getToken()
}

// ─────────────────────────────────────────────
// GROUP 1 — SIMULATION & MAP
// ─────────────────────────────────────────────
export const simulation = {
  /**
   * GET /api/v1/simulation/current-load
   * → latest prediction record, including predicted_load
   */
  getCurrentLoad: () =>
    get('/api/v1/simulation/current-load'),

  /**
   * POST /api/v1/simulation/allocate?year=2025
   * body: {
   *   year: 2025,
   *   weights: { residential, industrial, commercial, services }
   * }
   * → [ { ward_code, ward_name, allocation_pct, allocated_kwh, priority_level } ]
   */
  allocate: ({ year, weights }) =>
    post(`/api/v1/simulation/allocate?year=${encodeURIComponent(year)}`, { year, weights }),

  /**
   * GET /api/v1/simulation/grid-stress-priorities?year=2025&limit=10
   * → { total_load, count, results: [ { ward_code, ward_name, allocated_kwh, priority_level, primary_reason } ] }
   */
  gridStressPriorities: ({ year, limit = 10 }) =>
    get(`/api/v1/simulation/grid-stress-priorities?year=${encodeURIComponent(year)}&limit=${limit}`),

  topRisks: ({ year, limit = 10 }) =>
    get(`/api/v1/simulation/grid-stress-priorities?year=${encodeURIComponent(year)}&limit=${limit}`)
}

// ─────────────────────────────────────────────
// GROUP 2 — WEBSOCKET live-predict
// ─────────────────────────────────────────────

/**
 * Tạo WebSocket kết nối tới /ws/v1/live-predict
 * Server push: { week, timestamp, predicted_load, simulated_temp }
 *
 * @param {function} onMessage  - callback(data: object)
 * @param {function} [onError]  - callback(event)
 * @param {function} [onClose]  - callback()
 * @returns WebSocket instance (gọi .close() để ngắt)
 *
 * Ví dụ:
 *   const ws = createLiveSocket(
 *     data => setLoad(data.predicted_load),
 *     err  => console.error(err)
 *   )
 *   // cleanup:
 *   ws.close()
 */
export function createLiveSocket(onMessage, onError, onClose, token = auth.getToken()) {
  if (!token) {
    throw new Error('WebSocket requires a logged-in JWT access token')
  }

  const url = `${WS_URL}/ws/v1/live-predict?token=${encodeURIComponent(token)}`
  const ws = new WebSocket(url)

  ws.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data))
    } catch {
      onMessage(event.data)
    }
  }

  ws.onerror = onError  ?? ((e) => console.error('[WS] error', e))
  ws.onclose = onClose  ?? (() => console.log('[WS] closed'))

  // Keep-alive mỗi 30s
  const ping = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'noop' }))
    } else {
      clearInterval(ping)
    }
  }, 30_000)

  ws.addEventListener('close', () => clearInterval(ping))

  return ws
}

// ─────────────────────────────────────────────
// GROUP 3 — SCENARIOS CRUD
// ─────────────────────────────────────────────
export const scenarios = {
  /**
   * GET /api/v1/scenarios/
   * → [ { id, weight, created_by, created_at } ]
   *
   * weight là JSON string: { w_residential, w_industrial, w_commercial, w_services }
   * parse: JSON.parse(scenario.weight)
   */
  getAll: () => get('/api/v1/scenarios/'),

  /**
   * POST /api/v1/scenarios/
   * body: {
   *   weight: { w_residential, w_industrial, w_commercial, w_services },
   *   created_by: <user_id>     ← lấy từ auth.me() rồi map sang user_id
   * }
   * → { success, scenario_id }
   *
   * Quan trọng: tổng 4 weight = 1.0
   */
  create: (weight, created_by) =>
    post('/api/v1/scenarios/', { weight, created_by }),

  /**
   * PUT /api/v1/scenarios/{id}
   * body: { weight: { w_residential, w_industrial, w_commercial, w_services } }
   * → { success, updated, scenario_id }
   */
  update: (id, weight) =>
    put(`/api/v1/scenarios/${id}`, { weight }),

  /**
   * DELETE /api/v1/scenarios/{id}
   * → { success, deleted, scenario_id }
   */
  delete: (id) => del(`/api/v1/scenarios/${id}`),

  /**
   * POST /api/v1/scenarios/{id}/apply
   * → { success, applied, scenario_id, weights }
   * Load weights vào session hiện tại của backend
   */
  apply: (id) => post(`/api/v1/scenarios/${id}/apply`)
}

// ─────────────────────────────────────────────
// GROUP 4 — AI MONITOR
// ─────────────────────────────────────────────
export const models = {
  /**
   * GET /api/v1/models/
   * → [ { id, max_depth, min_child_weight, mae, mape, rmse, r2,
   *        model_path, is_best, is_active, created_at } ]
   */
  getAll: () => get('/api/v1/models/'),

  /**
   * GET /api/v1/models/active
   * → model object (cùng shape như trên)
   */
  getActive: () => get('/api/v1/models/active'),

  /**
   * GET /api/v1/models/{id}/metrics
   * → { mae, mape, rmse, r2 }
   */
  getMetrics: (id) => get(`/api/v1/models/${id}/metrics`),

  /**
   * GET /api/v1/models/{id}/acceptance-graph
   * → [ { week, predicted, actual, error } ]
   */
  getAcceptanceGraph: (id) => get(`/api/v1/models/${id}/acceptance-graph`),

  /**
   * POST /api/v1/models/{id}/set-active
   * → { success, active_model_id }
   */
  setActive: (id) => post(`/api/v1/models/${id}/set-active`),

  /**
   * GET /api/v1/models/compare?ids=1,2,3
   * → [ { id, mae, mape, rmse, r2 } ]
   */
  compare: (ids = []) => get(`/api/v1/models/compare?ids=${ids.join(',')}`),

  /**
   * POST /api/v1/models/   (multipart/form-data)
   * Upload model XGBoost mới (file .json)
   * fields: max_depth, min_child_weight, mae, mape, rmse, r2,
   *         is_best, is_active, model_file
   * → { success, model_id, file }
   *
   * Ví dụ upload:
   *   const fd = new FormData()
   *   fd.append('model_file', file)
   *   fd.append('mae', 120.5)
   *   ... (các field còn lại)
   *   fetch('/api/v1/models/', { method: 'POST', body: fd,
   *     headers: { Authorization: `Bearer ${token}` } })
   */
  upload: (formData) => {
    // formData là FormData object chứa đủ các field
    return request('POST', '/api/v1/models/', formData, true)
  }
}

// ─────────────────────────────────────────────
// GROUP 5 — DATA MANAGEMENT
// ─────────────────────────────────────────────
export const data = {
  /**
   * POST /api/v1/data/upload-energy
   * file CSV với cols: week, start_date, end_date,
   *                    Pmax (MW), Pmin (MW), total_load (kWh)
   * → { success, processed, rowcount }
   */
  uploadEnergy: (file) =>
    upload('/api/v1/data/upload-energy', file),

  /**
   * POST /api/v1/data/upload-ward-stats
   * file CSV field name: file
   * → { success, processed, rowcount }
   */
  uploadWardStats: (file) =>
    upload('/api/v1/data/upload-ward-stats', file),

  /**
   * GET /api/v1/data/status
   * → { energy_rows, ward_rows, status }
   */
  getStatus: () => get('/api/v1/data/status'),

  /**
   * GET /api/v1/geojson/wards
   * → GeoJSON FeatureCollection (168 phường TPHCM)
   */
  getWardsGeoJSON: () => get('/api/v1/geojson/wards')
}

// ─────────────────────────────────────────────
// EXPORT — gộp tất cả
// ─────────────────────────────────────────────
export const api = {
  auth,
  simulation,
  scenarios,
  models,
  data,
  createLiveSocket,
  // Thêm các hàm này vào để code cũ không bị lỗi:
  get,
  post,
  put,
  del,
  upload 
}

export default api;
