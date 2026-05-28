import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Navbar from './Navbar'
import { useWebSocket } from '../../hooks/useWebSocket'

export default function Layout() {
  useWebSocket() // init WS connection globally

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Navbar />
        <main style={{
          flex: 1,
          overflow: 'hidden',
          background: 'var(--bg-void)',
        }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}