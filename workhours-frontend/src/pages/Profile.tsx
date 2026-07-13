import { useEffect, useState } from 'react'
import { getProfile, updateProfile, getDepartments } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, CardHeader, CardTitle, Badge, Label } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { UserAvatar } from '@/components/ui/avatar'
import { EmptyState } from '@/components/ui/empty-state'
import { UserCircle, Save } from 'lucide-react'

export default function Profile() {
  const { toast } = useToast()
  const [profile, setProfile] = useState<any>(null)
  const [departments, setDepartments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ phone_number: '', date_of_birth: '', pan_number: '' })
  const [errors, setErrors] = useState<any>({})

  const load = async () => {
    setLoading(true)
    try {
      const [profileRes, deptsRes] = await Promise.all([
        getProfile(),
        getDepartments({ page: 1, size: 100 }),
      ])
      setProfile(profileRes.data)
      setDepartments(deptsRes.data.items)
      setForm({
        phone_number: profileRes.data.phone_number || '',
        date_of_birth: profileRes.data.date_of_birth || '',
        pan_number: '', // write-only — the API only ever returns a masked value, never the real one
      })
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const validate = () => {
    const e: any = {}
    if (form.pan_number && !/^[A-Za-z]{5}[0-9]{4}[A-Za-z]$/.test(form.pan_number.trim()))
      e.pan_number = 'Format: AAAAA9999A (5 letters, 4 digits, 1 letter)'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSave = async () => {
    if (!validate()) return
    setSaving(true)
    try {
      await updateProfile({
        phone_number: form.phone_number || null,
        date_of_birth: form.date_of_birth || null,
        ...(form.pan_number ? { pan_number: form.pan_number.trim().toUpperCase() } : {}),
      })
      toast('Profile updated')
      load()
    } catch (err: any) {
      const msg = err.response?.data?.detail
      toast(Array.isArray(msg) ? msg[0]?.msg : (msg || 'Failed to update profile'), 'error')
    } finally { setSaving(false) }
  }

  const departmentName = (id: number | null) => departments.find(d => d.id === id)?.name

  if (loading) {
    return (
      <div className="p-8 max-w-2xl">
        <div className="h-8 w-40 bg-muted rounded animate-pulse mb-6" />
        <div className="h-64 bg-muted rounded-xl animate-pulse" />
      </div>
    )
  }

  // A user account can exist before HR has created an EmployeeProfile row for
  // them (Sprint 2, FR-E08) — that's a normal state, not an error, so this
  // isn't a blocking screen. Self-service fields (phone/DOB/PAN) still can't
  // be saved until a profile exists, since PATCH /profile/me updates an
  // existing row rather than creating one — onboarding is admin-initiated
  // via Admin → Employees.
  const hasProfile = profile?.full_name !== null && profile?.full_name !== undefined

  return (
    <div className="p-8 max-w-2xl">
      <div className="flex items-center gap-4 mb-6">
        <UserAvatar name={profile?.full_name || profile?.username} size={48} />
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">
            {profile?.full_name || profile?.username}
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {profile?.username} · <span className="capitalize">{profile?.role}</span>
          </p>
        </div>
      </div>

      {!hasProfile ? (
        <Card>
          <EmptyState
            icon={UserCircle}
            title="No employee profile yet"
            description="HR hasn't set up your employee profile yet — department, designation, and other details will appear here once it's created."
          />
        </Card>
      ) : (
        <>
          <Card className="mb-4">
            <CardHeader className="pb-3"><CardTitle>Organization Details</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Department</p>
                <p className="text-sm text-foreground">{departmentName(profile?.department_id) || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Designation</p>
                <p className="text-sm text-foreground">{profile?.designation || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Date of Joining</p>
                <p className="text-sm text-foreground">{profile?.date_of_joining || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">PAN</p>
                {profile?.pan_number_masked
                  ? <Badge variant="outline">{profile.pan_number_masked}</Badge>
                  : <p className="text-sm text-muted-foreground">Not set</p>}
              </div>
              <p className="col-span-2 text-xs text-muted-foreground/70 -mt-2">
                Managed by HR/admin — contact an administrator to change these.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3"><CardTitle>Personal Details</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label>Phone Number</Label>
                  <Input value={form.phone_number} onChange={e => setForm(f => ({ ...f, phone_number: e.target.value }))} />
                </div>
                <div className="space-y-1.5">
                  <Label>Date of Birth</Label>
                  <Input type="date" value={form.date_of_birth} onChange={e => setForm(f => ({ ...f, date_of_birth: e.target.value }))} />
                </div>
                <div className="space-y-1.5 col-span-2">
                  <Label>PAN <span className="text-muted-foreground font-normal">(leave blank to keep unchanged)</span></Label>
                  <Input placeholder="AAAAA9999A" value={form.pan_number}
                    onChange={e => setForm(f => ({ ...f, pan_number: e.target.value.toUpperCase() }))} />
                  {errors.pan_number && <p className="text-xs text-destructive">{errors.pan_number}</p>}
                  <p className="text-xs text-muted-foreground/70">
                    Every change is logged for compliance — the previous value is never shown again once saved.
                  </p>
                </div>
              </div>
              <Button size="sm" onClick={handleSave} loading={saving}>
                <Save size={14} /> Save Changes
              </Button>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
