import { useEffect, useMemo, useState } from 'react'
import WeightSliders from '../components/controls/WeightSliders'
import HeatMap from '../components/map/HeatMap'
import LiveLoadChart from '../components/charts/LiveLoadChart'
import { useMapStore } from '../store/mapStore'
import { useLiveStore } from '../store/liveStore'
import { useAllocation } from '../hooks/useAllocation'
import { simulationService } from '../services/simulationService'
import { modelService } from '../services/modelService'
import { getPriorityLevel } from '../utils/riskLevels'
import { useAuthStore } from '../store/authStore'
import { canMutate } from '../utils/roles'
import { normalizeWard } from '../utils/allocationFlow'

function formatEnergy(kwh) {
  if (kwh == null || Number.isNaN(Number(kwh))) return '--'
  const value = Number(kwh)
  if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(2)} TWh`
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(2)} GWh`
  return `${(value / 1e3).toFixed(0)} MWh`
}

function formatMwh(kwh) {
  if (kwh == null || Number.isNaN(Number(kwh))) return '--'
  return `${(Number(kwh) / 1e3).toLocaleString(undefined, { maximumFractionDigits: 1 })} MWh`
}

function formatKwh(kwh) {
  if (kwh == null || Number.isNaN(Number(kwh))) return 'N/A'
  return Number(kwh).toLocaleString(undefined, { maximumFractionDigits: 3 })
}

function formatKwhWithUnit(kwh) {
  if (kwh == null || Number.isNaN(Number(kwh))) return 'N/A'
  return `${formatKwh(kwh)} kWh`
}

function formatMwhForDetail(kwh) {
  if (kwh == null || Number.isNaN(Number(kwh))) return 'N/A'
  return formatMwh(kwh)
}

function formatScore(value) {
  if (value == null || Number.isNaN(Number(value))) return '--'
  return Number(value).toFixed(4)
}

function formatDetailScore(value) {
  if (value == null || Number.isNaN(Number(value))) return 'N/A'
  return Number(value).toFixed(4)
}

function factorValue(value) {
  if (value == null) return 'N/A'
  return value ? 'Yes' : 'No'
}

function PriorityBadge({ level }) {
  const value = getPriorityLevel(level)
  const colors = {
    HIGH: { background: '#dc2626', color: '#fff' },
    MEDIUM: { background: '#f59e0b', color: '#111827' },
    LOW: { background: '#16a34a', color: '#fff' },
  }

  return (
    <span style={{
      ...colors[value],
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      minWidth: 72,
      padding: '4px 9px',
      borderRadius: 6,
      fontSize: 13,
      fontWeight: 800,
      lineHeight: 1,
    }}>
      {value}
    </span>
  )
}

function StatCard({ label, value, unit, sub }) {
  return (
    <div style={{
      background: 'var(--bg-raised)',
      border: '1px solid var(--border-normal)',
      borderRadius: 8,
      padding: 16,
      minHeight: 92,
    }}>
      <div style={{ fontSize: 14, color: '#cbd5e1', fontWeight: 700, marginBottom: 8 }}>
        {label}
      </div>
      <div style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 8,
        fontFamily: 'var(--font-display)',
      }}>
        <span style={{ fontSize: 28, fontWeight: 900, color: 'var(--text-accent)' }}>{value}</span>
        {unit && <span style={{ fontSize: 15, color: '#cbd5e1', fontWeight: 700 }}>{unit}</span>}
      </div>
      {sub && <div style={{ fontSize: 13, color: '#cbd5e1', marginTop: 6, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{sub}</div>}
    </div>
  )
}

function StressFactors({ factors = {} }) {
  const labels = {
    high_load: 'High load',
    rapid_growth: 'Rapid growth',
    sector_shift: 'Sector shift',
    spatial_cluster: 'Spatial cluster',
  }

  return (
    <div style={{ display: 'grid', gap: 7, marginTop: 8 }}>
      {Object.entries(labels).map(([key, label]) => (
        <div key={key} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 13 }}>
          <span style={{ color: '#cbd5e1' }}>{label}</span>
          <span style={{
            color: factors?.[key] == null ? '#94a3b8' : factors[key] ? '#bbf7d0' : '#94a3b8',
            fontWeight: 800,
          }}>
            {factorValue(factors?.[key])}
          </span>
        </div>
      ))}
    </div>
  )
}

function ExplainabilityRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 13 }}>
      <span style={{ color: '#cbd5e1' }}>{label}</span>
      <span style={{ color: '#f8fafc', fontWeight: 800, textAlign: 'right' }}>{value ?? 'N/A'}</span>
    </div>
  )
}

function GridStressItem({ ward, index }) {
  const [expanded, setExpanded] = useState(false)
  const level = getPriorityLevel(ward)

  return (
    <button
      type="button"
      onClick={() => setExpanded(v => !v)}
      style={{
        width: '100%',
        textAlign: 'left',
        background: expanded ? 'rgba(96,165,250,0.12)' : 'var(--bg-raised)',
        border: '1px solid var(--border-normal)',
        borderRadius: 8,
        padding: 12,
        color: 'var(--text-primary)',
        cursor: 'pointer',
      }}
    >
      <div style={{ display: 'grid', gridTemplateColumns: '34px 1fr auto', gap: 10, alignItems: 'start' }}>
        <div style={{
          width: 30,
          height: 30,
          borderRadius: 6,
          background: 'rgba(96,165,250,0.16)',
          color: '#bfdbfe',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 15,
          fontWeight: 800,
        }}>
          {index + 1}
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 16, fontWeight: 800, color: '#f8fafc', lineHeight: 1.25 }}>
            {ward.ward_name ?? ward.name ?? ward.ward_code}
          </div>
          <div style={{ fontSize: 14, color: '#cbd5e1', marginTop: 4 }}>
            {formatMwh(ward.allocated_kwh)}
            <span style={{ marginLeft: 10 }}>Score {formatScore(ward.final_score_ranked ?? ward.final_score_raw)}</span>
          </div>
          {ward.primary_reason && (
            <div style={{
              fontSize: 13,
              color: '#cbd5e1',
              marginTop: 6,
              lineHeight: 1.35,
              display: expanded ? 'block' : '-webkit-box',
              WebkitLineClamp: expanded ? undefined : 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}>
              {ward.primary_reason}
            </div>
          )}
        </div>
        <PriorityBadge level={level} />
      </div>

      {expanded && (
        <div style={{
          marginTop: 12,
          paddingTop: 12,
          borderTop: '1px solid var(--border-dim)',
        }}>
          <div style={{ display: 'grid', gap: 12 }}>
            <div style={{ display: 'grid', gap: 7 }}>
              <ExplainabilityRow label="Ward Code" value={ward.ward_code ?? ward.ward_id ?? ward.code ?? ward.id ?? 'N/A'} />
              <ExplainabilityRow label="Ward Name" value={ward.ward_name ?? ward.name ?? 'N/A'} />
              <ExplainabilityRow label="Priority Level" value={level} />
              <ExplainabilityRow label="Allocated Load (kWh)" value={formatKwhWithUnit(ward.allocated_kwh)} />
              <ExplainabilityRow label="Allocated Load (MWh)" value={formatMwhForDetail(ward.allocated_kwh)} />
            </div>

            <div style={{ display: 'grid', gap: 7 }}>
              <ExplainabilityRow label="Rank Score" value={formatDetailScore(ward.rank_score)} />
              <ExplainabilityRow label="Absolute Score" value={formatDetailScore(ward.absolute_score)} />
              <ExplainabilityRow label="Acceleration Score" value={formatDetailScore(ward.acceleration_score)} />
              <ExplainabilityRow label="Final Score Raw" value={formatDetailScore(ward.final_score_raw)} />
              <ExplainabilityRow label="Final Score Ranked" value={formatDetailScore(ward.final_score_ranked)} />
            </div>

            <div>
              <div style={{ color: '#bfdbfe', fontSize: 13, fontWeight: 900, marginBottom: 6 }}>
                Stress Factors
              </div>
              <StressFactors factors={ward.stress_factors} />
            </div>

            <div>
              <div style={{ color: '#bfdbfe', fontSize: 13, fontWeight: 900, marginBottom: 6 }}>
                Primary Reason
              </div>
              <div style={{ color: '#dbeafe', fontSize: 13, lineHeight: 1.4 }}>
                {ward.primary_reason ?? 'No reason provided.'}
              </div>
            </div>
          </div>
        </div>
      )}
    </button>
  )
}

export default function DashboardPage() {
  const {
    topRisks,
    totalLoad,
    weights,
    selectedYear,
    allocationMessage,
    wardData,
    gridStressMeta,
    setSelectedYear,
    setTotalLoad,
    setPredictionReady,
    setAllocationMessage,
    setWardData,
    setTopRisks,
    setGridStressMeta,
  } = useMapStore()
  const { isDemoMode, setDemoMode, livePoints } = useLiveStore()
  const latestLive = livePoints?.[livePoints.length - 1]
  const { runAllocation } = useAllocation()
  const { user } = useAuthStore()
  const showMutateControls = canMutate(user)
  const [predictionLoading, setPredictionLoading] = useState(false)

  const highCount = useMemo(() => wardData.filter(w => getPriorityLevel(w) === 'HIGH').length, [wardData])
  const mediumCount = useMemo(() => wardData.filter(w => getPriorityLevel(w) === 'MEDIUM').length, [wardData])
  const dashboardLoad = gridStressMeta?.total_load ?? totalLoad
  const dashboardTemp = gridStressMeta?.avg_temp ?? latestLive?.simulated_temp

  console.log('[DASHBOARD]', {
    forecast: dashboardLoad,
    topRisks: topRisks?.length,
    allocations: wardData?.length,
  })

  useEffect(() => {
    let cancelled = false

    async function loadDashboardData() {
      try {
        const currentLoad = await simulationService.getCurrentLoad()
        if (!cancelled) setTotalLoad(currentLoad?.predicted_load)
      } catch (error) {
        if (error?.status === 404) {
          if (!cancelled) {
            setAllocationMessage(
              showMutateControls
                ? 'No prediction record is available yet. Please start prediction as admin/dev.'
                : 'No prediction record is available yet.'
            )
          }
        }
      }

      try {
        const gridStress = await simulationService.gridStressPriorities({
          year: selectedYear,
          limit: 168,
        })
        if (cancelled) return

        const payload = gridStress?.data ?? gridStress
        const rows = Array.isArray(payload)
          ? payload
          : payload?.results ?? []
        const wards = rows.map(normalizeWard)

        setGridStressMeta({
          total_load: payload?.total_load,
          avg_temp: payload?.avg_temp,
          method: payload?.method,
          week: payload?.week,
          start_date: payload?.start_date,
          end_date: payload?.end_date,
          count: payload?.count,
        })
        if (payload?.total_load != null) setTotalLoad(payload.total_load)
        setWardData(wards)
        setTopRisks(wards.slice(0, 10))
      } catch (error) {
        if (!cancelled) {
          setAllocationMessage(
            showMutateControls
              ? 'No grid stress data is available yet. Generate allocation to load priorities.'
              : 'No grid stress data is available yet.'
          )
        }
      }
    }

    loadDashboardData()
    return () => {
      cancelled = true
    }
  }, [
    selectedYear,
    setTotalLoad,
    setAllocationMessage,
    setWardData,
    setTopRisks,
    setGridStressMeta,
    showMutateControls,
  ])

  function handleYearChange(value) {
    const year = Number(value)
    if (!Number.isFinite(year)) return
    setSelectedYear(year)
    setAllocationMessage('Year changed. Click Generate Allocation to calculate grid stress for the selected year.')
  }

  async function restartPrediction() {
    if (!showMutateControls) return
    setPredictionLoading(true)
    setAllocationMessage('')
    try {
      await modelService.restartPrediction()
      setPredictionReady(true)
      const currentLoad = await simulationService.getCurrentLoad().catch(() => null)
      if (currentLoad?.predicted_load) setTotalLoad(currentLoad.predicted_load)
    } catch (e) {
      setAllocationMessage(e.message || 'Refresh Prediction failed.')
    } finally {
      setPredictionLoading(false)
    }
  }

  async function toggleDemo() {
    try {
      const next = !isDemoMode
      await simulationService.toggleDemo(next, next ? 5 : 1800)
      setDemoMode(next)
    } catch (e) {
      alert(e.message)
    }
  }

  return (
    <div style={{
      height: '100%',
      overflow: 'auto',
      background: 'var(--bg-base)',
      color: 'var(--text-primary)',
    }}>
      <div style={{ padding: 14 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12, marginBottom: 14 }}>
          <StatCard label="Weekly Forecast Load" value={formatEnergy(dashboardLoad).replace(/\s(TWh|GWh|MWh)$/, '')} unit={(formatEnergy(dashboardLoad).split(' ')[1] ?? '')} sub={gridStressMeta?.start_date && gridStressMeta?.end_date ? `${gridStressMeta.start_date} to ${gridStressMeta.end_date}` : undefined} />
          <StatCard label="Average Temperature" value={dashboardTemp != null ? Number(dashboardTemp).toFixed(1) : '--'} unit="°C" sub={gridStressMeta?.method ? `Method: ${gridStressMeta.method}` : 'Weather signal from backend'} />
          <StatCard label="High Priority Wards" value={highCount} unit="wards" />
          <StatCard label="Medium Priority Wards" value={mediumCount} unit="wards" />
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(280px, 310px) minmax(360px, 1fr) minmax(360px, 400px)',
          gap: 14,
          alignItems: 'stretch',
          maxWidth: '100%',
        }}>
          <aside style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-normal)',
            borderRadius: 8,
            padding: 14,
            display: 'flex',
            flexDirection: 'column',
            gap: 14,
          }}>
            <div>
              <label className="label" htmlFor="allocation-year" style={{ fontSize: 15, color: '#cbd5e1', fontWeight: 700 }}>
                DATA YEAR
              </label>
              <input
                id="allocation-year"
                className="input"
                type="number"
                min="2000"
                max="2100"
                value={selectedYear}
                onChange={e => handleYearChange(e.target.value)}
                style={{ fontSize: 15, height: 44 }}
              />
            </div>

            <WeightSliders />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {showMutateControls && (
                <button className="btn" style={{ fontSize: 14, fontWeight: 800, minHeight: 42 }} onClick={restartPrediction} disabled={predictionLoading}>
                  {predictionLoading ? 'REFRESHING...' : 'REFRESH PREDICTION'}
                </button>
              )}
              {showMutateControls ? (
                <button className="btn btn-primary" style={{ fontSize: 15, fontWeight: 900, minHeight: 46 }} onClick={() => runAllocation(weights, selectedYear)} disabled={predictionLoading}>
                  GENERATE ALLOCATION
                </button>
              ) : (
                <div style={{
                  padding: 12,
                  border: '1px solid var(--border-normal)',
                  borderRadius: 8,
                  background: 'var(--bg-overlay)',
                  color: '#cbd5e1',
                  fontSize: 14,
                  lineHeight: 1.45,
                }}>
                  Read-only access. Allocation can be generated by admin or dev users.
                </div>
              )}
              {showMutateControls && (
                <button className={`btn ${isDemoMode ? 'btn-danger' : ''}`} style={{ fontSize: 14, fontWeight: 800, minHeight: 42 }} onClick={toggleDemo}>
                  {isDemoMode ? 'STOP DEMO' : 'DEMO MODE'}
                </button>
              )}
            </div>

            {allocationMessage && (
              <div style={{
                padding: 12,
                border: '1px solid var(--border-normal)',
                borderRadius: 8,
                background: 'var(--bg-overlay)',
                color: '#cbd5e1',
                fontSize: 14,
                lineHeight: 1.45,
              }}>
                {allocationMessage}
              </div>
            )}
          </aside>

          <section style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-normal)',
            borderRadius: 8,
            overflow: 'hidden',
            minHeight: 'calc(100vh - 260px)',
            position: 'relative',
          }}>
            <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-dim)' }}>
              <div style={{ fontSize: 16, color: '#f8fafc', fontWeight: 800 }}>Allocation Heat Map</div>
              <div style={{ fontSize: 14, color: '#cbd5e1', marginTop: 4 }}>Priority coloring from latest allocation result</div>
            </div>
            <div style={{ position: 'absolute', inset: '64px 0 0 0' }}>
              <HeatMap allocations={wardData} />
            </div>
          </section>

          <section style={{ display: 'flex', flexDirection: 'column', gap: 14, minHeight: 'calc(100vh - 260px)', minWidth: 0 }}>
            <LiveLoadChart />

            <div style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-normal)',
              borderRadius: 8,
              padding: 16,
              flex: 1,
              minHeight: 0,
              overflow: 'hidden',
            }}>
              <div style={{ fontSize: 16, color: '#f8fafc', fontWeight: 900, marginBottom: 12 }}>
                GRID STRESS PRIORITIES
              </div>
              {topRisks.length === 0 ? (
                <div style={{ color: '#cbd5e1', fontSize: 14 }}>No grid stress data. Generate allocation to load priorities.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 360, overflowY: 'auto', paddingRight: 4 }}>
                  {topRisks.map((ward, i) => (
                    <GridStressItem key={ward.ward_code ?? i} ward={ward} index={i} />
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
