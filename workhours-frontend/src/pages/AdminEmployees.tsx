import { useEffect, useState } from 'react'
import {
  getEmployees, createEmployeeProfile, updateEmployeeProfile, getDepartments, getUsers,
} from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import {
  Card, CardContent, Badge, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { UserAvatar } from '@/components/ui/avatar'
import { TableSkeleton } from '@/components/ui/skeleton'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import { UserPlus, RefreshCw, Pencil, Users2 } from 'lucide-react'

const emptyForm = {
  user_id: '', full_name: '', department_id: '', date_of_birth: '', date_of_joining: '',
  phone_number: '', designation: '', pan_number: '',
}

export default function AdminEmployees() {
  const { toast } = useToast()
  const [profiles, setProfiles] = useState<any[]>([])
  const [departments, setDepartments] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [departmentFilter, setDepartmentFilter] = useState<string>('all')
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [errors, setErrors] = useState<any>({})

  const load = async (deptFilter = departmentFilter) => {
    setLoading(true)
    try {
      const params: any = { page: 1, size: 100 }
      if (deptFilter !== 'all') params.department_id = Number(deptFilter)
      const [profilesRes, deptsRes] = await Promise.all([
        getEmployees(params),
        getDepartments({ page: 1, size: 100 }),
      ])
      setProfiles(profilesRes.data.items)
      setDepartments(deptsRes.data.items)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(departmentFilter) }, [departmentFilter]) // eslint-disable-line react-hooks/exhaustive-deps

  const resetForm = () => {
    setShowForm(false); setEditingId(null); setForm(emptyForm); setErrors({})
  }

  const openCreate = async () => {
    // Onboarding needs a list of users who don't yet have a profile —
    // the backend doesn't filter this for us, so fetch a page of users and
    // let the admin pick; the API will 409 if the chosen user already has one.
    try {
      const res = await getUsers({ page: 1, size: 100 })
      setUsers(res.data.items)
    } catch {
      toast('Failed to load users', 'error')
      return
    }
    resetForm()
    setShowForm(true)
  }

  const openEdit = (p: any) => {
    setEditingId(p.id)
    setForm({
      user_id: String(p.user_id),
      full_name: p.full_name || '',
      department_id: p.department_id ? String(p.department_id) : '',
      date_of_birth: p.date_of_birth || '',
      date_of_joining: p.date_of_joining || '',
      phone_number: p.phone_number || '',
      designation: p.designation || '',
      pan_number: '', // write-only — always blank on open, backend only ever returns the masked value
    })
    setErrors({})
    setShowForm(true)
  }

  const validate = () => {
    const e: any = {}
    if (!editingId && !form.user_id) e.user_id = 'Select a user to onboard'
    if (!form.full_name.trim()) e.full_name = 'Required'
    if (form.pan_number && !/^[A-Za-z]{5}[0-9]{4}[A-Za-z]$/.test(form.pan_number.trim()))
      e.pan_number = 'Format: AAAAA9999A (5 letters, 4 digits, 1 letter)'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const buildPayload = () => ({
    full_name: form.full_name,
    department_id: form.department_id ? Number(form.department_id) : null,
    date_of_birth: form.date_of_birth || null,
    date_of_joining: form.date_of_joining || null,
    phone_number: form.phone_number || null,
    designation: form.designation || null,
    // Blank means "leave unchanged" on edit; on create an empty PAN is just omitted.
    ...(form.pan_number ? { pan_number: form.pan_number.trim().toUpperCase() } : {}),
  })

  const handleSubmit = async () => {
    if (!validate()) return
    setSubmitting(true)
    try {
      if (editingId) {
        await updateEmployeeProfile(editingId, buildPayload())
        toast('Employee profile updated')
      } else {
        await createEmployeeProfile({ user_id: Number(form.user_id), ...buildPayload() })
        toast('Employee profile created')
      }
      resetForm()
      load()
    } catch (err: any) {
      const msg = err.response?.data?.detail
      toast(Array.isArray(msg) ? msg[0]?.msg : (msg || 'Failed to save employee profile'), 'error')
    } finally { setSubmitting(false) }
  }

  const departmentName = (id: number | null) => departments.find(d => d.id === id)?.name || '—'

  return (
    <div className="p-8 max-w-5xl">
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
          <Button size="sm" onClick={openCreate}><UserPlus size={14} /> Onboard Employee</Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <TableSkeleton rows={5} cols={5} />
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
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Department</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Designation</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Phone</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">PAN</th>
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
                      <td className="px-6 py-3.5 text-muted-foreground">{departmentName(p.department_id)}</td>
                      <td className="px-6 py-3.5 text-muted-foreground">{p.designation || '—'}</td>
                      <td className="px-6 py-3.5 text-muted-foreground">{p.phone_number || '—'}</td>
                      <td className="px-6 py-3.5">
                        {p.pan_number_masked ? <Badge variant="outline">{p.pan_number_masked}</Badge> : '—'}
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

      <Dialog open={showForm} onOpenChange={(open: boolean) => { if (!open) resetForm() }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingId ? 'Edit Employee Profile' : 'Onboard Employee'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {!editingId && (
              <div className="space-y-1.5">
                <Label>User Account <span className="text-destructive">*</span></Label>
                <Select value={form.user_id} onValueChange={v => setForm(f => ({ ...f, user_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="Select a user..." /></SelectTrigger>
                  <SelectContent>
                    {users.map(u => (
                      <SelectItem key={u.id} value={String(u.id)}>{u.username}{u.email ? ` · ${u.email}` : ''}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.user_id && <p className="text-xs text-destructive">{errors.user_id}</p>}
              </div>
            )}
            <div className="space-y-1.5">
              <Label>Full Name <span className="text-destructive">*</span></Label>
              <Input value={form.full_name} onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))} />
              {errors.full_name && <p className="text-xs text-destructive">{errors.full_name}</p>}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Department</Label>
                <Select value={form.department_id || 'none'} onValueChange={v => setForm(f => ({ ...f, department_id: v === 'none' ? '' : v }))}>
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
                <Input value={form.designation} onChange={e => setForm(f => ({ ...f, designation: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Date of Birth</Label>
                <Input type="date" value={form.date_of_birth} onChange={e => setForm(f => ({ ...f, date_of_birth: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Date of Joining</Label>
                <Input type="date" value={form.date_of_joining} onChange={e => setForm(f => ({ ...f, date_of_joining: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Phone Number</Label>
                <Input value={form.phone_number} onChange={e => setForm(f => ({ ...f, phone_number: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>PAN {editingId && <span className="text-muted-foreground font-normal">(leave blank to keep unchanged)</span>}</Label>
                <Input placeholder="AAAAA9999A" value={form.pan_number}
                  onChange={e => setForm(f => ({ ...f, pan_number: e.target.value.toUpperCase() }))} />
                {errors.pan_number && <p className="text-xs text-destructive">{errors.pan_number}</p>}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={resetForm}>Cancel</Button>
            <Button size="sm" onClick={handleSubmit} loading={submitting}>
              {editingId ? 'Save Changes' : 'Create Profile'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
