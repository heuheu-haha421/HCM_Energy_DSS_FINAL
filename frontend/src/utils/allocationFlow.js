export const DEFAULT_ALLOCATION_WEIGHTS = {
  residential: 15,
  industrial: 50,
  commercial: 5,
  services: 30,
}

export function normalizeDashboardWeights(weights = DEFAULT_ALLOCATION_WEIGHTS) {
  return {
    residential: weights.residential ?? DEFAULT_ALLOCATION_WEIGHTS.residential,
    industrial: weights.industrial ?? DEFAULT_ALLOCATION_WEIGHTS.industrial,
    commercial: weights.commercial ?? DEFAULT_ALLOCATION_WEIGHTS.commercial,
    services: weights.services ?? DEFAULT_ALLOCATION_WEIGHTS.services,
  }
}

export function toAllocationApiWeights(weights = DEFAULT_ALLOCATION_WEIGHTS) {
  const safeWeights = normalizeDashboardWeights(weights)

  return {
    residential: safeWeights.residential / 100,
    industrial: safeWeights.industrial / 100,
    commercial: safeWeights.commercial / 100,
    services: safeWeights.services / 100,
  }
}

export function toScenarioApiWeights(weights = DEFAULT_ALLOCATION_WEIGHTS) {
  const apiWeights = toAllocationApiWeights(weights)

  return {
    w_residential: apiWeights.residential,
    w_industrial: apiWeights.industrial,
    w_commercial: apiWeights.commercial,
    w_services: apiWeights.services,
  }
}

export function fromScenarioApiWeights(weight = {}) {
  return normalizeDashboardWeights({
    residential: Math.round(((weight.residential ?? weight.w_residential) || 0) * 100),
    industrial: Math.round(((weight.industrial ?? weight.w_industrial) || 0) * 100),
    commercial: Math.round(((weight.commercial ?? weight.w_commercial) || 0) * 100),
    services: Math.round(((weight.services ?? weight.w_services) || 0) * 100),
  })
}

export function normalizeMatchKey(value) {
  if (value == null) return ''
  return String(value).trim().toLowerCase().replace(/\s+/g, ' ')
}

export function normalizeWardName(name) {
  if (name == null) return ''

  return String(name)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()
    .replace(/^(ward|commune|phuong|xa|thi tran)\s+/i, '')
    .replace(/\s+/g, ' ')
}

export function getWardMatchKey(row) {
  return (
    row?.ward_code ??
    row?.ward_id ??
    row?.code ??
    row?.id ??
    row?.name ??
    row?.ward_name ??
    null
  )
}

export function normalizeWard(row) {
  const wardCode = getWardMatchKey(row)
  const wardName = row?.ward_name ?? row?.name
  const allocatedKwh =
    row?.allocated_kwh != null
      ? Number(row.allocated_kwh)
      : row?.allocated_mwh != null
        ? Number(row.allocated_mwh) * 1000
        : null
  const allocatedMwh = allocatedKwh != null ? allocatedKwh / 1000 : null

  return {
    ...row,
    ward_code: wardCode,
    ward_id: row?.ward_id ?? row?.id ?? wardCode,
    ward_name: wardName,
    name: row?.name ?? row?.ward_name ?? wardCode,
    allocated_kwh: allocatedKwh,
    allocated_mwh: allocatedMwh,
    priority_level: row?.priority_level ?? row?.risk_level ?? 'LOW',
    risk_level: row?.priority_level ?? row?.risk_level ?? 'LOW',
  }
}
