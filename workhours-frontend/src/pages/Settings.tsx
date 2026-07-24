import { useEffect, useState } from 'react'
import { useTheme } from '@/hooks/useTheme'
import { useToast } from '@/hooks/useToast'
import { getMyPreferences, updateMyPreferences, changePassword } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Sun, Moon, Check } from 'lucide-react'

// A practical subset, not every IANA zone — covers this org's likely
// spread without turning the picker into an unscrollable 400-item list.
const TIMEZONES = [
  'UTC', 'Asia/Kolkata', 'Asia/Dubai', 'Asia/Singapore', 'Asia/Tokyo',
  'Europe/London', 'Europe/Berlin', 'America/New_York', 'America/Chicago',
  'America/Los_Angeles', 'Australia/Sydney',
]

export default function Settings() {
  const { theme, toggle } = useTheme()
  const { toast } = useToast()

  const [timezone, setTimezone] = useState('UTC')
  const [emailNotifications, setEmailNotifications] = useState(true)
  const [loading, setLoading] = useState(true)
  const [savingPrefs, setSavingPrefs] = useState(false)

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [changingPassword, setChangingPassword] = useState(false)

  useEffect(() => {
    getMyPreferences()
      .then(res => {
        setTimezone(res.data.timezone)
        setEmailNotifications(res.data.email_notifications_enabled)
      })
      .catch(() => toast('Failed to load preferences', 'error'))
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const savePreferences = async (next: { timezone?: string; email_notifications_enabled?: boolean }) => {
    setSavingPrefs(true)
    try {
      await updateMyPreferences(next)
      toast('Preferences saved')
    } catch (err: any) {
      toast(err.response?.data?.detail || 'Failed to save preferences', 'error')
    } finally {
      setSavingPrefs(false)
    }
  }

  const handleTimezoneChange = (value: string) => {
    setTimezone(value)
    savePreferences({ timezone: value })
  }

  const handleNotificationsToggle = () => {
    const next = !emailNotifications
    setEmailNotifications(next)
    savePreferences({ email_notifications_enabled: next })
  }

  const handleChangePassword = async () => {
    setPasswordError('')
    if (newPassword.length < 8) { setPasswordError('New password must be at least 8 characters'); return }
    if (newPassword !== confirmPassword) { setPasswordError('Passwords do not match'); return }
    setChangingPassword(true)
    try {
      await changePassword(currentPassword, newPassword)
      toast('Password changed')
      setCurrentPassword(''); setNewPassword(''); setConfirmPassword('')
    } catch (err: any) {
      setPasswordError(err.response?.data?.detail || 'Failed to change password')
    } finally {
      setChangingPassword(false)
    }
  }

  return (
    <div className="p-8 max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-display font-semibold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage your appearance and account preferences.</p>
      </div>

      <Card>
        <CardHeader className="pb-3"><CardTitle>Appearance</CardTitle></CardHeader>
        <CardContent className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-foreground">Theme</p>
            <p className="text-xs text-muted-foreground mt-0.5">Switch between light and dark mode.</p>
          </div>
          <Button variant="outline" size="sm" onClick={toggle}>
            {theme === 'dark' ? <Moon size={14} /> : <Sun size={14} />}
            {theme === 'dark' ? 'Dark' : 'Light'}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3"><CardTitle>Account</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5 max-w-xs">
            <Label>Timezone</Label>
            <Select value={timezone} onValueChange={handleTimezoneChange} disabled={loading || savingPrefs}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {TIMEZONES.map(tz => <SelectItem key={tz} value={tz}>{tz}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between pt-2">
            <div>
              <p className="text-sm font-medium text-foreground">Email Notifications</p>
              <p className="text-xs text-muted-foreground mt-0.5">Receive email updates for leave approvals and onboarding.</p>
            </div>
            <Button
              variant={emailNotifications ? 'default' : 'outline'} size="sm"
              onClick={handleNotificationsToggle} disabled={loading || savingPrefs}
            >
              {emailNotifications && <Check size={14} />} {emailNotifications ? 'Enabled' : 'Disabled'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3"><CardTitle>Change Password</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>Current Password</Label>
            <Input type="password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>New Password</Label>
            <Input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Confirm New Password</Label>
            <Input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} />
          </div>
          {passwordError && <p className="text-xs text-destructive">{passwordError}</p>}
          <Button size="sm" onClick={handleChangePassword} loading={changingPassword}>Update Password</Button>
        </CardContent>
      </Card>
    </div>
  )
}
