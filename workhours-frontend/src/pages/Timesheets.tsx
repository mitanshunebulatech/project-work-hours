import { useEffect, useState } from 'react'
import { getEntries, getProjects, createEntry, updateEntry } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, CardHeader, CardTitle, Badge, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem, Textarea } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TableSkeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { Plus, RefreshCw, Pencil, ClipboardList } from 'lucide-react'
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

  const weekHours = entries
    .filter(e => {
      const d = new Date(e.entry_date)
      const now = new Date()
      const start = new Date(now); start.setDate(now.getDate() - now.getDay())
      return d >= start
    })
    .reduce((s, e) => s + parseFloat(e.hours_worked), 0)

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">My Timesheets</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Submit and track your daily work hours · <span className="font-medium text-foreground">{weekHours.toFixed(1)}h</span> logged this week
          </p>
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
        <Card className="mb-6 border-nebula-200 shadow-elevated animate-in fade-in slide-in-from-top-1 duration-200">
          <CardHeader className="pb-3">
            <CardTitle>{editEntry ? 'Edit Entry' : 'Log Work Hours'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Project <span className="text-destructive">*</span></Label>
                <Select value={form.project_id} onValueChange={v => setForm(f => ({ ...f, project_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="Select project" /></SelectTrigger>
                  <SelectContent>
                    {projects.map(p => <SelectItem key={p.id} value={String(p.id)}>{p.project_name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Date <span className="text-destructive">*</span></Label>
                <Input type="date" value={form.entry_date} max={today}
                  onChange={e => setForm(f => ({ ...f, entry_date: e.target.value }))} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Hours Worked <span className="text-destructive">*</span></Label>
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
              <Button size="sm" onClick={handleSubmit} loading={submitting}>
                {editEntry ? 'Update Entry' : 'Submit Entry'}
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
            <TableSkeleton rows={4} cols={6} />
          ) : entries.length === 0 ? (
            <EmptyState
              icon={ClipboardList}
              title="No entries yet"
              description='Click "Log Hours" above to submit your first timesheet.'
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/40">
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Date</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Project</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Hours</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Remarks</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Status</th>
                    <th className="px-6 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {entries.map((e: any) => (
                    <tr key={e.id} className="border-b last:border-0 hover:bg-muted/40 transition-colors">
                      <td className="px-6 py-3.5 text-muted-foreground whitespace-nowrap">{formatDate(e.entry_date)}</td>
                      <td className="px-6 py-3.5 font-medium text-foreground">{e.project_name}</td>
                      <td className="px-6 py-3.5 text-foreground font-medium tabular-nums">{e.hours_worked}h</td>
                      <td className="px-6 py-3.5 text-muted-foreground max-w-[200px] truncate">{e.remarks || '—'}</td>
                      <td className="px-6 py-3.5"><Badge variant={STATUS_VARIANT[e.status]} dot>{e.status}</Badge></td>
                      <td className="px-6 py-3.5 text-right">
                        {canEdit(e) && (
                          <button onClick={() => openEdit(e)} className="text-muted-foreground hover:text-nebula-600 transition-colors">
                            <Pencil size={14} />
                          </button>
                        )}
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
