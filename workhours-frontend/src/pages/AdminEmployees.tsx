import { useEffect, useState } from 'react'
import {
  getEmployees, createEmployeeProfile, updateEmployeeProfile, getDepartments, getUsers,
  onboardEmployee, getRoles,
} from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import {
  Card, CardContent, Badge, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem, Textarea,
} from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { UserAvatar } from '@/components/ui/avatar'
import { TableSkeleton } from '@/components/ui/skeleton'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog'
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem,
} from '@/components/ui/dropdown-menu'
import {
  UserPlus, RefreshCw, Pencil, Users2, ChevronDown, UserCog, Copy, Check,
  Mail, MailX, FileText, KeyRound,
} from 'lucide-react'

const emptyOnboardForm = {
  first_name: '', last_name: '', email: '', personal_phone_number: '', emergency_phone_number: '',
  present_address: '', joining_date: '', birth_date: '', department_id: '', designation: '',
  years_of_experience: '', pan_number: '', role_id: '',
}

const emptyLegacyForm = {
  user_id: '', full_name: '', department_id: '', date_of_birth: '', date_of_joining: '',
  phone_number: '', emergency_contact_phone: '', present_address: '', designation: '',
  years_of_experience: '', pan_number: '',
}

export default function AdminEmployees() {
  const { toast } = useToast()
  const [profiles, setProfiles] = useState<any[]>([])
  const [departments, setDepartments] = useState<any[]>([])
  const [roles, setRoles] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [departmentFilter, setDepartmentFilter] = useState<string>('all')

  // Primary flow: onboard a brand-new employee (creates the User too)
  const [showOnboard, setShowOnboard] = useState(false)
  const [onboardForm, setOnboardForm] = useState(emptyOnboardForm)
  const [onboardErrors, setOnboardErrors] = useState<any>({})
  const [onboarding, setOnboarding] = useState(false)

  // One-time result modal — this is the ONLY place the temp password is
  // ever shown, per EmployeeOnboardingResponse's contract.
  const [onboardResult, setOnboardResult] = useState<any>(null)
  const [copied, setCopied] = useState(false)

  // Secondary/legacy flow: attach a profile to an EXISTING user account,
  // or edit an existing profile (same field set either way)
  const [showLegacy, setShowLegacy] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [legacyForm, setLegacyForm] = useState(emptyLegacyForm)
  const [legacyErrors, setLegacyErrors] = useState<any>({})
  const [legacySubmitting, setLegacySubmitting] = useState(false)

  const errMsg = (err: any, fallback: string) => {
    const detail = err.response?.data?.detail
    if (Array.isArray(detail)) return detail[0]?.msg || fallback
    return detail || fallback
  }

  const load = async (deptFilter = departmentFilter) => {
    setLoading(true)
    try {
      const params: any = { page: 1, size: 100 }
      if (deptFilter !== 'all') params.department_id = Number(deptFilter)
      const [profilesRes, deptsRes, rolesRes] = await Promise.all([
        getEmployees(params),
        getDepartments({ page: 1, size: 100 }),
        getRoles(),
      ])
      setProfiles(profilesRes.data.items)
      setDepartments(deptsRes.data.items)
      setRoles(rolesRes.data)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(departmentFilter) }, [departmentFilter]) // eslint-disable-line react-hooks/exhaustive-deps

  // --- Onboarding (primary) ---

  const openOnboard = () => {
    setOnboardForm(emptyOnboardForm)
    setOnboardErrors({})
    setShowOnboard(true)
  }

  const validateOnboard = () => {
    const e: any = {}
    if (!onboardForm.first_name.trim()) e.first_name = 'Required'
    if (!onboardForm.email.trim()) e.email = 'Required'
    if (!onboardForm.role_id) e.role_id = 'Select a role'
    if (onboardForm.pan_number && !/^[A-Za-z]{5}[0-9]{4}[A-Za-z]$/.test(onboardForm.pan_number.trim()))
      e.pan_number = 'Format: AAAAA9999A (5 letters, 4 digits, 1 letter)'
    setOnboardErrors(e)
    return Object.keys(e).length === 0
  }

  const handleOnboardSubmit = async () => {
    if (!validateOnboard()) return
    setOnboarding(true)
    try {
      const res = await onboardEmployee({
        first_name: onboardForm.first_name,
        last_name: onboardForm.last_name || null,
        email: onboardForm.email,
        personal_phone_number: onboardForm.personal_phone_number || null,
        emergency_phone_number: onboardForm.emergency_phone_number || null,
        present_address: onboardForm.present_address || null,
        joining_date: onboardForm.joining_date || null,
        birth_date: onboardForm.birth_date || null,
        department_id: onboardForm.department_id ? Number(onboardForm.department_id) : null,
        designation: onboardForm.designation || null,
        years_of_experience: onboardForm.years_of_experience ? Number(onboardForm.years_of_experience) : null,
        pan_number: onboardForm.pan_number ? onboardForm.pan_number.trim().toUpperCase() : null,
        role_id: Number(onboardForm.role_id),
      })
      setShowOnboard(false)
      setOnboardResult(res.data)
      setCopied(false)
      load()
    } catch (err: any) {
      toast(errMsg(err, 'Failed to onboard employee'), 'error')
    } finally { setOnboarding(false) }
  }

  const handleCopyPassword = async () => {
    if (!onboardResult?.temp_password) return
    try {
      await navigator.clipboard.writeText(onboardResult.temp_password)
      setCopied(true)
      toast('Password copied')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast('Failed to copy — select and copy manually', 'error')
    }
  }

  // --- Legacy flow (attach-to-existing-user / edit) ---

  const openLegacyCreate = async () => {
    try {
      const res = await getUsers({ page: 1, size: 100 })
      setUsers(res.data.items)
    } catch {
      toast('Failed to load users', 'error')
      return
    }
    setEditingId(null)
    setLegacyForm(emptyLegacyForm)
    setLegacyErrors({})
    setShowLegacy(true)
  }

  const openEdit = (p: any) => {
    setEditingId(p.id)
    setLegacyForm({
      user_id: String(p.user_id),
      full_name: p.full_name || '',
      department_id: p.department_id ? String(p.department_id) : '',
      date_of_birth: p.date_of_birth || '',
      date_of_joining: p.date_of_joining || '',
      phone_number: p.phone_number || '',
      emergency_contact_phone: p.emergency_contact_phone || '',
      present_address: p.present_address || '',
      designation: p.designation || '',
      years_of_experience: p.years_of_experience != null ? String(p.years_of_experience) : '',
      pan_number: '', // write-only — always blank on open, backend only ever returns the masked value
    })
    setLegacyErrors({})
    setShowLegacy(true)
  }

  const validateLegacy = () => {
    const e: any = {}
    if (!editingId && !legacyForm.user_id) e.user_id = 'Select a user to onboard'
    if (!legacyForm.full_name.trim()) e.full_name = 'Required'
    if (legacyForm.pan_number && !/^[A-Za-z]{5}[0-9]{4}[A-Za-z]$/.test(legacyForm.pan_number.trim()))
      e.pan_number = 'Format: AAAAA9999A (5 letters, 4 digits, 1 letter)'
    setLegacyErrors(e)
    return Object.keys(e).length === 0
  }

  const buildLegacyPayload = () => ({
    full_name: legacyForm.full_name,
    department_id: legacyForm.department_id ? Number(legacyForm.department_id) : null,
    date_of_birth: legacyForm.date_of_birth || null,
    date_of_joining: legacyForm.date_of_joining || null,
    phone_number: legacyForm.phone_number || null,
    emergency_contact_phone: legacyForm.emergency_contact_phone || null,
    present_address: legacyForm.present_address || null,
    designation: legacyForm.designation || null,
    years_of_experience: legacyForm.years_of_experience ? Number(legacyForm.years_of_experience) : null,
    // Blank means "leave unchanged" on edit; on create an empty PAN is just omitted.
    ...(legacyForm.pan_number ? { pan_number: legacyForm.pan_number.trim().toUpperCase() } : {}),
  })

  const handleLegacySubmit = async () => {
    if (!validateLegacy()) return
    setLegacySubmitting(true)
    try {
      if (editingId) {
        await updateEmployeeProfile(editingId, buildLegacyPayload())
        toast('Employee profile updated')
      } else {
        await createEmployeeProfile({ user_id: Number(legacyForm.user_id), ...buildLegacyPayload() })
        toast('Employee profile created')
      }
      setShowLegacy(false)
      load()
    } catch (err: any) {
      toast(errMsg(err, 'Failed to save employee profile'), 'error')
    } finally { setLegacySubmitting(false) }
  }

  const departmentName = (id: number | null) => departments.find(d => d.id === id)?.name || '—'

  return (
    <div className="p-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">Employees</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Employee profiles, department assignment, and HR-of-record data
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={departmentFilter} onValueChange={setDepartmentFilter}>
            <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All departments</SelectItem>
              {departments.map(d => (
                <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={() => load()}><RefreshCw size={14} /></Button>
          <Button size="sm" onClick={openOnboard}><UserPlus size={14} /> Onboard Employee</Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm" variant="outline"><ChevronDown size={14} /></Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={openLegacyCreate}>
                <UserCog size={14} /> Attach Profile to Existing User
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <TableSkeleton rows={5} cols={6} />
          ) : profiles.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <Users2 size={28} className="mx-auto text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground">No employee profiles yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/40">
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Employee</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">ID</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Department</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Designation</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Phone</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Documents</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {profiles.map((p: any) => (
                    <tr key={p.id} className="border-b last:border-0 hover:bg-muted/40 transition-colors">
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-3">
                          <UserAvatar name={p.full_name} size={30} />
                          <span className="font-medium text-foreground">{p.full_name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-3.5 text-muted-foreground font-mono text-xs">{p.employee_code || '—'}</td>
                      <td className="px-6 py-3.5 text-muted-foreground">{departmentName(p.department_id)}</td>
                      <td className="px-6 py-3.5 text-muted-foreground">{p.designation || '—'}</td>
                      <td className="px-6 py-3.5 text-muted-foreground">{p.phone_number || '—'}</td>
                      <td className="px-6 py-3.5">
                        {p.identity_documents?.length > 0 ? (
                          <Badge variant="outline" className="gap-1">
                            <FileText size={11} /> {p.identity_documents.length}
                          </Badge>
                        ) : <span className="text-muted-foreground text-xs">None</span>}
                      </td>
                      <td className="px-6 py-3.5 text-right">
                        <button onClick={() => openEdit(p)} className="text-muted-foreground hover:text-foreground transition-colors" title="Edit">
                          <Pencil size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Primary: Onboard a new employee */}
      <Dialog open={showOnboard} onOpenChange={(open: boolean) => { if (!open) setShowOnboard(false) }}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Onboard Employee</DialogTitle>
            <DialogDescription>
              Creates a login account, generates a temporary password, assigns the role and
              department, and creates their employee profile — all in one step.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>First Name <span className="text-destructive">*</span></Label>
                <Input value={onboardForm.first_name} onChange={e => setOnboardForm(f => ({ ...f, first_name: e.target.value }))} />
                {onboardErrors.first_name && <p className="text-xs text-destructive">{onboardErrors.first_name}</p>}
              </div>
              <div className="space-y-1.5">
                <Label>Last Name</Label>
                <Input value={onboardForm.last_name} onChange={e => setOnboardForm(f => ({ ...f, last_name: e.target.value }))} />
              </div>
              <div className="space-y-1.5 col-span-2">
                <Label>Email <span className="text-destructive">*</span></Label>
                <Input type="email" value={onboardForm.email} onChange={e => setOnboardForm(f => ({ ...f, email: e.target.value }))} />
                {onboardErrors.email && <p className="text-xs text-destructive">{onboardErrors.email}</p>}
              </div>
              <div className="space-y-1.5">
                <Label>Role <span className="text-destructive">*</span></Label>
                <Select value={onboardForm.role_id} onValueChange={v => setOnboardForm(f => ({ ...f, role_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
                  <SelectContent>
                    {roles.map(r => <SelectItem key={r.id} value={String(r.id)}>{r.name}</SelectItem>)}
                  </SelectContent>
                </Select>
                {onboardErrors.role_id && <p className="text-xs text-destructive">{onboardErrors.role_id}</p>}
              </div>
              <div className="space-y-1.5">
                <Label>Department</Label>
                <Select value={onboardForm.department_id || 'none'} onValueChange={v => setOnboardForm(f => ({ ...f, department_id: v === 'none' ? '' : v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Unassigned</SelectItem>
                    {departments.map(d => (
                      <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Designation</Label>
                <Input value={onboardForm.designation} onChange={e => setOnboardForm(f => ({ ...f, designation: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Years of Experience</Label>
                <Input type="number" min="0" step="0.5" value={onboardForm.years_of_experience}
                  onChange={e => setOnboardForm(f => ({ ...f, years_of_experience: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Personal Phone</Label>
                <Input value={onboardForm.personal_phone_number} onChange={e => setOnboardForm(f => ({ ...f, personal_phone_number: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Emergency Phone</Label>
                <Input value={onboardForm.emergency_phone_number} onChange={e => setOnboardForm(f => ({ ...f, emergency_phone_number: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Joining Date</Label>
                <Input type="date" value={onboardForm.joining_date} onChange={e => setOnboardForm(f => ({ ...f, joining_date: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Birth Date</Label>
                <Input type="date" value={onboardForm.birth_date} onChange={e => setOnboardForm(f => ({ ...f, birth_date: e.target.value }))} />
              </div>
              <div className="space-y-1.5 col-span-2">
                <Label>Present Address</Label>
                <Textarea rows={2} value={onboardForm.present_address} onChange={e => setOnboardForm(f => ({ ...f, present_address: e.target.value }))} />
              </div>
              <div className="space-y-1.5 col-span-2">
                <Label>PAN</Label>
                <Input placeholder="AAAAA9999A" value={onboardForm.pan_number}
                  onChange={e => setOnboardForm(f => ({ ...f, pan_number: e.target.value.toUpperCase() }))} />
                {onboardErrors.pan_number && <p className="text-xs text-destructive">{onboardErrors.pan_number}</p>}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setShowOnboard(false)}>Cancel</Button>
            <Button size="sm" onClick={handleOnboardSubmit} loading={onboarding}>Onboard Employee</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* One-time temp password result — this is the ONLY place it's ever shown */}
      <Dialog open={!!onboardResult} onOpenChange={(open: boolean) => { if (!open) setOnboardResult(null) }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Check size={16} className="text-emerald-600" /> Employee Onboarded
            </DialogTitle>
          </DialogHeader>
          {onboardResult && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm">
                {onboardResult.email_sent ? (
                  <><Mail size={14} className="text-emerald-600" /> <span className="text-foreground">Welcome email sent to {onboardResult.email}</span></>
                ) : (
                  <><MailX size={14} className="text-amber-600" /> <span className="text-foreground">Email not sent (no mail provider configured) — share these credentials directly</span></>
                )}
              </div>

              <div className="rounded-lg border bg-muted/30 p-3 space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-muted-foreground">Username</span><span className="font-mono text-foreground">{onboardResult.username}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Employee ID</span><span className="font-mono text-foreground">{onboardResult.employee_code}</span></div>
              </div>

              <div className="rounded-lg border border-amber-200 bg-amber-500/10 p-3">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <KeyRound size={13} className="text-amber-600" />
                  <span className="text-xs font-medium text-foreground">Temporary Password — shown once only</span>
                </div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-background rounded border px-2.5 py-1.5 text-sm font-mono text-foreground select-all">
                    {onboardResult.temp_password}
                  </code>
                  <Button size="sm" variant="outline" onClick={handleCopyPassword}>
                    {copied ? <Check size={13} /> : <Copy size={13} />}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  This won't be shown again after you close this dialog. The employee will be
                  required to set a new password on first login.
                </p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button size="sm" onClick={() => setOnboardResult(null)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Secondary/legacy: attach to existing user, or edit an existing profile */}
      <Dialog open={showLegacy} onOpenChange={(open: boolean) => { if (!open) setShowLegacy(false) }}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingId ? 'Edit Employee Profile' : 'Attach Profile to Existing User'}</DialogTitle>
            {!editingId && (
              <DialogDescription>
                For accounts created before the onboarding flow existed. For new hires, use
                "Onboard Employee" instead — it creates the login account for you.
              </DialogDescription>
            )}
          </DialogHeader>
          <div className="space-y-4">
            {!editingId && (
              <div className="space-y-1.5">
                <Label>User Account <span className="text-destructive">*</span></Label>
                <Select value={legacyForm.user_id} onValueChange={v => setLegacyForm(f => ({ ...f, user_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="Select a user..." /></SelectTrigger>
                  <SelectContent>
                    {users.map(u => (
                      <SelectItem key={u.id} value={String(u.id)}>{u.username}{u.email ? ` · ${u.email}` : ''}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {legacyErrors.user_id && <p className="text-xs text-destructive">{legacyErrors.user_id}</p>}
              </div>
            )}
            <div className="space-y-1.5">
              <Label>Full Name <span className="text-destructive">*</span></Label>
              <Input value={legacyForm.full_name} onChange={e => setLegacyForm(f => ({ ...f, full_name: e.target.value }))} />
              {legacyErrors.full_name && <p className="text-xs text-destructive">{legacyErrors.full_name}</p>}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Department</Label>
                <Select value={legacyForm.department_id || 'none'} onValueChange={v => setLegacyForm(f => ({ ...f, department_id: v === 'none' ? '' : v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Unassigned</SelectItem>
                    {departments.map(d => (
                      <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Designation</Label>
                <Input value={legacyForm.designation} onChange={e => setLegacyForm(f => ({ ...f, designation: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Date of Birth</Label>
                <Input type="date" value={legacyForm.date_of_birth} onChange={e => setLegacyForm(f => ({ ...f, date_of_birth: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Date of Joining</Label>
                <Input type="date" value={legacyForm.date_of_joining} onChange={e => setLegacyForm(f => ({ ...f, date_of_joining: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Phone Number</Label>
                <Input value={legacyForm.phone_number} onChange={e => setLegacyForm(f => ({ ...f, phone_number: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Emergency Phone</Label>
                <Input value={legacyForm.emergency_contact_phone} onChange={e => setLegacyForm(f => ({ ...f, emergency_contact_phone: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Years of Experience</Label>
                <Input type="number" min="0" step="0.5" value={legacyForm.years_of_experience}
                  onChange={e => setLegacyForm(f => ({ ...f, years_of_experience: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>PAN {editingId && <span className="text-muted-foreground font-normal">(leave blank to keep unchanged)</span>}</Label>
                <Input placeholder="AAAAA9999A" value={legacyForm.pan_number}
                  onChange={e => setLegacyForm(f => ({ ...f, pan_number: e.target.value.toUpperCase() }))} />
                {legacyErrors.pan_number && <p className="text-xs text-destructive">{legacyErrors.pan_number}</p>}
              </div>
              <div className="space-y-1.5 col-span-2">
                <Label>Present Address</Label>
                <Textarea rows={2} value={legacyForm.present_address} onChange={e => setLegacyForm(f => ({ ...f, present_address: e.target.value }))} />
              </div>
            </div>

            {editingId && profiles.find(p => p.id === editingId)?.identity_documents?.length > 0 && (
              <div className="pt-2 border-t">
                <p className="text-xs font-medium text-muted-foreground mb-2">
                  Identity Documents <span className="font-normal">(view-only — uploaded by the employee)</span>
                </p>
                <div className="space-y-1.5">
                  {profiles.find(p => p.id === editingId)?.identity_documents.map((d: any) => (
                    <div key={d.id} className="flex items-center gap-2 text-xs text-muted-foreground">
                      <FileText size={12} />
                      <span className="text-foreground">{d.document_type}</span>
                      {d.document_number_masked && <span>· {d.document_number_masked}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setShowLegacy(false)}>Cancel</Button>
            <Button size="sm" onClick={handleLegacySubmit} loading={legacySubmitting}>
              {editingId ? 'Save Changes' : 'Create Profile'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
