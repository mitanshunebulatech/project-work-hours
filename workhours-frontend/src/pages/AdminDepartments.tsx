import { useEffect, useState } from 'react'
import { getDepartments, createDepartment, updateDepartment, deactivateDepartment } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, CardHeader, CardTitle, Badge, Label, Textarea } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/ui/empty-state'
import { Plus, RefreshCw, Pencil, ToggleLeft, ToggleRight, Building2 } from 'lucide-react'

export default function AdminDepartments() {
  const { toast } = useToast()
  const [departments, setDepartments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ name: '', description: '' })
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const res = await getDepartments({ page: 1, size: 100 })
      setDepartments(res.data.items)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const resetForm = () => {
    setShowForm(false); setEditingId(null); setForm({ name: '', description: '' }); setError('')
  }

  const startEdit = (d: any) => {
    setEditingId(d.id)
    setForm({ name: d.name, description: d.description || '' })
    setShowForm(true)
  }

  const handleSubmit = async () => {
    if (!form.name.trim()) { setError('Department name is required'); return }
    setSubmitting(true)
    try {
      if (editingId) {
        await updateDepartment(editingId, { name: form.name, description: form.description || null })
        toast('Department updated')
      } else {
        await createDepartment({ name: form.name, description: form.description || null })
        toast('Department created')
      }
      resetForm()
      load()
    } catch (err: any) {
      const msg = err.response?.data?.detail
      toast(Array.isArray(msg) ? msg[0]?.msg : (msg || 'Failed to save department'), 'error')
    } finally { setSubmitting(false) }
  }

  const handleToggleActive = async (d: any) => {
    try {
      if (d.is_active) {
        await deactivateDepartment(d.id)
        toast('Department deactivated')
      } else {
        await updateDepartment(d.id, { is_active: true })
        toast('Department reactivated')
      }
      load()
    } catch (err: any) {
      toast(err.response?.data?.detail || 'Failed to update department', 'error')
    }
  }

  const activeCount = departments.filter(d => d.is_active).length

  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">Departments</h1>
          <p className="text-sm text-muted-foreground mt-1">{activeCount} active departments</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
          <Button size="sm" onClick={() => { resetForm(); setShowForm(true) }}><Plus size={14} /> New Department</Button>
        </div>
      </div>

      {showForm && (
        <Card className="mb-6 border-nebula-200 shadow-elevated animate-in fade-in slide-in-from-top-1 duration-200">
          <CardHeader className="pb-3"><CardTitle>{editingId ? 'Edit Department' : 'Create Department'}</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Name <span className="text-destructive">*</span></Label>
              <Input placeholder="e.g. Engineering" value={form.name}
                onChange={e => { setForm(f => ({ ...f, name: e.target.value })); setError('') }} />
              {error && <p className="text-xs text-destructive">{error}</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Description</Label>
              <Textarea placeholder="Brief description of this department..." rows={2}
                value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={handleSubmit} loading={submitting}>
                {editingId ? 'Save Changes' : 'Create Department'}
              </Button>
              <Button size="sm" variant="outline" onClick={resetForm}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {loading ? (
          [1, 2, 3, 4].map(i => <div key={i} className="h-24 bg-muted rounded-xl animate-pulse" />)
        ) : departments.length === 0 ? (
          <Card className="col-span-2">
            <EmptyState icon={Building2} title="No departments yet" description="Create the first department to start organizing employees." />
          </Card>
        ) : departments.map((d: any) => (
          <Card key={d.id} hover className="group">
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-nebula-50 rounded-lg mt-0.5">
                    <Building2 size={16} className="text-nebula-600" />
                  </div>
                  <div>
                    <p className="font-medium text-foreground text-sm">{d.name}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{d.description || 'No description'}</p>
                    <Badge variant={d.is_active ? 'success' : 'outline'} dot className="mt-2">
                      {d.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
                  <button onClick={() => startEdit(d)} className="text-muted-foreground/40 hover:text-foreground" title="Edit">
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => handleToggleActive(d)}
                    className={d.is_active ? 'text-emerald-500/60 hover:text-red-500' : 'text-muted-foreground/40 hover:text-emerald-500'}
                    title={d.is_active ? 'Deactivate' : 'Reactivate'}
                  >
                    {d.is_active ? <ToggleRight size={16} /> : <ToggleLeft size={16} />}
                  </button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
