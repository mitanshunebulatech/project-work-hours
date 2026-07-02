import { useEffect, useState } from 'react'
import { getProjects, createProject, deleteProject } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, CardHeader, CardTitle, Badge, Label, Textarea } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Plus, RefreshCw, Trash2, FolderOpen } from 'lucide-react'

export default function AdminProjects() {
  const { toast } = useToast()
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ project_name: '', description: '' })
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const res = await getProjects({ page: 1, size: 100 })
      setProjects(res.data.items)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    if (!form.project_name.trim()) { setError('Project name is required'); return }
    setSubmitting(true)
    try {
      await createProject({ project_name: form.project_name, description: form.description || null })
      toast('Project created')
      setShowForm(false); setForm({ project_name: '', description: '' }); setError('')
      load()
    } catch (err: any) {
      const msg = err.response?.data?.detail
      toast(Array.isArray(msg) ? msg[0]?.msg : (msg || 'Failed to create project'), 'error')
    } finally { setSubmitting(false) }
  }

  const handleDelete = async (p: any) => {
    if (!confirm(`Deactivate "${p.project_name}"? Existing entries will be preserved.`)) return
    try {
      await deleteProject(p.id)
      toast('Project deactivated')
      load()
    } catch { toast('Failed to deactivate project', 'error') }
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Projects</h1>
          <p className="text-sm text-slate-500 mt-0.5">{projects.length} active projects</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
          <Button size="sm" onClick={() => setShowForm(true)}><Plus size={14} /> New Project</Button>
        </div>
      </div>

      {showForm && (
        <Card className="mb-6 border-blue-200">
          <CardHeader className="pb-3"><CardTitle>Create Project</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Project Name <span className="text-red-500">*</span></Label>
              <Input placeholder="e.g. Website Redesign" value={form.project_name}
                onChange={e => { setForm(f => ({ ...f, project_name: e.target.value })); setError('') }} />
              {error && <p className="text-xs text-red-500">{error}</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Description</Label>
              <Textarea placeholder="Brief description of this project..." rows={2}
                value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={handleCreate} disabled={submitting}>
                {submitting ? 'Creating...' : 'Create Project'}
              </Button>
              <Button size="sm" variant="outline" onClick={() => { setShowForm(false); setError('') }}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {loading ? (
          [1,2,3,4].map(i => <div key={i} className="h-24 bg-slate-100 rounded-lg animate-pulse" />)
        ) : projects.length === 0 ? (
          <div className="col-span-2 py-12 text-center text-sm text-slate-400">
            No projects yet. Create the first one.
          </div>
        ) : projects.map((p: any) => (
          <Card key={p.id} className="group hover:border-blue-200 transition-colors">
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-blue-50 rounded-lg mt-0.5">
                    <FolderOpen size={16} className="text-blue-600" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-900 text-sm">{p.project_name}</p>
                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{p.description || 'No description'}</p>
                    <Badge variant={p.is_active ? 'success' : 'outline'} className="mt-2">
                      {p.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                </div>
                {p.is_active && (
                  <button onClick={() => handleDelete(p)}
                    className="opacity-0 group-hover:opacity-100 text-slate-300 hover:text-red-500 transition-all">
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
