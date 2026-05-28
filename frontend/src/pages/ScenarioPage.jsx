import { useState, useEffect } from 'react'
import { scenarioService } from '../services/scenarioService'
import { useMapStore } from '../store/mapStore'
import { useAuthStore } from '../store/authStore'
import { useAllocation } from '../hooks/useAllocation'
import {
  DEFAULT_ALLOCATION_WEIGHTS,
  fromScenarioApiWeights,
  normalizeDashboardWeights,
  toScenarioApiWeights,
} from '../utils/allocationFlow'
import { canMutate, isDev } from '../utils/roles'

const DEFAULT_FORM = DEFAULT_ALLOCATION_WEIGHTS

const WEIGHT_FIELDS = [
  { key: 'residential', label: 'RESIDENTIAL', color: '#3b82f6' },
  { key: 'industrial',  label: 'INDUSTRIAL',  color: '#f97316' },
  { key: 'commercial',  label: 'COMMERCIAL',  color: '#22c55e' },
  { key: 'services',    label: 'SERVICES',    color: '#a78bfa' },
]

function parseScenarioWeight(scenario) {
  try {
    return typeof scenario.weight === 'string'
      ? JSON.parse(scenario.weight)
      : scenario.weight
  } catch {
    return {}
  }
}

function toBackendWeight(form) {
  return toScenarioApiWeights(form)
}

function toPercentWeight(weight) {
  const looksLikePercent = Object.values(weight ?? {}).some(value => Number(value) > 1)
  if (looksLikePercent) return normalizeDashboardWeights(weight)

  return fromScenarioApiWeights(weight)
}

export default function ScenarioPage() {
  const [scenarios, setScenarios] = useState([])
  const [form, setForm] = useState(DEFAULT_FORM)
  const [editing, setEditing] = useState(null)
  const [loading, setLoading] = useState(false)
  const { weights, selectedYear, setWeights } = useMapStore()
  const { user } = useAuthStore()
  const { runAllocation } = useAllocation()
  const showMutateControls = canMutate(user)
  const showDeleteControls = isDev(user)

  useEffect(() => { load() }, [])

  async function load() {
    try {
      setScenarios(await scenarioService.list())
    } catch {}
  }

  function normalizeForm(nextForm) {
    const total = Object.values(nextForm).reduce((sum, value) => sum + value, 0)
    return { nextForm, total }
  }

  function fillFromCurrent() {
    setForm(normalizeDashboardWeights(weights))
  }

  async function handleSave() {
    if (!showMutateControls) return
    const { total } = normalizeForm(form)
    if (total !== 100) {
      alert(`Total weights must be 100%, got ${total}%`)
      return
    }

    setLoading(true)
    try {
      const currentUserId = user?.user_id ?? user?.id
      if (!currentUserId) {
        throw new Error('Missing current user_id. Please log in again before saving scenarios.')
      }
      const payload = { weight: toBackendWeight(form), created_by: currentUserId }
      if (editing) {
        await scenarioService.update(editing, { weight: payload.weight })
      } else {
        await scenarioService.create(payload)
      }
      setForm(DEFAULT_FORM)
      setEditing(null)
      await load()
    } catch (e) {
      alert(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleApply(scenario) {
    if (!showMutateControls) return
    const weight = parseScenarioWeight(scenario)
    const percentWeight = toPercentWeight(weight)

    await scenarioService.apply(scenario.id)
    setWeights(percentWeight)
    await runAllocation(percentWeight, selectedYear)
    alert(`Scenario #${scenario.id} applied to dashboard.`)
  }

  async function handleDelete(id) {
    if (!showDeleteControls) return
    if (!confirm('Delete this scenario?')) return
    await scenarioService.delete(id)
    await load()
  }

  function startEdit(scenario) {
    if (!showMutateControls) return
    setEditing(scenario.id)
    setForm(toPercentWeight(parseScenarioWeight(scenario)))
  }

  const formTotal = Object.values(form).reduce((sum, value) => sum + value, 0)

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      <div style={{
        flex: 1, overflowY: 'auto', padding: 20,
        borderRight: '1px solid var(--border-dim)',
      }}>
        <div style={{
          fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 700,
          letterSpacing: '0.06em', marginBottom: 16,
        }}>
          SCENARIOS
        </div>

        {scenarios.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>No scenarios saved yet.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {scenarios.map(scenario => {
              const weight = toPercentWeight(parseScenarioWeight(scenario))

              return (
                <div key={scenario.id} className="card-raised fade-up">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
                        Scenario #{scenario.id}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                        Created by user #{scenario.created_by}
                      </div>
                    </div>
                    <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>
                      {scenario.created_at ? new Date(scenario.created_at).toLocaleDateString('vi-VN') : '--'}
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', marginBottom: 10 }}>
                    {WEIGHT_FIELDS.map(({ key, label, color }) => {
                      const val = weight[key] ?? 0
                      return (
                        <div key={key}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 2 }}>
                            <span style={{ color: 'var(--text-dim)' }}>{label}</span>
                            <span style={{ color }}>{val}%</span>
                          </div>
                          <div style={{ height: 2, background: 'var(--border-dim)', borderRadius: 1 }}>
                            <div style={{ height: 2, width: `${val}%`, background: color, borderRadius: 1 }} />
                          </div>
                        </div>
                      )
                    })}
                  </div>

	                  {showMutateControls && (
	                    <div style={{ display: 'flex', gap: 8 }}>
	                      <button className="btn btn-primary" style={{ fontSize: 11 }} onClick={() => handleApply(scenario)}>
	                        APPLY
	                      </button>
	                      <button className="btn" style={{ fontSize: 11 }} onClick={() => startEdit(scenario)}>
	                        EDIT
	                      </button>
	                      {showDeleteControls && (
	                        <button className="btn btn-danger" style={{ fontSize: 11 }} onClick={() => handleDelete(scenario.id)}>
	                          DELETE
	                        </button>
	                      )}
	                    </div>
	                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {showMutateControls && (
      <div style={{ width: 320, padding: 20, overflowY: 'auto', flexShrink: 0 }}>
        <div style={{
          fontFamily: 'var(--font-display)', fontSize: 16, fontWeight: 600,
          letterSpacing: '0.06em', marginBottom: 16,
        }}>
          {editing ? 'EDIT SCENARIO' : 'NEW SCENARIO'}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {WEIGHT_FIELDS.map(s => (
            <div key={s.key}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <label className="label" style={{ margin: 0 }}>{s.label}</label>
                <span style={{ fontSize: 12, color: s.color }}>{form[s.key]}%</span>
              </div>
              <input type="range" className="input" style={{ padding: 0, height: 20 }}
                min={0} max={100} value={form[s.key]}
                onChange={e => setForm(p => ({ ...p, [s.key]: parseInt(e.target.value) }))}
              />
            </div>
          ))}
          <div style={{
            fontSize: 11,
            color: formTotal === 100 ? 'var(--risk-low)' : 'var(--risk-crit)',
            letterSpacing: '0.08em',
          }}>
            TOTAL: {formTotal}%
          </div>
          <div className="divider" />
          <button className="btn" style={{ fontSize: 11 }} onClick={fillFromCurrent}>
            FILL FROM CURRENT DASHBOARD
          </button>
          <button className="btn btn-primary" onClick={handleSave} disabled={loading || formTotal !== 100}>
            {loading ? 'SAVING...' : editing ? 'UPDATE' : 'SAVE SCENARIO'}
          </button>
          {editing && (
            <button className="btn" onClick={() => { setEditing(null); setForm(DEFAULT_FORM) }}>
              CANCEL
            </button>
          )}
        </div>
      </div>
      )}
    </div>
  )
}
