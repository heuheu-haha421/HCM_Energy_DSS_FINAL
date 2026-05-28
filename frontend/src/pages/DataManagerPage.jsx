import { useState, useEffect } from 'react'
import { dataService } from '../services/dataService'
import DemoToggle from '../components/controls/DemoToggle'
import { useAuthStore } from '../store/authStore'
import { useMapStore } from '../store/mapStore'
import { canMutate } from '../utils/roles'

export default function DataManagerPage() {
  const [status, setStatus] = useState(null)
  const [energyFile, setEnergyFile] = useState(null)
  const [wardFile, setWardFile] = useState(null)
  const [holidayFile, setHolidayFile] = useState(null)
  const [uploading, setUploading] = useState({})
  const [uploadMsg, setUploadMsg] = useState({})
  const { user } = useAuthStore()
  const { setPredictionReady, setAllocationMessage } = useMapStore()
  const showMutateControls = canMutate(user)

  useEffect(() => { loadStatus() }, [])

  async function loadStatus() {
    try { setStatus(await dataService.status()) } catch {}
  }

  async function upload(type, file) {
    if (!file) return
    setUploading(p => ({ ...p, [type]: true }))
    setUploadMsg(p => ({ ...p, [type]: '' }))
    try {
      const uploaders = {
        energy: dataService.uploadEnergy,
        ward: dataService.uploadWardStats,
        holiday: dataService.uploadHoliday,
      }
      const r = await uploaders[type](file)
      setUploadMsg(p => ({ ...p, [type]: '✓ ' + (r.message || 'Upload successful') }))
      setPredictionReady(false)
      setAllocationMessage('Data changed. Click Generate Allocation to recalculate grid stress.')
      await loadStatus()
    } catch (e) {
      setUploadMsg(p => ({ ...p, [type]: '✗ ' + e.message }))
    } finally {
      setUploading(p => ({ ...p, [type]: false }))
    }
  }

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 20 }}>
      <div style={{
        fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 700,
        letterSpacing: '0.06em', marginBottom: 20,
      }}>DATA MANAGEMENT</div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

        {/* DB Status */}
        <div className="card" style={{ gridColumn: '1 / -1' }}>
          <div style={{ fontSize: 11, letterSpacing: '0.1em', color: 'var(--text-secondary)', marginBottom: 12 }}>
            DATABASE STATUS
          </div>
          {status ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
              {[
                { label: 'ENERGY ROWS', value: status.energy_rows },
                { label: 'WARD ROWS',   value: status.ward_rows },
                { label: 'STATUS',      value: status.status, ok: status.status === 'ok' },
              ].map(s => (
                <div key={s.label} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.1em', marginBottom: 4 }}>
                    {s.label}
                  </div>
                  <div style={{
                    fontSize: 18, fontWeight: 600,
                    color: s.ok != null ? (s.ok ? 'var(--risk-low)' : 'var(--risk-crit)')
                      : s.warn ? 'var(--risk-crit)' : 'var(--text-accent)',
                  }}>
                    {String(s.value)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="skeleton" style={{ height: 48 }} />
          )}
        </div>

        {showMutateControls && (
          <>
            <UploadCard
              title="ENERGY DATA"
              description="Weekly energy CSV from EVNHCMC extraction"
              accept=".csv"
              file={energyFile}
              onFileChange={setEnergyFile}
              onUpload={() => upload('energy', energyFile)}
              uploading={uploading.energy}
              message={uploadMsg.energy}
            />

            <UploadCard
              title="WARD STATISTICS"
              description="Infrastructure CSV from Statistical Yearbook"
              accept=".csv"
              file={wardFile}
              onFileChange={setWardFile}
              onUpload={() => upload('ward', wardFile)}
              uploading={uploading.ward}
              message={uploadMsg.ward}
            />

            <UploadCard
              title="HOLIDAY DATA"
              description="Holiday calendar CSV for prediction preprocessing"
              accept=".csv"
              file={holidayFile}
              onFileChange={setHolidayFile}
              onUpload={() => upload('holiday', holidayFile)}
              uploading={uploading.holiday}
              message={uploadMsg.holiday}
            />

            <div className="card" style={{ gridColumn: '1 / -1' }}>
              <div style={{ fontSize: 11, letterSpacing: '0.1em', color: 'var(--text-secondary)', marginBottom: 12 }}>
                DEMO ENGINE
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
                <DemoToggle />
              </div>
            </div>
          </>
        )}

        {!showMutateControls && (
          <div className="card" style={{ gridColumn: '1 / -1' }}>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', letterSpacing: '0.08em' }}>
              READ-ONLY ACCESS
            </div>
          </div>
        )}

      </div>
    </div>
  )
}

function UploadCard({ title, description, accept, file, onFileChange, onUpload, uploading, message }) {
  return (
    <div className="card">
      <div style={{ fontSize: 11, letterSpacing: '0.1em', color: 'var(--text-secondary)', marginBottom: 4 }}>
        {title}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 12 }}>{description}</div>

      <label style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        height: 80, border: '1px dashed var(--border-normal)', borderRadius: 6,
        cursor: 'pointer', marginBottom: 10, fontSize: 11, color: 'var(--text-dim)',
        transition: 'border-color 0.15s',
      }}
        onDragOver={e => e.preventDefault()}
        onDrop={e => { e.preventDefault(); onFileChange(e.dataTransfer.files[0]) }}
      >
        <input type="file" accept={accept} style={{ display: 'none' }}
          onChange={e => onFileChange(e.target.files[0])} />
        {file ? (
          <>
            <span style={{ color: 'var(--risk-low)', fontSize: 13 }}>✓</span>
            <span style={{ marginTop: 4, color: 'var(--text-secondary)' }}>{file.name}</span>
          </>
        ) : (
          <>
            <span style={{ fontSize: 20, marginBottom: 4 }}>⊕</span>
            DRAG & DROP or CLICK
          </>
        )}
      </label>

      <button className="btn btn-primary" style={{ width: '100%', fontSize: 11 }}
        disabled={!file || uploading} onClick={onUpload}>
        {uploading ? 'UPLOADING...' : 'UPLOAD & PROCESS'}
      </button>

      {message && (
        <div style={{
          marginTop: 8, fontSize: 11,
          color: message.startsWith('✓') ? 'var(--risk-low)' : 'var(--risk-crit)',
        }}>
          {message}
        </div>
      )}
    </div>
  )
}
