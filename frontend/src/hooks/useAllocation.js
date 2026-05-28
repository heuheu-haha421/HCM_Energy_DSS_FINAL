import { useCallback, useRef } from 'react'
import { useMapStore } from '../store/mapStore'
import { simulationService } from '../services/simulationService'
import {
  DEFAULT_ALLOCATION_WEIGHTS,
  normalizeDashboardWeights,
  normalizeWard,
  toAllocationApiWeights,
} from '../utils/allocationFlow'
import { attachRiskLevels } from '../utils/riskLevels'

const RUNTIME_NOT_READY_MESSAGE =
  'Generate allocation failed. Please check the latest prediction and energy data.'

const MISSING_WARD_INFRA_MESSAGE =
  'No ward infrastructure data found for the selected year. Upload ward stats or choose the correct year.'

const MISSING_WARD_ALLOCATION_MESSAGE =
  'No allocation data is available for this year. Generate allocation first.'

function getErrorText(error) {
  return String(error?.message ?? error?.data?.error ?? error?.data?.detail ?? '')
}

function getAllocationMessage(error) {
  const text = getErrorText(error)

  if (text.includes('total_load is None')) return RUNTIME_NOT_READY_MESSAGE
  if (text.includes('No ward infrastructure data')) return MISSING_WARD_INFRA_MESSAGE

  return text || 'Allocation failed.'
}

function getTopRiskMessage(error) {
  const text = getErrorText(error)

  if (text.includes('No ward allocation data')) return MISSING_WARD_ALLOCATION_MESSAGE

  return text || 'Top risks failed.'
}

function getWardMergeKeys(row) {
  return [
    row?.ward_code,
    row?.ward_id,
    row?.code,
    row?.id,
    row?.ward_name,
    row?.name,
  ]
    .filter(value => value != null)
    .map(value => String(value).trim().toLowerCase())
    .filter(Boolean)
}

function mergeGridStressIntoWards(wards, gridStressRows) {
  const fullRowsByKey = new Map()

  gridStressRows.forEach((row) => {
    getWardMergeKeys(row).forEach(key => {
      if (!fullRowsByKey.has(key)) fullRowsByKey.set(key, row)
    })
  })

  return wards.map((ward) => {
    const fullRow = getWardMergeKeys(ward)
      .map(key => fullRowsByKey.get(key))
      .find(Boolean)

    return fullRow ? normalizeWard({ ...ward, ...fullRow }) : ward
  })
}

export function useAllocation() {
  const {
    selectedYear,
    setWardData,
    setTopRisks,
    setLoading,
    setPredictionReady,
    setAllocationMessage,
    setTotalLoad,
    setGridStressMeta,
  } = useMapStore()
  const debounceRef = useRef(null)

  const runAllocation = useCallback(async (w, year = selectedYear) => {
    // Apply scenario/dashboard weights before calling allocation API.
    const safeWeights = normalizeDashboardWeights(w ?? DEFAULT_ALLOCATION_WEIGHTS)

    setLoading(true)
    setAllocationMessage('')
    console.group('[ALLOC]')
    console.log('year:', year)
    console.log('weights:', safeWeights)
    try {
      const apiWeights = toAllocationApiWeights(safeWeights)
      const allocation = await simulationService.allocate({ year, weights: apiWeights })
      console.log('allocate response:', allocation)
      console.log('[ALLOC] count:', allocation?.data?.results?.length ?? allocation?.results?.length)
      setGridStressMeta({
        total_load: allocation?.total_load,
        avg_temp: allocation?.avg_temp,
        method: allocation?.method,
        week: allocation?.week,
        start_date: allocation?.start_date,
        end_date: allocation?.end_date,
        count: allocation?.count,
      })
      if (allocation?.total_load != null) setTotalLoad(allocation.total_load)

      const wards = attachRiskLevels((allocation?.results ?? []).map(normalizeWard))
      setWardData(wards)
      setPredictionReady(true)

      try {
        const gridStress = await simulationService.gridStressPriorities({
          year,
          limit: Math.max(10, wards.length),
        })
        console.log('top risks response:', gridStress)
        const payload = gridStress?.data ?? gridStress
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
        const topRiskItems = Array.isArray(payload)
          ? payload
          : payload?.results ?? []
        const risks = topRiskItems.map(normalizeWard)
        const enrichedWards = mergeGridStressIntoWards(wards, risks)
        setWardData(enrichedWards)
        setTopRisks(risks.slice(0, 10))
      } catch (topRiskError) {
        setTopRisks([])
        setAllocationMessage(getTopRiskMessage(topRiskError))
        console.error('Top risks failed', topRiskError)
      }
    } catch (allocationError) {
      const message = getAllocationMessage(allocationError)
      setAllocationMessage(message)
      if (getErrorText(allocationError).includes('total_load is None')) {
        setPredictionReady(false)
      }
      console.error('Allocation failed', allocationError)
    } finally {
      console.groupEnd()
      setLoading(false)
    }
  }, [
    selectedYear,
    setWardData,
    setTopRisks,
    setLoading,
    setPredictionReady,
    setAllocationMessage,
    setTotalLoad,
    setGridStressMeta,
  ])

  const debouncedAllocation = useCallback((w) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => runAllocation(w), 300)
  }, [runAllocation])

  return { debouncedAllocation, runAllocation }
}
