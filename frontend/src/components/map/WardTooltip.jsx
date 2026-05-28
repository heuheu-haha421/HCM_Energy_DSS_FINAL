// Rendered inside Leaflet via ReactDOM.createPortal OR used as
// a floating panel when a ward is clicked on the map.
// This version is a standalone React component for the
// "clicked ward details" side panel — separate from the
// lightweight Leaflet HTML tooltip already in HeatMap.jsx.

import { RISK_META, getPriorityLevel } from '../../utils/riskLevels'

/**
 * Props:
 *   ward     – allocation/grid stress result
 *   onClose  – callback
 *   position – 'right' | 'left' (default 'right', panel slides from that side)
 */

function RiskBar({ value, max, color }) {
    return (
      <div style={{
        height: 4, background: 'var(--border-dim)',
        borderRadius: 2, overflow: 'hidden',
      }}>
        <div style={{
          height: '100%', borderRadius: 2,
          width: `${Math.min(100, (value / max) * 100)}%`,
          background: color,
          transition: 'width 0.4s ease',
        }} />
      </div>
    )
  }
  
  function InfoRow({ label, value, sub, accent }) {
    return (
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'flex-end',
        padding: '6px 0',
        borderBottom: '1px solid var(--border-dim)',
      }}>
        <span style={{
          fontSize: 10, color: 'var(--text-dim)',
          letterSpacing: '0.08em',
        }}>
          {label}
        </span>
        <div style={{ textAlign: 'right' }}>
          <span style={{
            fontSize: 13, fontWeight: 500,
            color: accent ? 'var(--text-accent)' : 'var(--text-primary)',
          }}>
            {value}
          </span>
          {sub && (
            <span style={{
              fontSize: 10, color: 'var(--text-dim)',
              marginLeft: 4,
            }}>
              {sub}
            </span>
          )}
        </div>
      </div>
    )
  }
  
  export default function WardTooltip({ ward, onClose, position = 'right' }) {
    if (!ward) return null
  
    const level = getPriorityLevel(ward)
    const risk = RISK_META[level]
    const factors = ward.stress_factors ?? {}
  
    return (
      <div
        className="fade-up"
        style={{
          position:   'absolute',
          top:        12,
          [position]: 12,
          zIndex:     2000,
          width:      280,
          background: 'var(--bg-overlay)',
          border:     '1px solid var(--border-normal)',
          borderRadius: 10,
          overflow:   'hidden',
          boxShadow:  '0 8px 32px rgba(0,0,0,0.5)',
          fontFamily: 'var(--font-mono)',
        }}
      >
        {/* Header bar — risk color */}
        <div style={{
          background: risk.color,
          padding: '8px 14px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <span style={{
            fontSize: 10, fontWeight: 600,
            color: '#000', letterSpacing: '0.12em',
            opacity: 0.8,
          }}>
            {level} PRIORITY
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none',
              color: '#000', opacity: 0.6,
              cursor: 'pointer', fontSize: 16,
              lineHeight: 1, padding: 0,
            }}
          >
            ×
          </button>
        </div>
  
        {/* Body */}
        <div style={{ padding: '12px 14px 14px' }}>
          {/* Ward name */}
          <div style={{ marginBottom: 12 }}>
            <div style={{
              fontFamily: 'var(--font-display)',
              fontSize: 16, fontWeight: 700,
              color: 'var(--text-primary)',
              marginBottom: 2,
            }}>
              {ward.name ?? ward.ward_name ?? ward.ward_code}
            </div>
            <div style={{
              fontSize: 10, color: 'var(--text-dim)',
              letterSpacing: '0.08em',
            }}>
              {ward.district}
            </div>
          </div>
  
          {/* Load highlight */}
          <div style={{
            background: 'var(--bg-raised)',
            borderRadius: 6, padding: '10px 12px',
            marginBottom: 12,
            border: `1px solid ${risk.color}33`,
          }}>
            <div style={{
              fontSize: 10, color: 'var(--text-dim)',
              letterSpacing: '0.1em', marginBottom: 4,
            }}>
              ALLOCATED LOAD
            </div>
            <div style={{
              display: 'flex', alignItems: 'baseline', gap: 6,
            }}>
              <span style={{
                fontFamily: 'var(--font-display)',
                fontSize: 26, fontWeight: 700,
                color: risk.color,
              }}>
                {ward.allocated_mwh?.toFixed(1) ?? '—'}
              </span>
              <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>MWh</span>
              <span style={{
                marginLeft: 'auto',
                fontSize: 12, color: 'var(--text-secondary)',
              }}>
                {ward.allocation_pct?.toFixed(3)}% of city
              </span>
            </div>
            <RiskBar
              value={ward.allocated_mwh ?? 0}
              max={250}
              color={risk.color}
            />
          </div>
  
          <InfoRow
            label="PROXY INDEX"
            value={ward.final_score_raw?.toFixed?.(3) ?? ward.proxy_index?.toFixed?.(6) ?? '—'}
            accent
          />
          <InfoRow
            label="FINAL SCORE"
            value={ward.final_score_ranked?.toFixed?.(3) ?? '—'}
            accent
          />
          <InfoRow
            label="PRIMARY REASON"
            value={ward.primary_reason ?? '—'}
          />
          <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {Object.entries({
              high_load: 'High load',
              rapid_growth: 'Rapid growth',
              sector_shift: 'Sector shift',
              spatial_cluster: 'Spatial cluster',
            }).map(([key, label]) => (
              <span key={key} style={{
                background: factors[key] ? `${risk.color}33` : 'rgba(148,163,184,0.12)',
                border: `1px solid ${factors[key] ? risk.color : 'rgba(148,163,184,0.22)'}`,
                borderRadius: 999,
                padding: '4px 8px',
                color: 'var(--text-primary)',
                fontSize: 11,
                fontWeight: 700,
              }}>
                {label}
              </span>
            ))}
          </div>
        </div>
      </div>
    )
  }
