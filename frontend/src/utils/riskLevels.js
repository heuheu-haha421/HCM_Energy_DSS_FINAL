const RISK_COLORS = {
  LOW: '#22c55e',
  MEDIUM: '#f59e0b',
  HIGH: '#f97316',
}

export const RISK_META = {
  LOW:    { color: 'var(--risk-low)',  fill: RISK_COLORS.LOW,    label: 'LOW RISK' },
  MEDIUM: { color: 'var(--risk-med)',  fill: RISK_COLORS.MEDIUM, label: 'MEDIUM RISK' },
  HIGH:   { color: 'var(--risk-high)', fill: RISK_COLORS.HIGH,   label: 'HIGH RISK' },
}

export function normalizeRiskLevel(level) {
  const value = String(level ?? 'LOW').toUpperCase()
  if (value === 'MED') return 'MEDIUM'
  return RISK_META[value] ? value : 'LOW'
}

export function getPriorityLevel(rowOrLevel) {
  if (typeof rowOrLevel === 'string') return normalizeRiskLevel(rowOrLevel)
  return normalizeRiskLevel(rowOrLevel?.priority_level ?? rowOrLevel?.risk_level ?? 'LOW')
}

export function getRiskBadgeClass(level) {
  const value = getPriorityLevel(level)
  return value === 'MEDIUM' ? 'badge-med' : `badge-${value.toLowerCase()}`
}

export function getAllocationRiskStats(wards = []) {
  const loads = wards
    .map((ward) => Number(ward?.allocated_mwh))
    .filter((value) => Number.isFinite(value))

  if (loads.length === 0) {
    return {
      mean: 0,
      std: 0,
      mediumThreshold: 0,
      highThreshold: 0,
    }
  }

  const mean = loads.reduce((sum, value) => sum + value, 0) / loads.length
  const variance = loads.reduce((sum, value) => sum + (value - mean) ** 2, 0) / loads.length
  const std = Math.sqrt(variance)

  return {
    mean,
    std,
    mediumThreshold: mean + 0.5 * std,
    highThreshold: mean + 1.5 * std,
  }
}

export function getRiskLevelForLoad(allocatedMwh, stats) {
  const value = Number(allocatedMwh)
  if (!Number.isFinite(value)) return 'LOW'
  if (value > stats.highThreshold) return 'HIGH'
  if (value > stats.mediumThreshold) return 'MEDIUM'
  return 'LOW'
}

export function getRiskFill(level, opacity = 0.7) {
  const hex = RISK_META[normalizeRiskLevel(level)].fill
  const value = Number.parseInt(hex.slice(1), 16)
  const r = (value >> 16) & 255
  const g = (value >> 8) & 255
  const b = value & 255
  return `rgba(${r},${g},${b},${opacity})`
}

export function attachRiskLevels(wards = []) {
  const stats = getAllocationRiskStats(wards)
  return wards.map((ward) => ({
    ...ward,
    priority_level: getPriorityLevel(ward?.priority_level ?? ward?.risk_level ?? getRiskLevelForLoad(ward?.allocated_mwh, stats)),
    risk_level: getPriorityLevel(ward?.priority_level ?? ward?.risk_level ?? getRiskLevelForLoad(ward?.allocated_mwh, stats)),
  }))
}
