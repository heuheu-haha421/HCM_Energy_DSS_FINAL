import { useState } from 'react'
import { simulationService } from '../../services/simulationService'
import { useLiveStore } from '../../store/liveStore'

const INTERVALS = [
  { label: '3s',  value: 3  },
  { label: '5s',  value: 5  },
  { label: '10s', value: 10 },
]

/**
 * Props:
 *   showIntervalPicker – boolean (default true)
 *   size – 'sm' | 'md' (default 'md')
 */
export default function DemoToggle({ showIntervalPicker = true, size = 'md' }) {
  const { isDemoMode, setDemoMode } = useLiveStore()
  const [interval, setInterval_]   = useState(5)
  const [loading, setLoading]      = useState(false)

  async function toggle() {
    setLoading(true)
    try {
      const next = !isDemoMode
      await simulationService.toggleDemo(next, next ? interval : 1800)
      setDemoMode(next)
    } catch (e) {
      console.error('Demo toggle failed', e)
    } finally {
      setLoading(false)
    }
  }

  const isSmall = size === 'sm'

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>

      {/* Interval picker */}
      {showIntervalPicker && !isDemoMode && (
        <div style={{ display: 'flex', gap: 4 }}>
          {INTERVALS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setInterval_(opt.value)}
              style={{
                padding: isSmall ? '2px 6px' : '4px 9px',
                fontSize: isSmall ? 10 : 11,
                border: '1px solid',
                borderColor: interval === opt.value ? 'var(--accent)' : 'var(--border-normal)',
                background: interval === opt.value ? 'var(--accent-dim)' : 'var(--bg-overlay)',
                color: interval === opt.value ? 'var(--text-accent)' : 'var(--text-dim)',
                borderRadius: 4,
                cursor: 'pointer',
                fontFamily: 'var(--font-mono)',
                letterSpacing: '0.06em',
                transition: 'all 0.12s',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}

      {/* Toggle button */}
      <button
        onClick={toggle}
        disabled={loading}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: isSmall ? '4px 10px' : '7px 14px',
          fontSize: isSmall ? 10 : 11,
          border: '1px solid',
          borderColor: isDemoMode ? 'var(--risk-crit)' : 'var(--border-normal)',
          background: isDemoMode ? 'var(--risk-crit-bg)' : 'var(--bg-overlay)',
          color: isDemoMode ? 'var(--risk-crit)' : 'var(--text-secondary)',
          borderRadius: 6,
          cursor: loading ? 'not-allowed' : 'pointer',
          fontFamily: 'var(--font-mono)',
          letterSpacing: '0.08em',
          fontWeight: 500,
          opacity: loading ? 0.6 : 1,
          transition: 'all 0.15s',
        }}
      >
        {/* Indicator dot */}
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: isDemoMode ? 'var(--risk-crit)' : 'var(--text-dim)',
          ...(isDemoMode ? { animation: 'demoPulse 1s ease infinite' } : {}),
          flexShrink: 0,
        }} />
        {loading ? 'SWITCHING...' : isDemoMode ? 'STOP DEMO' : 'DEMO MODE'}
      </button>

      {/* Running badge */}
      {isDemoMode && (
        <span style={{
          fontSize: 10, color: 'var(--risk-crit)',
          letterSpacing: '0.08em',
          opacity: 0.8,
        }}>
          {interval}s interval
        </span>
      )}
    </div>
  )
}