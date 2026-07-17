import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { changePassword } from '@/lib/api'
import { Clock, Eye, EyeOff, ShieldAlert, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/misc'

// PM V2 Part 4: rendered whenever mustChangePassword is true (see
// App.tsx's routing — every other route redirects here regardless of
// what was requested). Deliberately has no "back"/"skip" option; the
// backend enforces the same lock independently (app/core/deps.py
// get_current_user), so this screen is a real gate, not just a UI nudge.
// The only way out besides submitting is logging out, since
// POST /auth/logout stays reachable even while locked.
export default function ForcedPasswordChange() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { completePasswordChange, logout } = useAuth()
  const navigate = useNavigate()

  const passwordMeetsPolicy = (pw: string) => /^(?=.*[A-Za-z])(?=.*\d).{8,}$/.test(pw)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match')
      return
    }
    if (!passwordMeetsPolicy(newPassword)) {
      setError('New password must be at least 8 characters and contain at least one letter and one digit')
      return
    }
    if (newPassword === currentPassword) {
      setError('New password must be different from your current password')
      return
    }

    setLoading(true)
    try {
      await changePassword(currentPassword, newPassword)
      await completePasswordChange()
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to change password')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex bg-background">
      {/* Left panel — mirrors Login.tsx's branding treatment, so this
          doesn't feel like a bare, unstyled interruption screen */}
      <div className="hidden lg:flex flex-col justify-between w-[460px] shrink-0 p-10 relative overflow-hidden bg-nebula-mesh">
        <div className="absolute inset-0 bg-grid opacity-40" />
        <div className="absolute -top-24 -right-24 h-72 w-72 rounded-full bg-nebula-500/30 blur-3xl animate-float-slow" />
        <div className="absolute bottom-0 left-0 h-64 w-64 rounded-full bg-nebula-700/40 blur-3xl animate-float" />

        <div className="relative flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center backdrop-blur">
            <Clock size={16} className="text-white" />
          </div>
          <span className="text-white font-display font-semibold text-base tracking-tight">WorkHours</span>
        </div>

        <div className="relative">
          <p className="text-white font-display text-3xl font-semibold leading-tight mb-4">
            Almost there.<br />Set a <span className="text-gradient-brand">new password.</span>
          </p>
          <p className="text-slate-300 text-sm leading-relaxed max-w-sm">
            This account was set up with a temporary password. Choose a new one to finish securing it.
          </p>
        </div>

        <p className="relative text-slate-500 text-xs">© 2026 WorkHours · Nebula Tech</p>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm animate-in fade-in slide-in-from-bottom-2 duration-500">
          <div className="lg:hidden flex items-center gap-2.5 mb-10">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-nebula-500 to-nebula-700 flex items-center justify-center">
              <Clock size={16} className="text-white" />
            </div>
            <span className="font-display font-semibold text-base text-foreground">WorkHours</span>
          </div>

          <div className="rounded-2xl border bg-card shadow-elevated p-8">
            <div className="mb-7 flex items-start gap-3">
              <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/10">
                <ShieldAlert size={17} className="text-amber-600 dark:text-amber-500" />
              </div>
              <div>
                <h1 className="text-xl font-display font-semibold text-foreground mb-1">Password change required</h1>
                <p className="text-sm text-muted-foreground">Set a new password before continuing.</p>
              </div>
            </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="current-password">Current (temporary) password</Label>
              <div className="relative">
                <Input
                  id="current-password"
                  type={showCurrent ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={e => setCurrentPassword(e.target.value)}
                  autoComplete="current-password"
                  autoFocus
                  required
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrent(p => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showCurrent ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="new-password">New password</Label>
              <div className="relative">
                <Input
                  id="new-password"
                  type={showNew ? 'text' : 'password'}
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowNew(p => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground">At least 8 characters, with a letter and a digit.</p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="confirm-password">Confirm new password</Label>
              <Input
                id="confirm-password"
                type={showNew ? 'text' : 'password'}
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                required
              />
            </div>

            {error && (
              <div className="bg-destructive/10 border border-destructive/30 text-destructive text-sm px-3 py-2 rounded-md animate-in fade-in slide-in-from-top-1 duration-200">
                {error}
              </div>
            )}

            <Button type="submit" className="w-full" size="lg" loading={loading}>
              {loading ? 'Updating…' : 'Set new password'}
            </Button>
          </form>

          <button
            onClick={handleLogout}
            className="w-full mt-4 flex items-center justify-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <LogOut size={12} /> Log out instead
          </button>
        </div>
      </div>
    </div>
  </div>
  )
}
