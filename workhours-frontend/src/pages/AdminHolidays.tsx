import { useEffect, useState } from 'react'
import {
  getHolidays, createHoliday, updateHoliday, deactivateHoliday,
  publishHolidayYear, unpublishHolidayYear
} from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, CardHeader, CardTitle, Badge, Label } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/ui/empty-state'
import { Plus, RefreshCw, Pencil, ToggleLeft, ToggleRight, CalendarDays, CheckCircle2, XCircle } from 'lucide-react'
import { formatDate } from '@/lib/utils'

const CURRENT_YEAR = new Date().getFullYear()
// A few years back and forward — admins mostly manage the current/next
// year's calendar but occasionally need to look back or plan further out.
const YEAR_OPTIONS = Array.from({ length: 7 }, (_, i) => CURRENT_YEAR - 2 + i)

export default function AdminHolidays() {
  const { toast } = useToast()
  const [year, setYear] = useState(CURRENT_YEAR)
  const [holidays, setHolidays] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [publishing, setPublishing] = useState(false)

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ name: '', date: '' })
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const res = await getHolidays({ year, page: 1, size: 100 })
      const items = [...res.data.items].sort((a: any, b: any) => a.date.localeCompare(b.date))
      setHolidays(items)
    } catch {
      toast('Failed to load holidays', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [year]) // eslint-disable-line react-hooks/exhaustive-deps

  const resetForm = () => {
    setShowForm(false); setEditingId(null); setForm({ name: '', date: '' }); setError('')
  }

  const startEdit = (h: any) => {
    setEditingId(h.id)
    setForm({ name: h.name, date: h.date })
    setShowForm(true)
  }

  const handleSubmit = async () => {
    if (!form.name.trim()) { setError('Holiday name is required'); return }
    if (!form.date) { setError('Date is required'); return }
    setSubmitting(true)
    try {
      if (editingId) {
        await updateHoliday(editingId, { name: form.name, date: form.date })
        toast('Holiday updated')
      } else {
        await createHoliday({ name: form.name, date: form.date })
        toast('Holiday created')
      }
      resetForm()
      // A date edit can move a holiday into a different year than the one
      // currently selected — re-derive from the submitted date rather than
      // leaving the admin looking at a list that silently dropped an entry.
      const submittedYear = Number(form.date.slice(0, 4))
      if (submittedYear !== year) setYear(submittedYear)
      else load()
    } catch (err: any) {
      const msg = err.response?.data?.detail
      toast(Array.isArray(msg) ? msg[0]?.msg : (msg || 'Failed to save holiday'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeactivate = async (h: any) => {
    try {
      await deactivateHoliday(h.id)
      toast('Holiday deactivated')
      load()
    } catch (err: any) {
      toast(err.response?.data?.detail || 'Failed to deactivate holiday', 'error')
    }
  }

  const handlePublish = async () => {
    setPublishing(true)
    try {
      const res = await publishHolidayYear(year)
      toast(res.data.message || `Published ${year}`)
      load()
    } catch (err: any) {
      toast(err.response?.data?.detail || 'Failed to publish calendar', 'error')
    } finally {
      setPublishing(false)
    }
  }

  const handleUnpublish = async () => {
    setPublishing(true)
    try {
      const res = await unpublishHolidayYear(year)
      toast(res.data.message || `Unpublished ${year}`)
      load()
    } catch (err: any) {
      toast(err.response?.data?.detail || 'Failed to unpublish calendar', 'error')
    } finally {
      setPublishing(false)
    }
  }

  const activeHolidays = holidays.filter(h => h.is_active)
  // Published state is a per-holiday flag (HolidayService.publish_year sets
  // it per row), so "is this year published" is derived here rather than
  // tracked as separate state — true only once every active holiday in the
  // year has been published, so a half-published year still shows as
  // needing publish rather than falsely reading as done.
  const allPublished = activeHolidays.length > 0 && activeHolidays.every(h => h.is_published)

  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">Holiday Calendar</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage the yearly holiday list — employees only see a year once it's published.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
          <Button size="sm" onClick={() => { resetForm(); setShowForm(true) }}><Plus size={14} /> Add Holiday</Button>
        </div>
      </div>

      <Card className="mb-4">
        <CardContent className="p-4 flex flex-wrap items-center gap-3">
          <div className="space-y-1.5">
            <Label className="text-xs">Year</Label>
            <select
              value={year}
              onChange={e => setYear(Number(e.target.value))}
              className="h-9 px-3 rounded-md border border-input bg-background text-sm"
            >
              {YEAR_OPTIONS.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
          <div className="flex-1" />
          <Badge variant={allPublished ? 'success' : 'warning'} dot>
            {allPublished ? 'Published' : 'Draft (not visible to employees)'}
          </Badge>
          {allPublished ? (
            <Button size="sm" variant="outline" onClick={handleUnpublish} loading={publishing}>
              <XCircle size={14} /> Unpublish {year}
            </Button>
          ) : (
            <Button size="sm" onClick={handlePublish} loading={publishing} disabled={activeHolidays.length === 0}>
              <CheckCircle2 size={14} /> Publish {year}
            </Button>
          )}
        </CardContent>
      </Card>

      {showForm && (
        <Card className="mb-6 border-nebula-200 shadow-elevated animate-in fade-in slide-in-from-top-1 duration-200">
          <CardHeader className="pb-3"><CardTitle>{editingId ? 'Edit Holiday' : 'Add Holiday'}</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Occasion / Name <span className="text-destructive">*</span></Label>
              <Input placeholder="e.g. Republic Day" value={form.name}
                onChange={e => { setForm(f => ({ ...f, name: e.target.value })); setError('') }} />
            </div>
            <div className="space-y-1.5">
              <Label>Date <span className="text-destructive">*</span></Label>
              <input type="date" value={form.date}
                onChange={e => { setForm(f => ({ ...f, date: e.target.value })); setError('') }}
                className="h-9 px-3 rounded-md border border-input bg-background text-sm" />
            </div>
            {error && <p className="text-xs text-destructive">{error}</p>}
            <div className="flex gap-2">
              <Button size="sm" onClick={handleSubmit} loading={submitting}>
                {editingId ? 'Save Changes' : 'Add Holiday'}
              </Button>
              <Button size="sm" variant="outline" onClick={resetForm}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3"><CardTitle>{year} Holidays</CardTitle></CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-2">
              {[1, 2, 3].map(i => <div key={i} className="h-12 bg-muted rounded-lg animate-pulse" />)}
            </div>
          ) : holidays.length === 0 ? (
            <EmptyState icon={CalendarDays} title={`No holidays for ${year}`} description="Add the first holiday to start building this year's calendar." />
          ) : (
            <div className="divide-y">
              {holidays.map((h: any) => (
                <div key={h.id} className="flex items-center justify-between px-4 py-3 group">
                  <div className="flex items-center gap-3">
                    <CalendarDays size={16} className="text-muted-foreground shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-foreground">{h.name}</p>
                      <p className="text-xs text-muted-foreground">{formatDate(h.date)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={h.is_active ? (h.is_published ? 'success' : 'warning') : 'outline'} dot>
                      {h.is_active ? (h.is_published ? 'Published' : 'Draft') : 'Deactivated'}
                    </Badge>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
                      <button onClick={() => startEdit(h)} className="text-muted-foreground/40 hover:text-foreground" title="Edit">
                        <Pencil size={14} />
                      </button>
                      {h.is_active && (
                        <button onClick={() => handleDeactivate(h)} className="text-emerald-500/60 hover:text-red-500" title="Deactivate">
                          <ToggleRight size={16} />
                        </button>
                      )}
                      {!h.is_active && <ToggleLeft size={16} className="text-muted-foreground/40" />}
                    </div>
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
