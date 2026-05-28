import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { normalizeToken } from '../services/api'
import { useMapStore } from './mapStore'
import { useLiveStore } from './liveStore'

function clearSessionState() {
  useMapStore.getState().resetDashboardData()
  useLiveStore.getState().resetLiveData()
}

export const useAuthStore = create(persist(
  (set) => ({
    token: normalizeToken(localStorage.getItem('access_token')),
    user: null,
    setAuth: (token, user) => {
      const accessToken = normalizeToken(token)

      if (!accessToken) {
        localStorage.removeItem('access_token')
        sessionStorage.removeItem('access_token')
        clearSessionState()
        set({ token: null, user: null })
        return
      }

      localStorage.setItem('access_token', accessToken)
      set({ token: accessToken, user })
    },
    setUser: (user) => set({ user }),
    logout: () => {
      localStorage.removeItem('access_token')
      sessionStorage.removeItem('access_token')
      clearSessionState()
      set({ token: null, user: null })
    },
  }),
  { name: 'evn-auth' }
))
