import { useEffect, useRef } from 'react'
import { useLiveStore } from '../store/liveStore'
import { useAuthStore } from '../store/authStore'
import { normalizeToken } from '../services/api'

const DEFAULT_WS_URL = typeof window === 'undefined'
  ? 'ws://localhost:8000'
  : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
const WS_URL = import.meta.env.VITE_WS_URL || DEFAULT_WS_URL

export function useWebSocket() {
  const wsRef = useRef(null)
  const reconnectRef = useRef(null)
  const { addPoint, setConnected } = useLiveStore()
  const { token, logout } = useAuthStore()

  useEffect(() => {
    const accessToken =
      normalizeToken(token) ||
      normalizeToken(localStorage.getItem('access_token')) ||
      normalizeToken(sessionStorage.getItem('access_token'))

    if (!accessToken) {
      setConnected(false)
      return
    }

    let shouldReconnect = true

    function connect() {
      wsRef.current = new WebSocket(
        `${WS_URL}/ws/v1/live-predict?token=${encodeURIComponent(accessToken)}`
      )

      wsRef.current.onopen = () => {
        console.log('[WS OPEN]')
        setConnected(true)
        if (reconnectRef.current) {
          clearTimeout(reconnectRef.current)
          reconnectRef.current = null
        }
      }

      wsRef.current.onmessage = (event) => {
        console.log('[WS RAW]', event.data)
        try {
          const message = JSON.parse(event.data)
          console.log('[WS PARSED]', message)
          const data = message?.data && typeof message.data === 'object'
            ? message.data
            : message

          if (data?.predicted_load != null) {
            addPoint(data)
          }
        } catch {
          // Ignore malformed live packets; the next valid broadcast will update the chart.
        }
      }

      wsRef.current.onclose = (e) => {
        if (e.code === 1006) {
          console.warn('[WS CLOSED]', e.code, e.reason)
        } else {
          console.log('[WS CLOSED]', e.code, e.reason)
        }
        setConnected(false)
        if (e.code === 1008) {
          shouldReconnect = false
          logout()
          return
        }
        if (shouldReconnect) {
          reconnectRef.current = setTimeout(connect, 3000)
        }
      }

      wsRef.current.onerror = (e) => {
        console.error('[WS ERROR]', e)
        wsRef.current?.close()
      }
    }

    connect()
    return () => {
      shouldReconnect = false
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
        wsRef.current.close()
      }
    }
  }, [token, addPoint, setConnected, logout])
}
