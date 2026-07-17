import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { login as apiLogin, logout as apiLogout, getProfile } from '@/lib/api'

interface User { id: number; username: string; role: string; email?: string }
interface AuthCtx {
  user: User | null
  loading: boolean
  // PM V2 Part 4: true when the account has must_change_password=true.
  // While this is true, `user` stays null (the backend 403s /profile/me
  // for a locked account — see app/core/deps.py get_current_user — so
  // there's no profile to populate yet) and App.tsx routes everything to
  // the forced-change screen regardless of what was requested.
  mustChangePassword: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  // Called by ForcedPasswordChange after a successful POST /auth/change-password
  // — re-fetches the now-unlocked profile and clears mustChangePassword.
  completePasswordChange: () => Promise<void>
}

const AuthContext = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [mustChangePassword, setMustChangePassword] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      getProfile()
        .then(r => { setUser(r.data); setMustChangePassword(false) })
        .catch(err => {
          // /profile/me depends only on get_current_user (no additional
          // require_role/require_permission check), so a 403 here has
          // exactly one possible cause: must_change_password=true. A
          // locked account is still a valid session — keep the tokens,
          // don't log them out, just route to the forced-change screen.
          if (err.response?.status === 403) {
            setMustChangePassword(true)
          } else {
            localStorage.clear()
            setUser(null)
          }
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (username: string, password: string) => {
    const { data } = await apiLogin(username, password)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)

    if (data.must_change_password) {
      // Don't call getProfile() here — it would 403 for the same reason
      // noted above. Nothing else about the account is knowable (or
      // needed) until the password is changed.
      setMustChangePassword(true)
      setUser(null)
      return
    }

    setMustChangePassword(false)
    const profile = await getProfile()
    setUser(profile.data)
  }

  const completePasswordChange = async () => {
    const profile = await getProfile()
    setUser(profile.data)
    setMustChangePassword(false)
  }

  const logout = async () => {
    const refresh = localStorage.getItem('refresh_token')
    if (refresh) await apiLogout(refresh).catch(() => {})
    localStorage.clear()
    setUser(null)
    setMustChangePassword(false)
  }

  return (
    <AuthContext.Provider value={{ user, loading, mustChangePassword, login, logout, completePasswordChange }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
