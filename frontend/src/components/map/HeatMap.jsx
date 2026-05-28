import { useEffect, useRef, useCallback, useState } from 'react'
import { useMapStore } from '../../store/mapStore'
import { dataService } from '../../services/dataService'
import {
  getAllocationRiskStats,
  getRiskFill,
  getRiskLevelForLoad,
  getPriorityLevel,
} from '../../utils/riskLevels'
import { getWardMatchKey, normalizeMatchKey, normalizeWardName } from '../../utils/allocationFlow'

function getFeatureMatchKey(feature) {
  const properties = feature?.properties ?? {}
  return (
    properties.ward_code ??
    properties.ward_id ??
    properties.code ??
    properties.id ??
    properties.name ??
    null
  )
}

function getFeatureCandidateKeys(feature) {
  const properties = feature?.properties ?? {}
  return [
    properties.ward_code,
    properties.code,
    properties.id,
    normalizeWardName(properties.name),
    normalizeWardName(`${properties.type ?? ''} ${properties.name ?? ''}`),
  ].filter(Boolean)
}

function buildWardLookup(wards) {
  const exact = new Map()
  const normalized = new Map()

  wards.forEach((ward) => {
    const candidates = [
      getWardMatchKey(ward),
      ward?.ward_code,
      ward?.ward_id,
      ward?.code,
      ward?.id,
      ward?.name,
      ward?.ward_name,
      normalizeWardName(ward?.ward_name),
      normalizeWardName(ward?.name),
    ]

    candidates.forEach((candidate) => {
      if (candidate == null) return
      const exactKey = String(candidate)
      exact.set(exactKey, ward)
      const normalizedKey = normalizeMatchKey(candidate)
      if (normalizedKey) normalized.set(normalizedKey, ward)
    })
  })

  return { exact, normalized }
}

function findWardMatch(feature, lookup) {
  for (const key of getFeatureCandidateKeys(feature)) {
    const match = lookup.exact.get(String(key)) ?? lookup.normalized.get(normalizeMatchKey(key))
    if (match) return match
  }

  const key = getFeatureMatchKey(feature)
  if (key == null) return null
  return lookup.exact.get(String(key)) ?? lookup.normalized.get(normalizeMatchKey(key)) ?? null
}

function formatKwh(value) {
  if (value == null || Number.isNaN(Number(value))) return 'N/A'
  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: 3,
  })
}

function formatMwh(value) {
  if (value == null || Number.isNaN(Number(value))) return 'N/A'
  return (Number(value) / 1000).toLocaleString(undefined, {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  })
}

function formatScore(value) {
  if (value == null || Number.isNaN(Number(value))) return 'N/A'
  return Number(value).toFixed(4)
}

function withUnit(rawValue, formattedValue, unit) {
  if (rawValue == null || Number.isNaN(Number(rawValue))) return 'N/A'
  return `${formattedValue} ${unit}`
}

function getTooltipPosition(event, width = 360, height = 420) {
  const padding = 16
  const offset = 16
  const viewportWidth = window.innerWidth
  const viewportHeight = window.innerHeight
  let x = event.clientX + offset
  let y = event.clientY + offset

  if (x + width + padding > viewportWidth) {
    x = event.clientX - width - offset
  }

  if (y + height + padding > viewportHeight) {
    y = event.clientY - height - offset
  }

  return {
    x: Math.max(padding, x),
    y: Math.max(padding, y),
  }
}

function getRiskBadgeStyle(level) {
  const colors = {
    HIGH: { background: '#dc2626', color: '#fff' },
    MEDIUM: { background: '#f59e0b', color: '#111827' },
    LOW: { background: '#16a34a', color: '#fff' },
  }

  return colors[level] ?? colors.LOW
}

function DetailRow({ label, value }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, alignItems: 'start' }}>
      <span style={{ color: '#cbd5e1', fontSize: 13 }}>{label}</span>
      <span style={{ color: '#f8fafc', fontSize: 14, fontWeight: 700, textAlign: 'right' }}>{value ?? 'N/A'}</span>
    </div>
  )
}

function FactorRow({ label, value }) {
  const isMissing = value == null
  const isYes = value === true

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, alignItems: 'center' }}>
      <span style={{ color: '#cbd5e1', fontSize: 13 }}>{label}</span>
      <span style={{
        color: isMissing ? '#94a3b8' : isYes ? '#bbf7d0' : '#94a3b8',
        background: isMissing ? 'rgba(148,163,184,0.1)' : isYes ? 'rgba(34,197,94,0.18)' : 'rgba(148,163,184,0.1)',
        border: `1px solid ${isMissing ? 'rgba(148,163,184,0.18)' : isYes ? 'rgba(34,197,94,0.45)' : 'rgba(148,163,184,0.18)'}`,
        borderRadius: 999,
        padding: '2px 8px',
        fontSize: 12,
        fontWeight: 800,
      }}>
        {isMissing ? 'N/A' : isYes ? 'Yes' : 'No'}
      </span>
    </div>
  )
}

function SectionTitle({ children }) {
  return (
    <div style={{
      color: '#bfdbfe',
      fontSize: 13,
      fontWeight: 900,
      marginBottom: 7,
      textTransform: 'uppercase',
    }}>
      {children}
    </div>
  )
}

function WardHoverTooltip({ tooltip }) {
  if (!tooltip) return null

  const { data, position } = tooltip
  const ward = data.ward ?? {}
  const level = getPriorityLevel(ward.priority_level ?? ward.risk_level ?? data.risk ?? 'LOW')
  const factors = ward.stress_factors ?? {}
  const wardName = ward.ward_name ?? ward.name ?? data.name ?? 'N/A'
  const wardCode = ward.ward_code ?? ward.ward_id ?? ward.code ?? ward.id ?? 'N/A'
  const allocatedKwh = ward.allocated_kwh
  const primaryReason = ward.primary_reason ?? 'No reason provided.'
  const hasExplainability = [
    ward.rank_score,
    ward.absolute_score,
    ward.acceleration_score,
    ward.final_score_raw,
    ward.final_score_ranked,
    ward.primary_reason,
    ward.stress_factors,
  ].some(value => value != null)

  return (
    <div style={{
      position: 'fixed',
      left: position.x,
      top: position.y,
      width: 'min(360px, calc(100vw - 32px))',
      maxWidth: 'calc(100vw - 32px)',
      maxHeight: 420,
      overflowY: 'auto',
      background: 'rgba(15, 23, 42, 0.97)',
      border: '1px solid rgba(203, 213, 225, 0.28)',
      borderRadius: 12,
      padding: 14,
      zIndex: 2400,
      pointerEvents: 'none',
      boxShadow: '0 16px 40px rgba(0,0,0,0.42)',
      color: '#e2e8f0',
      opacity: 1,
      transform: 'translateY(0)',
      transition: 'opacity 140ms ease, transform 140ms ease',
      fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10, marginBottom: 10 }}>
        <div style={{
          fontSize: 16,
          lineHeight: 1.25,
          fontWeight: 800,
          color: '#f8fafc',
        }}>
          {wardName}
          <div style={{ color: '#cbd5e1', fontSize: 13, fontWeight: 700, marginTop: 3 }}>
            {wardCode}
          </div>
        </div>
        <span style={{
          ...getRiskBadgeStyle(level),
          borderRadius: 999,
          padding: '4px 9px',
          fontSize: 13,
          lineHeight: 1,
          fontWeight: 800,
          whiteSpace: 'nowrap',
        }}>
          {level}
        </span>
      </div>

      <div style={{
        borderTop: '1px solid rgba(148, 163, 184, 0.18)',
        borderBottom: '1px solid rgba(148, 163, 184, 0.18)',
        padding: '8px 0',
        marginBottom: 10,
        display: 'grid',
        gap: 6,
      }}>
        <SectionTitle>Load</SectionTitle>
        <DetailRow label="Priority Level" value={level} />
        <DetailRow label="Allocated Load (kWh)" value={withUnit(allocatedKwh, formatKwh(allocatedKwh), 'kWh')} />
        <DetailRow label="Allocated Load (MWh)" value={withUnit(allocatedKwh, formatMwh(allocatedKwh), 'MWh')} />
      </div>

      <div style={{ display: 'grid', gap: 10 }}>
        {!hasExplainability && (
          <div style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.35 }}>
            No explainability available
          </div>
        )}

        <div>
          <SectionTitle>Scores</SectionTitle>
          <div style={{ display: 'grid', gap: 6 }}>
            <DetailRow label="Rank Score" value={formatScore(ward.rank_score)} />
            <DetailRow label="Absolute Score" value={formatScore(ward.absolute_score)} />
            <DetailRow label="Acceleration Score" value={formatScore(ward.acceleration_score)} />
            <DetailRow label="Final Score Raw" value={formatScore(ward.final_score_raw)} />
            <DetailRow label="Final Score Ranked" value={formatScore(ward.final_score_ranked)} />
          </div>
        </div>

        <div>
          <SectionTitle>Stress Factors</SectionTitle>
          <div style={{ display: 'grid', gap: 6 }}>
            <FactorRow label="High Load" value={factors.high_load} />
            <FactorRow label="Rapid Growth" value={factors.rapid_growth} />
            <FactorRow label="Sector Shift" value={factors.sector_shift} />
            <FactorRow label="Spatial Cluster" value={factors.spatial_cluster} />
          </div>
        </div>

        <div>
          <SectionTitle>Reason</SectionTitle>
          <div style={{ color: '#dbeafe', fontSize: 13, lineHeight: 1.35 }}>
            {primaryReason}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function HeatMap({ allocations: allocationRows }) {
  const mapRef     = useRef(null)
  const leafletRef = useRef(null)
  const layersRef  = useRef({})
  const geojsonRef = useRef(null)
  const { wardData, allocations, isLoading } = useMapStore()
  const activeAllocations = allocationRows ?? allocations ?? wardData ?? []
  const [nameMismatchWarning, setNameMismatchWarning] = useState(false)
  const [hoverTooltip, setHoverTooltip] = useState(null)

  useEffect(() => {
    if (leafletRef.current) return
    if (!mapRef.current) return

    import('leaflet').then(L => {
      // Guard sau async — tránh React StrictMode double-invoke
      if (leafletRef.current) return
      if (!mapRef.current) return

      L.Icon.Default.prototype._getIconUrl = () => ''
      const map = L.map(mapRef.current, {
        center: [10.776, 106.701],
        zoom: 11,
        zoomControl: true,
        attributionControl: false,
      })
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
      }).addTo(map)
      leafletRef.current = map

      dataService.getWardsGeoJson().then(raw => {
        const features = Array.isArray(raw?.features) ? raw.features : []
        console.log('[GEOJSON RAW]', raw)
        console.log('[GEOJSON FEATURES]', features.length)

        if (raw?.type !== 'FeatureCollection' || !Array.isArray(raw.features)) {
          console.error('[GEOJSON ERROR] Invalid FeatureCollection', raw)
          return
        }

        geojsonRef.current = raw
        renderWards(L, map, raw, activeAllocations)
      }).catch(error => {
        console.error('[GEOJSON ERROR] Invalid FeatureCollection', error)
      })
    })

    return () => {
      leafletRef.current?.remove()
      leafletRef.current = null
    }
  }, [])

  const renderWards = useCallback((L, map, geojson, wards) => {
    Object.values(layersRef.current).forEach(l => map.removeLayer(l))
    layersRef.current = {}

    const allocationData = Array.isArray(wards) ? wards : []
    const stats = getAllocationRiskStats(allocationData)
    const wardLookup = buildWardLookup(allocationData)
    const features = Array.isArray(geojson?.features) ? geojson.features : []
    console.group('[MAP]')
    console.log('geo features:', features.length)
    console.log('allocation rows:', allocationData?.length)
    console.log('geo sample:', geojson?.features?.slice?.(0, 3))
    console.log('allocation sample:', allocationData?.slice?.(0, 3))
    console.groupEnd()
    console.log('[MAP] allocation keys:', Array.from(wardLookup.normalized.keys()).slice(0, 10))
    const matchedCount = features.reduce((count, feature) => (
      findWardMatch(feature, wardLookup) ? count + 1 : count
    ), 0)
    console.log('[MAP] matched:', matchedCount, '/', features.length)
    if (features.length > 0 && allocationData.length > 0 && matchedCount === 0) {
      console.error('[MAP] No features matched allocation')
    }

    if (import.meta.env.DEV) {
      console.debug('[HeatMap]', {
        allocationCount: allocationData.length,
        geoFeatureCount: features.length,
        matchedCount,
        sampleAllocationKeys: Array.from(wardLookup.normalized.keys()).slice(0, 8),
        sampleGeoKeys: features.slice(0, 5).map(getFeatureCandidateKeys),
      })
    }

    setNameMismatchWarning(allocationData.length > 0 && features.length > 0 && matchedCount === 0)

    if (features.length === 0) return

    L.geoJSON(geojson, {
      style: (feature) => {
        const w = findWardMatch(feature, wardLookup)
        const mwh = w?.allocated_mwh ?? 0
        const risk = w ? getPriorityLevel(w) : getRiskLevelForLoad(mwh, stats)
        return {
          fillColor: getRiskFill(risk, 0.65),
          fillOpacity: 0.65,
          color: 'rgba(255,255,255,0.15)',
          weight: 0.5,
        }
      },
      onEachFeature: (feature, layer) => {
        const wardCode = getFeatureMatchKey(feature)
        const w = findWardMatch(feature, wardLookup)
        const name = feature.properties.name || feature.properties.ward_name || wardCode
        const risk = w ? getPriorityLevel(w) : 'LOW'
        const tooltipData = {
          name,
          risk,
          ward: w ?? {
            ward_code: wardCode,
            ward_name: name,
            priority_level: risk,
          },
        }

        layer.on('mouseover', (event) => {
          layer.setStyle({ fillOpacity: 0.85, weight: 1.5, color: 'rgba(255,255,255,0.4)' })
          console.log('[HEATMAP FULL OBJECT]', tooltipData.ward)
          setHoverTooltip({
            data: tooltipData,
            position: getTooltipPosition(event.originalEvent),
          })
        })
        layer.on('mousemove', (event) => {
          setHoverTooltip({
            data: tooltipData,
            position: getTooltipPosition(event.originalEvent),
          })
        })
        layer.on('mouseout',  () => {
          layer.setStyle({ fillOpacity: 0.65, weight: 0.5, color: 'rgba(255,255,255,0.15)' })
          setHoverTooltip(null)
        })

        layersRef.current[String(wardCode ?? name)] = layer
      }
    }).addTo(map)
  }, [])

  useEffect(() => {
    if (!leafletRef.current || !geojsonRef.current) return
    import('leaflet').then(L => {
      renderWards(L, leafletRef.current, geojsonRef.current, activeAllocations)
    })
  }, [activeAllocations, renderWards])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
      <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
      <WardHoverTooltip tooltip={hoverTooltip} />
      {isLoading && (
        <div style={{
          position: 'absolute', inset: 0,
          background: 'rgba(13,17,23,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1000,
        }}>
          <span style={{ color: 'var(--text-accent)', fontSize: 12, letterSpacing: '0.1em' }}>
            RECALCULATING...
          </span>
        </div>
      )}
      <div style={{
        position: 'absolute', bottom: 20, left: 12,
        background: 'var(--bg-overlay)',
        border: '1px solid var(--border-normal)',
        borderRadius: 6, padding: '8px 12px',
        zIndex: 1000, fontSize: 13,
      }}>
        {[
          { color: 'var(--risk-low)',  label: 'LOW priority' },
          { color: 'var(--risk-med)',  label: 'MEDIUM priority' },
          { color: 'var(--risk-high)', label: 'HIGH priority' },
        ].map(l => (
          <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
            <div style={{ width: 14, height: 14, borderRadius: 3, background: l.color }} />
            <span style={{ color: '#cbd5e1', fontSize: 13, fontWeight: 700 }}>{l.label}</span>
          </div>
        ))}
      </div>
      {nameMismatchWarning && (
        <div style={{
          position: 'absolute',
          top: 20,
          left: 12,
          background: 'var(--bg-overlay)',
          border: '1px solid var(--risk-med)',
          borderRadius: 6,
          padding: '8px 12px',
          zIndex: 1000,
          color: 'var(--text-secondary)',
          fontSize: 11,
          maxWidth: 280,
          lineHeight: 1.4,
        }}>
          Map data loaded but ward names do not match allocation data.
        </div>
      )}
    </div>
  )
}
