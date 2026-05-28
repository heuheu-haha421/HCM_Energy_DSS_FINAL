import { useState } from 'react'
import { modelService } from '../../services/modelService'
import { useMapStore } from '../../store/mapStore'
import { simulationService } from '../../services/simulationService'
import {
  normalizeWard,
  toAllocationApiWeights,
} from '../../utils/allocationFlow'
import { attachRiskLevels } from '../../utils/riskLevels'

/**
 * Props:
 *   modelRunId  – int | null  (if null, uses active model)
 *   week        – string | null (if null, predicts current week)
 *   onResult    – callback(result) after successful prediction
 *   label       – string override for button text
 *   variant     – 'primary' | 'ghost'
 *   fullWidth   – boolean
 */
export default function PredictButton({
  modelRunId  = null,
  week        = null,
  onResult    = null,
  label       = null,
  variant     = 'primary',
  fullWidth   = false,
}) {
  const [state, setState] = useState('idle') // idle | loading | success | error
  const [errorMsg, setErrorMsg] = useState('')
  const {
    selectedYear,
    setTotalLoad,
    weights,
    setWardData,
    setTopRisks,
    setPredictionReady,
    setAllocationMessage,
  } = useMapStore()

  async function handleClick() {
    setState('loading')
    setErrorMsg('')
    try {
      const result = await modelService.predict(modelRunId, week)
      setPredictionReady(true)
      setAllocationMessage('')
      const currentLoad = await simulationService.getCurrentLoad().catch(() => null)

      if (currentLoad?.predicted_load) {
        setTotalLoad(currentLoad.predicted_load)
      }

      const allocation = await simulationService.allocate({
        year: selectedYear,
        weights: toAllocationApiWeights(weights),
      })
      const wards = attachRiskLevels((allocation?.results ?? []).map(normalizeWard))
      setWardData(wards)

      try {
        const topRisks = await simulationService.topRisks({ year: selectedYear, limit: 10 })
        const topRiskItems = Array.isArray(topRisks)
          ? topRisks
          : topRisks?.results ?? topRisks?.data?.results ?? []
        const risks = topRiskItems.map(normalizeWard)
        setTopRisks(risks)
      } catch (topRiskError) {
        setTopRisks([])
        setAllocationMessage(
          String(topRiskError.message).includes('No ward allocation data')
            ? 'No allocation data is available for this year. Generate allocation first.'
            : topRiskError.message
        )
      }

      setState('success')
      onResult?.({ status: result, currentLoad })

      // Reset to idle after 2s
      setTimeout(() => setState('idle'), 2000)
    } catch (e) {
      if (String(e.message).includes('total_load is None')) {
        setPredictionReady(false)
        setAllocationMessage('Generate allocation failed. Please check the latest prediction and energy data.')
      }
      setErrorMsg(e.message || 'Prediction failed')
      setState('error')
      setTimeout(() => setState('idle'), 3000)
    }
  }

  const isLoading = state === 'loading'
  const isSuccess = state === 'success'
  const isError   = state === 'error'

  const baseStyle = {
    display:        'inline-flex',
    alignItems:     'center',
    justifyContent: 'center',
    gap:            6,
    padding:        '8px 18px',
    borderRadius:   6,
    fontSize:       12,
    fontFamily:     'var(--font-mono)',
    fontWeight:     500,
    letterSpacing:  '0.08em',
    cursor:         isLoading ? 'not-allowed' : 'pointer',
    transition:     'all 0.15s',
    border:         '1px solid',
    width:          fullWidth ? '100%' : undefined,
    opacity:        isLoading ? 0.7 : 1,
  }

  const variantStyle = isError ? {
    borderColor: 'var(--risk-crit)',
    background:  'var(--risk-crit-bg)',
    color:       'var(--risk-crit)',
  } : isSuccess ? {
    borderColor: 'var(--risk-low)',
    background:  'var(--risk-low-bg)',
    color:       'var(--risk-low)',
  } : variant === 'primary' ? {
    borderColor: 'var(--accent)',
    background:  'var(--accent)',
    color:       '#fff',
  } : {
    borderColor: 'var(--border-normal)',
    background:  'var(--bg-overlay)',
    color:       'var(--text-secondary)',
  }

  function getContent() {
    if (isLoading) return (
      <>
        <SpinnerIcon />
        PREDICTING...
      </>
    )
    if (isSuccess) return <>✓ PREDICTED</>
    if (isError)   return <>✗ FAILED</>
    return (
      <>
        <PlayIcon />
        {label ?? 'PREDICT NOW'}
      </>
    )
  }

  return (
    <div>
      <button
        onClick={handleClick}
        disabled={isLoading}
        style={{ ...baseStyle, ...variantStyle }}
      >
        {getContent()}
      </button>
      {isError && errorMsg && (
        <div style={{
          marginTop: 6, fontSize: 11,
          color: 'var(--risk-crit)',
          letterSpacing: '0.04em',
        }}>
          {errorMsg}
        </div>
      )}
    </div>
  )
}

function PlayIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
      <polygon points="1,0 9,5 1,10" />
    </svg>
  )
}

function SpinnerIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5"
      style={{ animation: 'spin 0.8s linear infinite' }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round"/>
    </svg>
  )
}
