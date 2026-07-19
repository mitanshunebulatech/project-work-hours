import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Eye, EyeOff, ShieldCheck, BarChart3, Zap } from 'lucide-react'
import NebulaTechIcon from '@/components/NebulaTechIcon'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/misc'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [remember, setRemember] = useState(true)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-background">
      {/* Left panel — brand */}
      <div className="hidden lg:flex flex-col justify-between w-[460px] shrink-0 p-10 relative overflow-hidden bg-nebula-mesh">
        <div className="absolute inset-0 bg-grid opacity-40" />
        <div className="absolute -top-24 -right-24 h-72 w-72 rounded-full bg-nebula-500/30 blur-3xl animate-float-slow" />
        <div className="absolute bottom-0 left-0 h-64 w-64 rounded-full bg-nebula-700/40 blur-3xl animate-float" />

        <div className="relative flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center backdrop-blur">
            <NebulaTechIcon size={20} />
          </div>
          <span className="text-white font-display font-semibold text-base tracking-tight">WorkHours</span>
        </div>

        <div className="relative">
          <p className="text-white font-display text-3xl font-semibold leading-tight mb-4">
            Track time.<br />Stay <span className="text-gradient-brand">accountable.</span>
          </p>
          <p className="text-slate-300 text-sm leading-relaxed max-w-sm mb-8">
            Enterprise-grade timesheet management for teams that care about accuracy, transparency and speed.
          </p>

          <div className="space-y-3">
            {[
              { icon: Zap, text: 'Log hours in seconds, not minutes' },
              { icon: ShieldCheck, text: 'Full audit trail on every change' },
              { icon: BarChart3, text: 'Real-time reporting across projects' },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-3 text-slate-300 text-sm">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-white/10 border border-white/10">
                  <Icon size={13} className="text-nebula-300" />
                </div>
                {text}
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-slate-500 text-xs">© 2026 WorkHours · Nebula Tech</p>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm animate-in fade-in slide-in-from-bottom-2 duration-500">
          {/* Mobile brand mark */}
          <div className="lg:hidden flex items-center gap-2.5 mb-10">
            <div className="w-8 h-8 flex items-center justify-center shrink-0">
              <NebulaTechIcon size={26} />
            </div>
            <span className="font-display font-semibold text-base text-foreground">WorkHours</span>
          </div>

          <div className="rounded-2xl border bg-card shadow-elevated p-8">
            <div className="mb-7">
              <h1 className="text-xl font-display font-semibold text-foreground mb-1">Welcome back</h1>
              <p className="text-sm text-muted-foreground">Sign in to your account to continue</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="Enter username"
                  autoComplete="username"
                  autoFocus
                  required
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <button
                    type="button"
                    onClick={() => setError('Contact your administrator to reset your password')}
                    className="text-xs font-medium text-nebula-600 hover:text-nebula-700"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPw ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="Enter password"
                    autoComplete="current-password"
                    required
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(p => !p)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <label className="flex items-center gap-2 text-sm text-muted-foreground select-none cursor-pointer">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={e => setRemember(e.target.checked)}
                  className="h-3.5 w-3.5 rounded border-input text-nebula-600 focus:ring-nebula-500/40"
                />
                Remember me
              </label>

              {error && (
                <div className="bg-destructive/10 border border-destructive/30 text-destructive text-sm px-3 py-2 rounded-md animate-in fade-in slide-in-from-top-1 duration-200">
                  {error}
                </div>
              )}

              <Button type="submit" className="w-full" size="lg" loading={loading}>
                {loading ? 'Signing in…' : 'Sign in'}
              </Button>
            </form>
          </div>

          <p className="text-center text-xs text-muted-foreground mt-6">
            Contact your administrator if you need access
          </p>
        </div>
      </div>
    </div>
  )
}
