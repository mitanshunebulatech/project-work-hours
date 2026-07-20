import { useEffect, useState } from 'react'
import { getLeavePlans, createLeavePlan, updateLeavePlan, deleteLeavePlan, getLeaveTypes } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, CardHeader, CardTitle, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/ui/empty-state'
import { Plus, RefreshCw, Pencil, Trash2, CalendarRange } from 'lucide-react'
import { formatDate } from '@/lib/utils'

const CURRENT_YEAR = new Date().getFullYear()

/**
 * PM req #6 — informational, year-ahead leave planning. Deliberately NOT
 * a leave request: no approval, no balance deduction (see LeavePlanService
 * docstring). This page is self-service only — an employee's own plans —
 * matching how Leave.tsx (leave requests) scopes itself; admin-wide
 * visibility across employees isn't built here (LeavePlanService.list_plans
 * supports it server-side already, if a future admin overview page needs it).
 */
export default function LeavePlans() {
  const { toast } = useToast()
  const [plans, setPlans] = useState<any[]>([])
  const [leaveTypes, setLeaveTypes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ leave_type_id: '', start: '', end: '', reason: '' })
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [plansRes, typesRes] = await Promise.all([
        getLeavePlans({ year: CURRENT_YEAR, page: 1, size: 100 }),
        getLeaveTypes(),
      ])
      const items = [...plansRes.data.items].sort((a: any, b: any) => a.planned_start_date.localeCompare(b.planned_start_date))
      setPlans(items)
      setLeaveTypes(typesRes.data)
    } catch {
      toast('Failed to load leave plans', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const resetForm = () => {
    setShowForm(false); setEditingId(null)
    setForm({ leave_type_id: '', start: '', end: '', reason: '' })
    setError('')
  }

  const startEdit = (p: any) => {
    setEditingId(p.id)
    setForm({
      leave_type_id: String(p.leave_type_id),
      start: p.planned_start_date,
      end: p.planned_end_date,
      reason: p.reason || '',
    })
    setShowForm(true)
  }

  const handleSubmit = async () => {
    if (!form.leave_type_id) { setError('Leave type is required'); return }
    if (!form.start || !form.end) { setError('Start and end dates are required'); return }
    if (form.end < form.start) { setError('End date cannot be before start date'); return }
    setSubmitting(true)
    try {
      const payload = {
        leave_type_id: Number(form.leave_type_id),
        planned_start_date: form.start,
        planned_end_date: form.end,
        reason: form.reason || null,
      }
      if (editingId) {
        await updateLeavePlan(editingId, payload)
        toast('Leave plan updated')
      } else {
        await createLeavePlan(payload)
        toast('Leave plan added')
      }
      resetForm()
      load()
    } catch (err: any) {
      const msg = err.response?.data?.detail
      toast(Array.isArray(msg) ? msg[0]?.msg : (msg || 'Failed to save leave plan'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteLeavePlan(id)
      toast('Leave plan removed')
      load()
    } catch (err: any) {
      toast(err.response?.data?.detail || 'Failed to remove leave plan', 'error')
    }
  }

  return (
    <div className="p-8 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">Leave Planning</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Note down leave you're planning ahead of time — this is informational only and doesn't submit a leave request.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
          <Button size="sm" onClick={() => { resetForm(); setShowForm(true) }}><Plus size={14} /> Plan Leave</Button>
        </div>
      </div>

      {showForm && (
        <Card className="mb-6 border-nebula-200 shadow-elevated animate-in fade-in slide-in-from-top-1 duration-200">
          <CardHeader className="pb-3"><CardTitle>{editingId ? 'Edit Plan' : 'Plan Leave'}</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Leave Type <span className="text-destructive">*</span></Label>
              <Select value={form.leave_type_id} onValueChange={v => { setForm(f => ({ ...f, leave_type_id: v })); setError('') }}>
                <SelectTrigger><SelectValue placeholder="Select leave type" /></SelectTrigger>
                <SelectContent>
                  {leaveTypes.map((t: any) => <SelectItem key={t.id} value={String(t.id)}>{t.display_name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Start Date <span className="text-destructive">*</span></Label>
                <input type="date" value={form.start}
                  onChange={e => { setForm(f => ({ ...f, start: e.target.value })); setError('') }}
                  className="h-9 px-3 rounded-md border border-input bg-background text-sm w-full" />
              </div>
              <div className="space-y-1.5">
                <Label>End Date <span className="text-destructive">*</span></Label>
                <input type="date" value={form.end}
                  onChange={e => { setForm(f => ({ ...f, end: e.target.value })); setError('') }}
                  className="h-9 px-3 rounded-md border border-input bg-background text-sm w-full" />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Occasion / Reason</Label>
              <Input placeholder="e.g. Family trip" value={form.reason}
                onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} />
            </div>
            {error && <p className="text-xs text-destructive">{error}</p>}
            <div className="flex gap-2">
              <Button size="sm" onClick={handleSubmit} loading={submitting}>
                {editingId ? 'Save Changes' : 'Add Plan'}
              </Button>
              <Button size="sm" variant="outline" onClick={resetForm}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3"><CardTitle>Your Planned Leave</CardTitle></CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-2">
              {[1, 2].map(i => <div key={i} className="h-12 bg-muted rounded-lg animate-pulse" />)}
            </div>
          ) : plans.length === 0 ? (
            <EmptyState icon={CalendarRange} title="No leave planned yet"
              description="Add planned leave so you and your team have visibility ahead of time." />
          ) : (
            <div className="divide-y">
              {plans.map((p: any) => (
                <div key={p.id} className="flex items-center justify-between px-4 py-3 group">
                  <div className="flex items-center gap-3">
                    <CalendarRange size={16} className="text-muted-foreground shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {leaveTypes.find((t: any) => t.id === p.leave_type_id)?.display_name || 'Leave'}
                        {p.reason && <span className="text-muted-foreground font-normal"> — {p.reason}</span>}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(p.planned_start_date)} – {formatDate(p.planned_end_date)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all">
                    <button onClick={() => startEdit(p)} className="text-muted-foreground/40 hover:text-foreground" title="Edit">
                      <Pencil size={14} />
                    </button>
                    <button onClick={() => handleDelete(p.id)} className="text-muted-foreground/40 hover:text-destructive" title="Remove">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
