import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { authService } from '../services/authService'

export default function LoginPage() {
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await authService.login(form.username, form.password)
      setAuth(data.access_token, {
        username: form.username,
        role: data.role,
        user_id: data.user_id,
      })
      navigate('/')
    } catch (err) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-void)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Grid background */}
      <div style={{
        position: 'absolute', inset: 0, opacity: 0.04,
        backgroundImage: `
          linear-gradient(var(--accent) 1px, transparent 1px),
          linear-gradient(90deg, var(--accent) 1px, transparent 1px)
        `,
        backgroundSize: '40px 40px',
      }} />

      <div className="card fade-up" style={{
        width: 360,
        position: 'relative',
        zIndex: 1,
        border: '1px solid var(--border-normal)',
      }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 800,
            fontSize: 28,
            letterSpacing: '0.15em',
            color: 'var(--text-accent)',
            marginBottom: 4,
          }}>EVN·DSS</div>
          <div style={{
            fontSize: 10,
            letterSpacing: '0.2em',
            color: 'var(--text-dim)',
          }}>ENERGY DISTRIBUTION SUPPORT SYSTEM</div>
          <div style={{
            marginTop: 12,
            fontSize: 10,
            color: 'var(--text-dim)',
            letterSpacing: '0.1em',
          }}>HO CHI MINH CITY · AUTHORIZED ACCESS ONLY</div>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 14 }}>
            <label className="label">USERNAME</label>
            <input
              className="input"
              type="text"
              value={form.username}
              onChange={e => setForm(p => ({ ...p, username: e.target.value }))}
              autoComplete="username"
              required
            />
          </div>
          <div style={{ marginBottom: 20 }}>
            <label className="label">PASSWORD</label>
            <input
              className="input"
              type="password"
              value={form.password}
              onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <div style={{
              background: 'var(--risk-crit-bg)',
              border: '1px solid var(--risk-crit)',
              borderRadius: 6,
              padding: '8px 12px',
              fontSize: 12,
              color: 'var(--risk-crit)',
              marginBottom: 14,
              letterSpacing: '0.05em',
            }}>
              {error}
            </div>
          )}

          <button
            className="btn btn-primary"
            type="submit"
            disabled={loading}
            style={{ width: '100%', letterSpacing: '0.12em' }}
          >
            {loading ? 'AUTHENTICATING...' : 'LOGIN'}
          </button>
        </form>
      </div>
    </div>
  )
}
