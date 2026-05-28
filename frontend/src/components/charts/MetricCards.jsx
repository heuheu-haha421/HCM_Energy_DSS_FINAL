/**
 * Props:
 *   metrics – { mae, mape, rmse, r2 }
 *   loading – boolean
 *   compact – boolean (smaller sizing)
 */

function Skeleton() {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 }}>
        {[...Array(4)].map((_, i) => (
          <div key={i} className="card" style={{ height: 76 }}>
            <div className="skeleton" style={{ height: 10, width: '50%', marginBottom: 10, borderRadius: 3 }} />
            <div className="skeleton" style={{ height: 28, width: '80%', borderRadius: 4 }} />
          </div>
        ))}
      </div>
    )
  }
  
  function gradeR2(v)    { return v >= 0.85 ? 'low' : v >= 0.70 ? 'med' : 'crit' }
  function gradeMape(v)  { return v <= 4    ? 'low' : v <= 8    ? 'med' : 'crit' }
  
  const COLOR_MAP = {
    low:  'var(--risk-low)',
    med:  'var(--risk-med)',
    crit: 'var(--risk-crit)',
    neutral: 'var(--text-accent)',
  }
  
  export default function MetricCards({ metrics, loading = false, compact = false }) {
    if (loading) return <Skeleton />
    if (!metrics) return null
  
    const cards = [
      {
        label: 'MAE',
        raw:   metrics.mae,
        value: metrics.mae != null ? metrics.mae.toLocaleString('en-US', { maximumFractionDigits: 0 }) : '—',
        unit:  'kWh',
        grade: 'neutral',
        hint:  'Mean absolute error',
      },
      {
        label: 'MAPE',
        raw:   metrics.mape,
        value: metrics.mape != null ? metrics.mape.toFixed(2) : '—',
        unit:  '%',
        grade: metrics.mape != null ? gradeMape(metrics.mape) : 'neutral',
        hint:  'Mean abs. percentage error',
      },
      {
        label: 'RMSE',
        raw:   metrics.rmse,
        value: metrics.rmse != null ? metrics.rmse.toLocaleString('en-US', { maximumFractionDigits: 0 }) : '—',
        unit:  'kWh',
        grade: 'neutral',
        hint:  'Root mean squared error',
      },
      {
        label: 'R²',
        raw:   metrics.r2,
        value: metrics.r2 != null ? metrics.r2.toFixed(4) : '—',
        unit:  '',
        grade: metrics.r2 != null ? gradeR2(metrics.r2) : 'neutral',
        hint:  'Coefficient of determination',
      },
    ]
  
    return (
      <div style={{
        display: 'grid',
        gridTemplateColumns: compact ? 'repeat(4,1fr)' : 'repeat(4,minmax(0,1fr))',
        gap: compact ? 8 : 10,
      }}>
        {cards.map(c => (
          <div key={c.label} className="card" style={{
            position: 'relative',
            overflow: 'hidden',
            padding: compact ? '10px 12px' : 14,
          }}
            title={c.hint}
          >
            {/* Grade bar on left edge */}
            <div style={{
              position: 'absolute', left: 0, top: 0, bottom: 0, width: 2,
              background: COLOR_MAP[c.grade],
              borderRadius: '8px 0 0 8px',
            }} />
  
            <div style={{
              fontSize: 10, color: 'var(--text-dim)',
              letterSpacing: '0.12em', marginBottom: compact ? 4 : 6,
            }}>
              {c.label}
            </div>
  
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 3 }}>
              <span style={{
                fontFamily: 'var(--font-display)',
                fontSize: compact ? 18 : 22,
                fontWeight: 700,
                color: COLOR_MAP[c.grade],
                lineHeight: 1,
              }}>
                {c.value}
              </span>
              {c.unit && (
                <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>{c.unit}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    )
  }
