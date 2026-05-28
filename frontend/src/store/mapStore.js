import { create } from 'zustand'
import { DEFAULT_ALLOCATION_WEIGHTS } from '../utils/allocationFlow'

export const useMapStore = create((set) => ({
  wardData: [],           // 168 wards allocation result
  allocations: [],        // canonical allocation rows for HeatMap
  gridStressMeta: null,
  totalLoad: null,        // latest predicted load
  topRisks: [],           // top 10 risk wards
  selectedYear: new Date().getFullYear(),
  weights: DEFAULT_ALLOCATION_WEIGHTS,
  isLoading: false,
  predictionReady: false,
  allocationMessage: '',
  setWardData: (wardData) => {
    console.group('[STORE]')
    console.log('allocation rows:', wardData?.length)
    console.log('sample:', wardData?.slice?.(0, 3))
    console.groupEnd()
    set({ wardData, allocations: wardData })
  },
  setTotalLoad: (totalLoad) => set({ totalLoad }),
  setTopRisks: (topRisks) => set({ topRisks }),
  setGridStressMeta: (gridStressMeta) => set({ gridStressMeta }),
  setSelectedYear: (selectedYear) => set({ selectedYear }),
  setWeights: (weights) => set({ weights }),
  setLoading: (isLoading) => set({ isLoading }),
  setPredictionReady: (predictionReady) => set({ predictionReady }),
  setAllocationMessage: (allocationMessage) => set({ allocationMessage }),
  resetDashboardData: () => set({
    wardData: [],
    allocations: [],
    gridStressMeta: null,
    totalLoad: null,
    topRisks: [],
    isLoading: false,
    predictionReady: false,
    allocationMessage: '',
  }),
}))
