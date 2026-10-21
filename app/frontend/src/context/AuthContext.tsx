import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api, ApiError, setToken } from '../api/client'
import type { User } from '../api/types'

interface AuthState {
  user: User | null
  loading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  register: (
    email: string,
    password: string,
    displayName: string,
    workspaceName: string,
  ) => Promise<void>
  enterDemo: () => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

function messageOf(error: unknown): string {
  if (error instanceof ApiError) return error.userMessage
  if (error instanceof Error) return error.message
  return 'Неизвестная ошибка'
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const current = await api.me()
      setUser(current)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const login = useCallback(async (email: string, password: string) => {
    setError(null)
    try {
      const response = await api.login(email, password)
      setToken(response.access_token)
      setUser(response.user)
    } catch (err) {
      setError(messageOf(err))
      throw err
    }
  }, [])

  const register = useCallback(
    async (email: string, password: string, displayName: string, workspaceName: string) => {
      setError(null)
      try {
        const response = await api.register(email, password, displayName, workspaceName)
        setToken(response.access_token)
        setUser(response.user)
      } catch (err) {
        setError(messageOf(err))
        throw err
      }
    },
    [],
  )

  const enterDemo = useCallback(async () => {
    setError(null)
    try {
      const response = await api.demoLogin()
      setToken(response.access_token)
      setUser(response.user)
    } catch (err) {
      setError(messageOf(err))
      throw err
    }
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  const value = useMemo<AuthState>(
    () => ({ user, loading, error, login, register, enterDemo, logout, refresh }),
    [user, loading, error, login, register, enterDemo, logout, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth используется вне AuthProvider')
  }
  return context
}
