import { useCallback, useEffect, useMemo, useState } from 'react'
import { authApi, sessionStore } from '../api/client'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState(() => sessionStore.get() ? 'restoring' : 'anonymous')
  const [sessionNotice, setSessionNotice] = useState('')
  const logout = useCallback((notice = '') => { sessionStore.clear(); setUser(null); setSessionNotice(notice); setStatus('anonymous') }, [])

  useEffect(() => {
    if (!sessionStore.get()) return
    authApi.me().then((currentUser) => { setUser(currentUser); setStatus('authenticated') }).catch((error) => {
      logout(error.code === 'unauthorized' ? 'Your session expired. Sign in again.' : 'We could not restore your session. Sign in again.')
    })
  }, [logout])

  const login = useCallback(async (email, password) => {
    const token = await authApi.login(email, password)
    sessionStore.set(token.access_token)
    try {
      const currentUser = await authApi.me()
      setUser(currentUser); setSessionNotice(''); setStatus('authenticated')
      return currentUser
    } catch (error) { sessionStore.clear(); throw error }
  }, [])

  const value = useMemo(() => ({ user, status, sessionNotice, login, logout }), [user, status, sessionNotice, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
