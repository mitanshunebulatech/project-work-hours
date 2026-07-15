import { useEffect, useState } from 'react'
import { getRoles, getPermissions, createRole, updateRole, deleteRole } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, CardHeader, CardTitle, Badge, Label } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/ui/empty-state'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import { Plus, RefreshCw, Pencil, Trash2, ShieldCheck, Lock } from 'lucide-react'

const emptyForm = { name: '', description: '', permission_codes: [] as string[] }

export default function AdminRoles() {
  const { toast } = useToast()
  const [roles, setRoles] = useState<any[]>([])
  const [permissions, setPermissions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingIsSystem, setEditingIsSystem] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [errors, setErrors] = useState<any>({})

  const load = async () => {
    setLoading(true)
    try {
      const [rolesRes, permsRes] = await Promise.all([getRoles(), getPermissions()])
      setRoles(rolesRes.data)
      setPermissions(permsRes.data)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const resetForm = () => {
    setShowForm(false); setEditingId(null); setEditingIsSystem(false); setForm(emptyForm); setErrors({})
  }

  const openCreate = () => { resetForm(); setShowForm(true) }

  const openEdit = (r: any) => {
    setEditingId(r.id)
    setEditingIsSystem(r.is_system_role)
    setForm({
      name: r.name,
      description: r.description || '',
      permission_codes: r.permissions.map((p: any) => p.code),
    })
    setErrors({})
    setShowForm(true)
  }

  const togglePermission = (code: string) => {
    setForm(f => ({
      ...f,
      permission_codes: f.permission_codes.includes(code)
        ? f.permission_codes.filter(c => c !== code)
        : [...f.permission_codes, code],
    }))
  }

  const validate = () => {
    const e: any = {}
    if (!form.name.trim()) e.name = 'Role name is required'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = async () => {
    if (!validate()) return
    setSubmitting(true)
    try {
      // System roles: name/description only — permission_codes is omitted
      // entirely rather than sent unchanged, since the backend rejects the
      // field outright for system roles even if the value wouldn't change.
      const payload = editingIsSystem
        ? { name: form.name, description: form.description || null }
        : { name: form.name, description: form.description || null, permission_codes: form.permission_codes }

      if (editingId) {
        await updateRole(editingId, payload)
        toast('Role updated')
      } else {
        await createRole(payload as any)
        toast('Role created')
      }
      resetForm()
      load()
    } catch (err: any) {
      const msg = err.response?.data?.detail
      toast(Array.isArray(msg) ? msg[0]?.msg : (msg || 'Failed to save role'), 'error')
    } finally { setSubmitting(false) }
  }

  const handleDelete = async (r: any) => {
    try {
      await deleteRole(r.id)
      toast('Role deleted')
      load()
    } catch (err: any) {
      toast(err.response?.data?.detail || 'Failed to delete role', 'error')
    }
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">Roles</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {roles.length} role{roles.length === 1 ? '' : 's'} · admin and employee are built-in and can't be deleted
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
          <Button size="sm" onClick={openCreate}><Plus size={14} /> New Role</Button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => <div key={i} className="h-20 bg-muted rounded-xl animate-pulse" />)}
        </div>
      ) : roles.length === 0 ? (
        <Card><EmptyState icon={ShieldCheck} title="No roles yet" description="Create a role to start assigning granular permissions." /></Card>
      ) : (
        <div className="space-y-3">
          {roles.map((r: any) => (
            <Card key={r.id} hover className="group">
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-foreground text-sm">{r.name}</p>
                      {r.is_system_role && (
                        <Badge variant="outline" className="gap-1"><Lock size={10} /> System</Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{r.description || 'No description'}</p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {r.permissions.length === 0 ? (
                        <span className="text-xs text-muted-foreground/60">No permissions assigned</span>
                      ) : r.permissions.map((p: any) => (
                        <Badge key={p.id} variant="secondary" className="text-[10px]">{p.code}</Badge>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
                    <button onClick={() => openEdit(r)} className="text-muted-foreground/40 hover:text-foreground" title="Edit">
                      <Pencil size={14} />
                    </button>
                    {!r.is_system_role && (
                      <button onClick={() => handleDelete(r)} className="text-muted-foreground/40 hover:text-destructive" title="Delete">
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={showForm} onOpenChange={(open: boolean) => { if (!open) resetForm() }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingId ? 'Edit Role' : 'Create Role'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>Name <span className="text-destructive">*</span></Label>
              <Input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              {errors.name && <p className="text-xs text-destructive">{errors.name}</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Description</Label>
              <Input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </div>
            <div className="space-y-1.5">
              <Label>Permissions</Label>
              {editingIsSystem ? (
                <p className="text-xs text-muted-foreground/70 border rounded-lg p-3 bg-muted/30">
                  System role permissions are fixed and can't be edited here — create a custom role
                  instead if different access is needed.
                </p>
              ) : (
                <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto border rounded-lg p-3">
                  {permissions.map((p: any) => (
                    <label key={p.id} className="flex items-center gap-2 text-xs cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.permission_codes.includes(p.code)}
                        onChange={() => togglePermission(p.code)}
                      />
                      <span title={p.description || ''}>{p.code}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={resetForm}>Cancel</Button>
            <Button size="sm" onClick={handleSubmit} loading={submitting}>
              {editingId ? 'Save Changes' : 'Create Role'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
