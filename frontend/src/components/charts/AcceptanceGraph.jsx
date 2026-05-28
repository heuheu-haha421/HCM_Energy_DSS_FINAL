import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine, Brush
} from 'recharts'

const COLORS = {
  actual:    '#3b82f6',
  predicted: '#f59e0b',
  compare:   '#22c55e',
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-overlay)',
      border: '1px solid var(--border-normal)',
      borderRadius: 6, padding: '10px 14px',
      fontFamily: 'var(--font-mono)', fontSize: 11,
      minWidth: 180,
    }}>
      <div style={{ color: 'var(--text-dim)', marginBottom: 6, letterSpacing: '0.08em' }}>
        WEEK {label}
      </div>
      {payload.map(p => (
        <div key={p.dataKey} style={{
          display: 'flex', justifyContent: 'space-between',
          gap: 16, marginBottom: 3,
          color: p.color,
        }}>
          <span style={{ color: 'var(--text-secondary)' }}>
            {p.name.toUpperCase()}
          </span>
          <span style={{ fontWeight: 500 }}>
            {p.value != null ? (p.value / 1e6).toFixed(3) + ' GWh' : '—'}
          </span>
        </div>
      ))}
      {payload.length >= 2 && payload[0].value && payload[1].value && (
        <>
          <div style={{
            borderTop: '1px solid var(--border-dim)',
            marginTop: 6, paddingTop: 6,
            display: 'flex', justifyContent: 'space-between',
            color: 'var(--text-dim)',
          }}>
            <span>ERROR</span>
            <span style={{
              color: Math.abs(payload[0].value - payload[1].value) / payload[0].value > 0.05
                ? 'var(--risk-crit)' : 'var(--risk-low)'
            }}>
              {(Math.abs(payload[0].value - payload[1].value) / payload[0].value * 100).toFixed(1)}%
            </span>
          </div>
        </>
      )}
    </div>
  )
}

/**
 * Props:
 *   data        – array of { week, actual, predicted, predicted2? }
 *   title       – string
 *   compareLabel– string (optional second predicted line label)
 *   tetWeeks    – array of week strings to shade (optional)
 *   height      – number (default 240)
 *   showBrush   – boolean (default false)
 */
export default function AcceptanceGraph({
  data = [],
  title = 'ACCEPTANCE GRAPH',
  compareLabel = null,
  tetWeeks = [],
  height = 240,
  showBrush = false,
}) {
  const [hiddenLines, setHiddenLines] = useState({})

  function toggleLine(key) {
    setHiddenLines(p => ({ ...p, [key]: !p[key] }))
  }

  if (data.length === 0) {
    return (
      <div style={{
        height, display: 'flex', alignItems: 'center',
        justifyContent: 'center', color: 'var(--text-dim)', fontSize: 11,
        letterSpacing: '0.1em',
      }}>
        NO DATA AVAILABLE
      </div>
    )
  }

  // Calculate MAPE for header
  const valid = data.filter(d => d.actual && d.predicted)
  const mape = valid.length
    ? valid.reduce((s, d) => s + Math.abs(d.actual - d.predicted) / d.actual, 0) / valid.length * 100
    : null

  return (
    <div>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', marginBottom: 12,
      }}>
        <div style={{
          fontSize: 11, color: 'var(--text-secondary)',
          letterSpacing: '0.1em',
        }}>
          {title}
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          {mape != null && (
            <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>
              MAPE&nbsp;
              <span style={{
                color: mape < 5 ? 'var(--risk-low)'
                  : mape < 10 ? 'var(--risk-med)'
                  : 'var(--risk-crit)',
                fontWeight: 600,
              }}>
                {mape.toFixed(2)}%
              </span>
            </div>
          )}
          {/* Legend toggles */}
          {[
            { key: 'actual',    label: 'ACTUAL',    color: COLORS.actual    },
            { key: 'predicted', label: 'PREDICTED', color: COLORS.predicted },
            ...(compareLabel ? [{ key: 'predicted2', label: compareLabel.toUpperCase(), color: COLORS.compare }] : []),
          ].map(l => (
            <button key={l.key} onClick={() => toggleLine(l.key)} style={{
              display: 'flex', alignItems: 'center', gap: 4,
              background: 'none', border: 'none', cursor: 'pointer',
              padding: '2px 6px', borderRadius: 4,
              opacity: hiddenLines[l.key] ? 0.35 : 1,
              transition: 'opacity 0.15s',
            }}>
              <div style={{
                width: 20, height: 2,
                background: hiddenLines[l.key] ? 'var(--text-dim)' : l.color,
                borderRadius: 1,
                ...(l.key !== 'actual' ? {
                  backgroundImage: `repeating-linear-gradient(90deg,${l.color} 0,${l.color} 5px,transparent 5px,transparent 8px)`,
                  background: 'none',
                } : {}),
              }} />
              <span style={{ fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.08em' }}>
                {l.label}
              </span>
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
          <XAxis
            dataKey="week"
            tick={{ fontSize: 9, fill: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}
            tickLine={false} axisLine={{ stroke: 'var(--border-dim)' }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 9, fill: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}
            tickLine={false} axisLine={false}
            tickFormatter={v => (v / 1e9).toFixed(1) + 'T'}
            width={36}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Tet shading */}
          {tetWeeks.map(w => (
            <ReferenceLine key={w} x={w}
              stroke="rgba(239,68,68,0.25)"
              strokeWidth={8}
              label={{ value: 'TET', position: 'top', fontSize: 8, fill: 'var(--risk-crit)', fontFamily: 'var(--font-mono)' }}
            />
          ))}

          <Line
            type="monotone" dataKey="actual" name="actual"
            stroke={hiddenLines.actual ? 'transparent' : COLORS.actual}
            strokeWidth={1.5} dot={false}
            activeDot={{ r: 4, fill: COLORS.actual, strokeWidth: 0 }}
            isAnimationActive={false}
          />
          <Line
            type="monotone" dataKey="predicted" name="predicted"
            stroke={hiddenLines.predicted ? 'transparent' : COLORS.predicted}
            strokeWidth={1.5} strokeDasharray="5 3" dot={false}
            activeDot={{ r: 4, fill: COLORS.predicted, strokeWidth: 0 }}
            isAnimationActive={false}
          />
          {compareLabel && (
            <Line
              type="monotone" dataKey="predicted2" name={compareLabel}
              stroke={hiddenLines.predicted2 ? 'transparent' : COLORS.compare}
              strokeWidth={1.5} strokeDasharray="3 3" dot={false}
              activeDot={{ r: 4, fill: COLORS.compare, strokeWidth: 0 }}
              isAnimationActive={false}
            />
          )}

          {showBrush && (
            <Brush
              dataKey="week" height={18} travellerWidth={4}
              stroke="var(--border-normal)"
              fill="var(--bg-surface)"
              travellerStyle={{ fill: 'var(--accent)' }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
