import { useEffect, useState } from 'react'
import { getEntries, getProjects, createEntry, updateEntry } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, CardHeader, CardTitle, Badge, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem, Textarea } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Plus, RefreshCw, Pencil } from 'lucide-react'
import { formatDate } from '@/lib/utils'

const STATUS_VARIANT: Record<string, any> = {
  pending: 'pending', approved: 'success', rejected: 'destructive'
}

export default function Timesheets() {
  const { toast } = useToast()
  const [entries, setEntries] = useState<any[]>([])
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editEntry, setEditEntry] = useState<any>(null)
  const [submitting, setSubmitting] = useState(false)

  const [form, setForm] = useState({
    project_id: '', entry_date: new Date().toISOString().slice(0, 10),
    hours_worked: '', remarks: ''
  })

  const load = async () => {
    setLoading(true)
    try {
      const [entriesRes, projectsRes] = await Promise.all([
        getEntries({ page: 1, size: 100 }),
        getProjects({ page: 1, size: 100, is_active: true })
      ])
      setEntries(entriesRes.data.items)
      setProjects(projectsRes.data.items)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const resetForm = () => {
    setForm({ project_id: '', entry_date: new Date().toISOString().slice(0, 10), hours_worked: '', remarks: '' })
    setShowForm(false)
    setEditEntry(null)
  }

  const handleSubmit = async () => {
    if (!form.project_id || !form.hours_worked) {
      toast('Please fill all required fields', 'error'); return
    }
    const hours = parseFloat(form.hours_worked)
    if (isNaN(hours) || hours <= 0 || hours > 24) {
      toast('Hours must be between 0 and 24', 'error'); return
    }
    setSubmitting(true)
    try {
      if (editEntry) {
        await updateEntry(editEntry.id, { hours_worked: hours, remarks: form.remarks || null })
        toast('Entry updated successfully')
      } else {
        await createEntry({ project_id: parseInt(form.project_id), entry_date: form.entry_date, hours_worked: hours, remarks: form.remarks || null })
        toast('Entry submitted successfully')
      }
      resetForm(); load()
    } catch (err: any) {
      const msg = err.response?.data?.detail
      toast(Array.isArray(msg) ? msg[0]?.msg : (msg || 'Failed to save entry'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const openEdit = (entry: any) => {
    setEditEntry(entry)
    setForm({ project_id: String(entry.project_id), entry_date: entry.entry_date, hours_worked: String(entry.hours_worked), remarks: entry.remarks || '' })
    setShowForm(true)
  }

  const today = new Date().toISOString().slice(0, 10)
  const canEdit = (e: any) => e.status === 'pending' && e.entry_date === today

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">My Timesheets</h1>
          <p className="text-sm text-slate-500 mt-0.5">Submit and track your daily work hours</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
          <Button size="sm" onClick={() => { resetForm(); setShowForm(true) }}>
            <Plus size={14} /> Log Hours
          </Button>
        </div>
      </div>

      {/* Submit form */}
      {showForm && (
        <Card className="mb-6 border-blue-200 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle>{editEntry ? 'Edit Entry' : 'Log Work Hours'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Project <span className="text-red-500">*</span></Label>
                <Select value={form.project_id} onValueChange={v => setForm(f => ({ ...f, project_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="Select project" /></SelectTrigger>
                  <SelectContent>
                    {projects.map(p => <SelectItem key={p.id} value={String(p.id)}>{p.project_name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Date <span className="text-red-500">*</span></Label>
                <Input type="date" value={form.entry_date} max={today}
                  onChange={e => setForm(f => ({ ...f, entry_date: e.target.value }))} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Hours Worked <span className="text-red-500">*</span></Label>
                <Select value={form.hours_worked} onValueChange={v => setForm(f => ({ ...f, hours_worked: v }))}>
                  <SelectTrigger><SelectValue placeholder="Select or type hours" /></SelectTrigger>
                  <SelectContent>
                    {['1','2','3','4','5','6','7','7.5','8','9','10','12'].map(h =>
                      <SelectItem key={h} value={h}>{h} hours</SelectItem>)}
                  </SelectContent>
                </Select>
                <Input placeholder="Or type custom hours (e.g. 6.5)"
                  value={form.hours_worked}
                  onChange={e => setForm(f => ({ ...f, hours_worked: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Remarks</Label>
                <Textarea placeholder="What did you work on?" rows={2}
                  value={form.remarks} onChange={e => setForm(f => ({ ...f, remarks: e.target.value }))} />
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <Button size="sm" onClick={handleSubmit} disabled={submitting}>
                {submitting ? 'Saving...' : editEntry ? 'Update Entry' : 'Submit Entry'}
              </Button>
              <Button size="sm" variant="outline" onClick={resetForm}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Entries table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Submission History</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-3">
              {[1,2,3].map(i => <div key={i} className="h-10 bg-slate-100 rounded animate-pulse" />)}
            </div>
          ) : entries.length === 0 ? (
            <div className="px-6 py-12 text-center text-sm text-slate-400">
              No entries yet. Click "Log Hours" to get started.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-slate-50">
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">Date</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">Project</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">Hours</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">Remarks</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">Status</th>
                  <th className="px-6 py-3" />
                </tr>
              </thead>
              <tbody>
                {entries.map((e: any) => (
                  <tr key={e.id} className="border-b last:border-0 hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-3.5 text-slate-600 whitespace-nowrap">{formatDate(e.entry_date)}</td>
                    <td className="px-6 py-3.5 font-medium text-slate-900">{e.project_name}</td>
                    <td className="px-6 py-3.5 text-slate-700 font-medium">{e.hours_worked}h</td>
                    <td className="px-6 py-3.5 text-slate-500 max-w-[200px] truncate">{e.remarks || '—'}</td>
                    <td className="px-6 py-3.5"><Badge variant={STATUS_VARIANT[e.status]}>{e.status}</Badge></td>
                    <td className="px-6 py-3.5 text-right">
                      {canEdit(e) && (
                        <button onClick={() => openEdit(e)} className="text-slate-400 hover:text-blue-600 transition-colors">
                          <Pencil size={14} />
                        </button>
                      )}
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
