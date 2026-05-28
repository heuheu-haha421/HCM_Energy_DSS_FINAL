import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { modelService } from '../services/modelService'
import { simulationService } from '../services/simulationService'
import { useAuthStore } from '../store/authStore'
import { useMapStore } from '../store/mapStore'
import { useAllocation } from '../hooks/useAllocation'
import { canMutate } from '../utils/roles'

export default function AIMonitorPage() {
  const [models, setModels] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [selected, setSelected] = useState(null)
  const [chartData, setChartData] = useState([])
  const [predForm, setPredForm] = useState({ model_run_id: '', week: '' })
  const [predResult, setPredResult] = useState(null)
  const [predLoading, setPredLoading] = useState(false)
  const [uploadForm, setUploadForm] = useState({
    max_depth: '',
    min_child_weight: '',
    mae: '',
    mape: '',
    rmse: '',
    r2: '',
    is_best: 0,
    is_active: 0,
    model_file: null,
  })
  const [uploading, setUploading] = useState(false)
  const { user } = useAuthStore()
  const {
    weights,
    selectedYear,
    setTotalLoad,
    setPredictionReady,
    setAllocationMessage,
  } = useMapStore()
  const { runAllocation } = useAllocation()
  const showMutateControls = canMutate(user)

  useEffect(() => {
    loadModels()
  }, [])

  async function loadModels() {
    modelService.list().then(data => {
      setModels(data)
      const active = data.find(m => m.is_active)
      if (active) {
        setActiveId(active.id)
        setSelected(active)
        loadChart(active.id)
        setPredForm(p => ({ ...p, model_run_id: String(active.id) }))
      }
    })
  }

  async function loadChart(id) {
    try {
      const data = await modelService.acceptanceGraph(id)
      setChartData(data.map((d, i) => ({
        week: d.week, actual: d.actual, predicted: d.predicted,
      })))
    } catch {}
  }

  async function handleSetActive(id) {
    if (!showMutateControls) return
    if (!confirm('Set this model as active?')) return
    await modelService.setActive(id)
    setActiveId(id)
    const updated = models.map(m => ({ ...m, is_active: m.id === id }))
    setModels(updated)
  }

  async function handlePredictionAction(action) {
    if (!showMutateControls) return
    setPredLoading(true)
    setPredResult(null)
    try {
      const r = await modelService[action]()
      setPredictionReady(action !== 'stopPrediction')
      const currentLoad = await simulationService.getCurrentLoad().catch(() => null)
      if (currentLoad?.predicted_load) {
        setTotalLoad(currentLoad.predicted_load)
      }
      if (action !== 'stopPrediction') {
        setAllocationMessage('')
        await runAllocation(weights, selectedYear)
      } else {
        setAllocationMessage('Prediction process stopped. Allocation can still run from the latest prediction data in the database.')
      }
      setPredResult({ action, status: r, currentLoad })
    } catch (e) {
      alert(e.message)
    } finally {
      setPredLoading(false)
    }
  }

  async function handleUploadModel() {
    if (!showMutateControls) return
    if (!uploadForm.model_file) return
    setUploading(true)
    try {
      const fd = new FormData()
      ;[
        'max_depth',
        'min_child_weight',
        'mae',
        'mape',
        'rmse',
        'r2',
        'is_best',
        'is_active',
      ].forEach(key => fd.append(key, uploadForm[key]))
      fd.append('model_file', uploadForm.model_file)
      await modelService.upload(fd)
      await loadModels()
      setPredictionReady(false)
      setAllocationMessage('Model/data changed. Click Generate Allocation to recalculate grid stress.')
      setUploadForm({
        max_depth: '',
        min_child_weight: '',
        mae: '',
        mape: '',
        rmse: '',
        r2: '',
        is_best: 0,
        is_active: 0,
        model_file: null,
      })
    } catch (e) {
      alert(e.message)
    } finally {
      setUploading(false)
    }
  }

  const activeModel = models.find(m => m.id === activeId)

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 20 }}>
      <div style={{
        fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 700,
        letterSpacing: '0.06em', marginBottom: 20,
      }}>AI MONITOR</div>

      {/* Metric cards */}
      {activeModel && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10, marginBottom: 20 }}>
          {[
            { label: 'MAE',   value: activeModel.mae?.toLocaleString() },
            { label: 'MAPE',  value: `${activeModel.mape?.toFixed(2)}%` },
            { label: 'RMSE',  value: activeModel.rmse?.toLocaleString() },
            { label: 'R²',    value: activeModel.r2?.toFixed(3) },
          ].map(m => (
            <div key={m.label} className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.1em', marginBottom: 4 }}>
                {m.label}
              </div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 700, color: 'var(--text-accent)' }}>
                {m.value ?? '--'}
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 16, marginBottom: 20 }}>

        {/* Model runs table */}
        <div className="card">
          <div style={{ fontSize: 11, letterSpacing: '0.1em', color: 'var(--text-secondary)', marginBottom: 10 }}>
            MODEL RUNS
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr>
                  {['ID','DEPTH','CHILD','MAE','MAPE','R²','STATUS',''].map(h => (
                    <th key={h} style={{
                      textAlign: 'left', padding: '6px 8px',
                      fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.08em',
                      borderBottom: '1px solid var(--border-dim)', whiteSpace: 'nowrap',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {models.map(m => (
                  <tr key={m.id}
                    onClick={() => { setSelected(m); loadChart(m.id) }}
                    style={{
                      cursor: 'pointer',
                      background: selected?.id === m.id ? 'var(--accent-dim)' : 'transparent',
                      borderBottom: '1px solid var(--border-dim)',
                    }}
                  >
                    <td style={{ padding: '7px 8px', fontFamily: 'var(--font-mono)', fontSize: 11 }}>{m.id}</td>
                    <td style={{ padding: '7px 8px' }}>{m.max_depth}</td>
                    <td style={{ padding: '7px 8px' }}>{m.min_child_weight}</td>
                    <td style={{ padding: '7px 8px' }}>{m.mae?.toLocaleString()}</td>
                    <td style={{ padding: '7px 8px' }}>{m.mape?.toFixed(2)}%</td>
                    <td style={{ padding: '7px 8px', fontWeight: 600 }}>{m.r2?.toFixed(3)}</td>
                    <td style={{ padding: '7px 8px' }}>
                      {m.is_active && <span className="badge badge-active" style={{ fontSize: 9 }}>ACTIVE</span>}
                      {m.is_best  && <span className="badge badge-best"   style={{ fontSize: 9, marginLeft: 4 }}>BEST</span>}
                    </td>
                    <td style={{ padding: '7px 8px' }}>
                      {showMutateControls && !m.is_active && (
                        <button className="btn" style={{ fontSize: 10, padding: '3px 8px' }}
                          onClick={e => { e.stopPropagation(); handleSetActive(m.id) }}>
                          SET
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {showMutateControls && (
        <div className="card">
          <div style={{ fontSize: 11, letterSpacing: '0.1em', color: 'var(--text-secondary)', marginBottom: 12 }}>
            PREDICTION CONTROLS
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <button className="btn btn-primary" onClick={() => handlePredictionAction('startPrediction')}
              disabled={predLoading}>
              {predLoading ? 'WORKING...' : '▶ START PREDICTION'}
            </button>
            <button className="btn" onClick={() => handlePredictionAction('restartPrediction')}
              disabled={predLoading}>
              RESTART PREDICTION
            </button>
            <button className="btn btn-danger" onClick={() => handlePredictionAction('stopPrediction')}
              disabled={predLoading}>
              STOP PREDICTION
            </button>

            {predResult && (
              <div style={{
                marginTop: 4, padding: 12,
                background: 'var(--bg-overlay)',
                borderRadius: 6, border: '1px solid var(--border-normal)',
              }} className="fade-up">
                <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 8 }}>PREDICTION STATUS</div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                  running: {String(predResult.status?.running ?? '--')}
                </div>
                {predResult.currentLoad?.predicted_load != null && (
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 700, color: 'var(--text-accent)' }}>
                  {(predResult.currentLoad.predicted_load / 1e6).toFixed(3)} GWh
                </div>
                )}
              </div>
            )}
          </div>
        </div>
        )}
      </div>

      {showMutateControls && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', color: 'var(--text-secondary)', marginBottom: 12 }}>
            UPLOAD MODEL
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
            {['max_depth','min_child_weight','mae','mape','rmse','r2'].map(key => (
              <input key={key} className="input" placeholder={key}
                value={uploadForm[key]}
                onChange={e => setUploadForm(p => ({ ...p, [key]: e.target.value }))} />
            ))}
            <input className="input" type="file" accept=".json"
              onChange={e => setUploadForm(p => ({ ...p, model_file: e.target.files[0] }))} />
          </div>
          <button className="btn btn-primary" style={{ marginTop: 10, fontSize: 11 }}
            disabled={uploading || !uploadForm.model_file}
            onClick={handleUploadModel}>
            {uploading ? 'UPLOADING...' : 'UPLOAD MODEL'}
          </button>
        </div>
      )}

      {/* Acceptance Graph */}
      <div className="card">
        <div style={{ fontSize: 11, letterSpacing: '0.1em', color: 'var(--text-secondary)', marginBottom: 12 }}>
          ACCEPTANCE GRAPH — {selected?.id != null ? `MODEL #${selected.id}` : '—'}
        </div>
        {chartData.length === 0 ? (
          <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: 11 }}>
            SELECT A MODEL ROW TO VIEW CHART
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
              <XAxis dataKey="week" tick={{ fontSize: 9, fill: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}
                tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 9, fill: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}
                tickLine={false} axisLine={false}
                tickFormatter={v => (v / 1e9).toFixed(1) + 'T'} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-overlay)', border: '1px solid var(--border-normal)', borderRadius: 6, fontSize: 11, fontFamily: 'var(--font-mono)' }}
                formatter={(v, n) => [(v / 1e6).toFixed(2) + ' GWh', n === 'actual' ? 'Actual' : 'Predicted']}
              />
              <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'var(--font-mono)' }} />
              <Line type="monotone" dataKey="actual" stroke="var(--accent)" strokeWidth={1.5} dot={false} name="actual" />
              <Line type="monotone" dataKey="predicted" stroke="var(--risk-med)" strokeWidth={1.5}
                strokeDasharray="5 3" dot={false} name="predicted" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
