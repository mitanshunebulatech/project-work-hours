import { useEffect, useState } from 'react'
import { getUsers, createUser, updateUser } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, CardHeader, CardTitle, Badge, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Plus, RefreshCw, ToggleLeft, ToggleRight } from 'lucide-react'

export default function AdminUsers() {
  const { toast } = useToast()
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'employee' })
  const [errors, setErrors] = useState<any>({})

  const load = async () => {
    setLoading(true)
    try {
      const res = await getUsers({ page: 1, size: 100 })
      setUsers(res.data.items)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const validate = () => {
    const e: any = {}
    if (!form.username) e.username = 'Required'
    if (!form.password) e.password = 'Required'
    if (form.password && !/(?=.*[A-Za-z])(?=.*\d).{8,}/.test(form.password))
      e.password = 'Min 8 chars, one letter and one number'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleCreate = async () => {
    if (!validate()) return
    setSubmitting(true)
    try {
      await createUser({ ...form, email: form.email || null })
      toast('User created successfully')
      setShowForm(false)
      setForm({ username: '', email: '', password: '', role: 'employee' })
      load()
    } catch (err: any) {
      const msg = err.response?.data?.detail
      toast(Array.isArray(msg) ? msg[0]?.msg : (msg || 'Failed to create user'), 'error')
    } finally { setSubmitting(false) }
  }

  const handleToggleActive = async (user: any) => {
    try {
      await updateUser(user.id, { is_active: !user.is_active })
      toast(`User ${user.is_active ? 'deactivated' : 'activated'}`)
      load()
    } catch (err: any) {
      toast(err.response?.data?.detail || 'Failed to update user', 'error')
    }
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Users</h1>
          <p className="text-sm text-slate-500 mt-0.5">Manage employee and admin accounts</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
          <Button size="sm" onClick={() => setShowForm(true)}><Plus size={14} /> Add User</Button>
        </div>
      </div>

      {showForm && (
        <Card className="mb-6 border-blue-200">
          <CardHeader className="pb-3"><CardTitle>Create New User</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Username <span className="text-red-500">*</span></Label>
                <Input placeholder="e.g. john.doe" value={form.username}
                  onChange={e => setForm(f => ({ ...f, username: e.target.value }))} />
                {errors.username && <p className="text-xs text-red-500">{errors.username}</p>}
              </div>
              <div className="space-y-1.5">
                <Label>Email</Label>
                <Input type="email" placeholder="john@company.com" value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Password <span className="text-red-500">*</span></Label>
                <Input type="password" placeholder="Min 8 chars, letter + number" value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
                {errors.password && <p className="text-xs text-red-500">{errors.password}</p>}
              </div>
              <div className="space-y-1.5">
                <Label>Role</Label>
                <Select value={form.role} onValueChange={v => setForm(f => ({ ...f, role: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="employee">Employee</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <Button size="sm" onClick={handleCreate} disabled={submitting}>
                {submitting ? 'Creating...' : 'Create User'}
              </Button>
              <Button size="sm" variant="outline" onClick={() => { setShowForm(false); setErrors({}) }}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-3">
              {[1,2,3].map(i => <div key={i} className="h-12 bg-slate-100 rounded animate-pulse" />)}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-slate-50">
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">User</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">Email</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">Role</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">Status</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u: any) => (
                  <tr key={u.id} className="border-b last:border-0 hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 text-xs font-bold">
                          {u.username[0].toUpperCase()}
                        </div>
                        <span className="font-medium text-slate-900">{u.username}</span>
                      </div>
                    </td>
                    <td className="px-6 py-3.5 text-slate-500">{u.email || '—'}</td>
                    <td className="px-6 py-3.5">
                      <Badge variant={u.role === 'admin' ? 'default' : 'secondary'}>{u.role}</Badge>
                    </td>
                    <td className="px-6 py-3.5">
                      <Badge variant={u.is_active ? 'success' : 'outline'}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <button
                        onClick={() => handleToggleActive(u)}
                        className={`transition-colors ${u.is_active ? 'text-emerald-500 hover:text-red-500' : 'text-slate-400 hover:text-emerald-500'}`}
                        title={u.is_active ? 'Deactivate' : 'Activate'}
                      >
                        {u.is_active ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
