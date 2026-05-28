import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { isAdminOrDev, isDev } from '../../utils/roles'

const NAV = [
  { to: '/',          icon: '⬡', label: 'SIMULATION' },
  { to: '/scenarios', icon: '◈', label: 'SCENARIOS'  },
  { to: '/ai-monitor',icon: '◉', label: 'AI MONITOR' },
  { to: '/data',      icon: '⊞', label: 'DATA MGMT' },
]

export default function Sidebar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  function openTester() {
    window.open('/tester.html', '_blank')
  }

  return (
    <aside style={{
      width: 'var(--sidebar-w)',
      height: '100vh',
      background: 'var(--bg-surface)',
      borderRight: '1px solid var(--border-dim)',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
    }}>
      {/* Logo */}
      <div style={{
        padding: '20px 16px 16px',
        borderBottom: '1px solid var(--border-dim)',
      }}>
        <div style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 800,
          fontSize: 16,
          letterSpacing: '0.12em',
          color: 'var(--text-accent)',
        }}>EVN·DSS</div>
        <div style={{
          fontSize: 10,
          color: 'var(--text-dim)',
          letterSpacing: '0.15em',
          marginTop: 2,
        }}>HCM ENERGY GRID</div>
      </div>

      {/* Nav links */}
      <nav style={{ flex: 1, padding: '8px 0' }}>
        {NAV.filter(n => !n.adminOnly || isAdminOrDev(user)).map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '12px 16px',
              color: isActive ? '#ffffff' : '#cbd5e1',
              background: isActive ? 'rgba(59,130,246,0.22)' : 'transparent',
              borderLeft: isActive ? '4px solid var(--accent)' : '4px solid transparent',
              textDecoration: 'none',
              fontSize: 12,
              letterSpacing: '0.06em',
              fontWeight: isActive ? 800 : 650,
              transition: 'all 0.15s',
            })}
          >
            <span style={{ fontSize: 14 }}>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* User info */}
      <div style={{
        padding: '12px 16px',
        borderTop: '1px solid var(--border-dim)',
      }}>
        {isDev(user) && (
          <button className="btn btn-primary" style={{ width: '100%', fontSize: 11, marginBottom: 10 }} onClick={openTester}>
            API TESTER
          </button>
        )}
        <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4 }}>
          {user?.role?.toUpperCase()}
        </div>
        <div style={{
          fontSize: 12,
          color: 'var(--text-secondary)',
          marginBottom: 8,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {user?.username}
        </div>
        <button className="btn" style={{ width: '100%', fontSize: 11 }} onClick={handleLogout}>
          LOGOUT
        </button>
      </div>
    </aside>
  )
}
