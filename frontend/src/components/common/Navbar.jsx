import { useLiveStore } from '../../store/liveStore'
import { useMapStore } from '../../store/mapStore'

export default function Navbar() {
  const { isConnected, isDemoMode, livePoints } = useLiveStore()
  const { totalLoad, gridStressMeta } = useMapStore()
  const latest = (livePoints ?? [])[( livePoints ?? []).length - 1]
  const load = gridStressMeta?.total_load ?? totalLoad ?? latest?.predicted_load
  const temp = gridStressMeta?.avg_temp ?? latest?.simulated_temp
  const week = gridStressMeta?.week ?? latest?.week

  return (
    <header style={{
      height: 62,
      background: 'var(--bg-surface)',
      borderBottom: '1px solid var(--border-dim)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 20px',
      gap: 18,
      flexShrink: 0,
    }}>
      <div>
        <div style={{
          fontFamily: 'var(--font-display)',
          fontSize: 20,
          lineHeight: 1,
          fontWeight: 900,
          color: 'var(--text-accent)',
        }}>
          EVN-DSS
        </div>
        <div style={{ fontSize: 13, color: '#cbd5e1', fontWeight: 700, marginTop: 3 }}>
          HCM Energy Grid
        </div>
      </div>

      {isDemoMode && (
        <span className="badge badge-crit demo-pulse" style={{ marginRight: 4 }}>
          ● DEMO
        </span>
      )}

      <div style={{ flex: 1 }} />

      <div style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
        <Stat label="Temp" value={temp != null ? `${Number(temp).toFixed(1)}°C` : '--'} />
        <Stat label="Forecast Load" value={load ? formatLoad(load) : '--'} accent />
        <Stat label="Week" value={week ?? '--'} />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{
          width: 9, height: 9, borderRadius: '50%',
          background: isConnected ? 'var(--risk-low)' : 'var(--risk-crit)',
          boxShadow: isConnected ? '0 0 6px var(--risk-low)' : 'none',
        }} />
        <span style={{
          fontSize: 13,
          color: isConnected ? '#86efac' : '#fca5a5',
          fontWeight: 800,
        }}>
          {isConnected ? 'LIVE' : 'OFFLINE'}
        </span>
      </div>
    </header>
  )
}

function Stat({ label, value, accent }) {
  return (
    <div style={{ textAlign: 'right' }}>
      <div style={{ fontSize: 12, color: '#cbd5e1', fontWeight: 700 }}>{label}</div>
      <div style={{
        fontSize: 15,
        fontWeight: 900,
        color: accent ? 'var(--text-accent)' : 'var(--text-primary)',
      }}>{value}</div>
    </div>
  )
}

function formatLoad(kwh) {
  if (kwh >= 1e9) return `${(kwh / 1e9).toFixed(2)} TWh`
  if (kwh >= 1e6) return `${(kwh / 1e6).toFixed(1)} GWh`
  return `${(kwh / 1e3).toFixed(0)} MWh`
}
