import { useEffect, useState } from 'react'
import { getUsers, createUser, updateUser, getRoles } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, CardHeader, CardTitle, Badge, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { UserAvatar } from '@/components/ui/avatar'
import { TableSkeleton } from '@/components/ui/skeleton'
import { Plus, RefreshCw, ToggleLeft, ToggleRight, Users } from 'lucide-react'

export default function AdminUsers() {
  const { toast } = useToast()
  const [users, setUsers] = useState<any[]>([])
  const [roles, setRoles] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'employee' })
  const [errors, setErrors] = useState<any>({})

  const load = async () => {
    setLoading(true)
    try {
      const [usersRes, rolesRes] = await Promise.all([getUsers({ page: 1, size: 100 }), getRoles()])
      setUsers(usersRes.data.items)
      setRoles(rolesRes.data)
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

  const activeCount = users.filter(u => u.is_active).length

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">User Accounts</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage employee and admin accounts · <span className="font-medium text-foreground">{activeCount}</span> active
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
          <Button size="sm" onClick={() => setShowForm(true)}><Plus size={14} /> Add User</Button>
        </div>
      </div>

      {showForm && (
        <Card className="mb-6 border-nebula-200 shadow-elevated animate-in fade-in slide-in-from-top-1 duration-200">
          <CardHeader className="pb-3"><CardTitle>Create New User</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Username <span className="text-destructive">*</span></Label>
                <Input placeholder="e.g. john.doe" value={form.username}
                  onChange={e => setForm(f => ({ ...f, username: e.target.value }))} />
                {errors.username && <p className="text-xs text-destructive">{errors.username}</p>}
              </div>
              <div className="space-y-1.5">
                <Label>Email</Label>
                <Input type="email" placeholder="john@company.com" value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Password <span className="text-destructive">*</span></Label>
                <Input type="password" placeholder="Min 8 chars, letter + number" value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
                {errors.password && <p className="text-xs text-destructive">{errors.password}</p>}
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
              <Button size="sm" onClick={handleCreate} loading={submitting}>Create User</Button>
              <Button size="sm" variant="outline" onClick={() => { setShowForm(false); setErrors({}) }}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <TableSkeleton rows={5} cols={5} />
          ) : users.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <Users size={28} className="mx-auto text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground">No users yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/40">
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">User</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Email</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Role</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Custom Role</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Status</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u: any) => (
                    <tr key={u.id} className="border-b last:border-0 hover:bg-muted/40 transition-colors">
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-3">
                          <UserAvatar name={u.username} size={30} />
                          <span className="font-medium text-foreground">{u.username}</span>
                        </div>
                      </td>
                      <td className="px-6 py-3.5 text-muted-foreground">{u.email || '—'}</td>
                      <td className="px-6 py-3.5">
                        <Badge variant={u.role === 'admin' ? 'default' : 'secondary'}>{u.role}</Badge>
                      </td>
                      <td className="px-6 py-3.5">
                        <Select
                          value={u.role_id ? String(u.role_id) : 'none'}
                          onValueChange={async v => {
                            try {
                              await updateUser(u.id, { role_id: v === 'none' ? null : Number(v) })
                              toast('Role assigned')
                              load()
                            } catch (err: any) {
                              toast(err.response?.data?.detail || 'Failed to assign role', 'error')
                            }
                          }}
                        >
                          <SelectTrigger className="w-40 h-8 text-xs"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="none">Unassigned</SelectItem>
                            {roles.map(r => (
                              <SelectItem key={r.id} value={String(r.id)}>{r.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </td>
                      <td className="px-6 py-3.5">
                        <Badge variant={u.is_active ? 'success' : 'outline'} dot>
                          {u.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="px-6 py-3.5 text-right">
                        <button
                          onClick={() => handleToggleActive(u)}
                          className={`transition-colors ${u.is_active ? 'text-emerald-500 hover:text-red-500' : 'text-muted-foreground hover:text-emerald-500'}`}
                          title={u.is_active ? 'Deactivate' : 'Activate'}
                        >
                          {u.is_active ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
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
    </div>
  )
}
