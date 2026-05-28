import { useMapStore } from '../../store/mapStore'
import { useAllocation } from '../../hooks/useAllocation'

const SLIDERS = [
  { key: 'residential', label: 'RESIDENTIAL', color: '#3b82f6' },
  { key: 'industrial',  label: 'INDUSTRIAL',  color: '#f97316' },
  { key: 'commercial',  label: 'COMMERCIAL',  color: '#22c55e' },
  { key: 'services',    label: 'SERVICES',    color: '#a78bfa' },
]

export default function WeightSliders() {
  const { weights, setWeights } = useMapStore()
  const { debouncedAllocation } = useAllocation()

  function handleChange(key, raw) {
    const val = Math.min(100, Math.max(0, parseInt(raw) || 0))
    const others = SLIDERS.filter(s => s.key !== key)
    const remaining = 100 - val
    const sumOthers = others.reduce((s, o) => s + weights[o.key], 0)
    const newW = { ...weights, [key]: val }
    if (sumOthers > 0) {
      others.forEach(o => {
        newW[o.key] = Math.round(weights[o.key] / sumOthers * remaining)
      })
    } else {
      const share = Math.floor(remaining / others.length)
      others.forEach(o => { newW[o.key] = share })
    }
    // Fix rounding
    const total = Object.values(newW).reduce((a, b) => a + b, 0)
    if (total !== 100) newW[others[0].key] += 100 - total
    setWeights(newW)
    debouncedAllocation(newW)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ fontSize: 16, color: '#f8fafc', fontWeight: 800, marginBottom: 2 }}>
        ALLOCATION WEIGHTS
      </div>
      {SLIDERS.map(s => (
        <div key={s.key}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 15, color: '#cbd5e1', fontWeight: 700 }}>
              {s.label}
            </span>
            <span style={{ fontSize: 16, fontWeight: 900, color: s.color }}>
              {weights[s.key]}%
            </span>
          </div>
          <div style={{ position: 'relative', height: 28, display: 'flex', alignItems: 'center' }}>
            <div style={{
              position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)',
              width: `${weights[s.key]}%`, height: 8,
              background: s.color, borderRadius: 999,
              transition: 'width 0.2s ease',
              pointerEvents: 'none',
            }} />
            <input
              type="range" min={0} max={100} value={weights[s.key]}
              onChange={e => handleChange(s.key, e.target.value)}
              style={{
                width: '100%', height: 8,
                appearance: 'none', background: 'var(--border-dim)',
                borderRadius: 999, cursor: 'pointer', position: 'relative',
                accentColor: s.color,
              }}
            />
          </div>
        </div>
      ))}
      <div style={{
        fontSize: 15, color: '#cbd5e1',
        borderTop: '1px solid var(--border-dim)',
        paddingTop: 12,
        display: 'flex', justifyContent: 'space-between',
        fontWeight: 800,
      }}>
        <span>TOTAL</span>
        <span style={{
          color: Object.values(weights).reduce((a,b)=>a+b,0) === 100
            ? 'var(--risk-low)' : 'var(--risk-crit)',
          fontSize: 17,
        }}>
          {Object.values(weights).reduce((a,b)=>a+b,0)}%
        </span>
      </div>
    </div>
  )
}
