import { useEffect, useState } from 'react'
import type { DateRange } from 'react-day-picker'
import { useToast } from '@/hooks/useToast'
import {
  getLeaveTypes, getMyLeaveBalances, getMyLeaveRequests, previewLeaveRequest,
  createLeaveRequest, uploadLeaveAttachment, downloadLeaveAttachment, cancelLeaveRequest
} from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, Badge, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem, Textarea } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { LeaveDateRangePicker } from '@/components/ui/date-range-picker'
import { CardGridSkeleton, TableSkeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { CalendarPlus, Paperclip, Plane, RefreshCw, X, CalendarClock, AlertTriangle, Download } from 'lucide-react'
import { formatDate } from '@/lib/utils'

const STATUS_VARIANT: Record<string, any> = {
  pending: 'pending', approved: 'success', rejected: 'destructive', cancelled: 'secondary'
}

/** Local (not UTC) yyyy-MM-dd — avoids the timezone-shift bug that
 * Date.toISOString() introduces for anything east of UTC (e.g. IST). */
function toISODate(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function startOfToday() {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d
}

export default function Leave() {
  const { toast } = useToast()

  const [loading, setLoading] = useState(true)
  const [leaveTypes, setLeaveTypes] = useState<any[]>([])
  const [balances, setBalances] = useState<any[]>([])
  const [requests, setRequests] = useState<any[]>([])

  const [showForm, setShowForm] = useState(false)
  const [leaveTypeId, setLeaveTypeId] = useState('')
  const [range, setRange] = useState<DateRange | undefined>()
  const [isHalfDay, setIsHalfDay] = useState(false)
  const [reason, setReason] = useState('')
  const [attachmentPath, setAttachmentPath] = useState<string | null>(null)
  const [attachmentName, setAttachmentName] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const [preview, setPreview] = useState<any>(null)
  const [previewing, setPreviewing] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const selectedType = leaveTypes.find(t => String(t.id) === leaveTypeId)

  const load = async () => {
    setLoading(true)
    try {
      const [typesRes, balancesRes, requestsRes] = await Promise.all([
        getLeaveTypes(),
        getMyLeaveBalances(),
        getMyLeaveRequests({ page: 1, size: 50 })
      ])
      setLeaveTypes(typesRes.data)
      setBalances(balancesRes.data)
      setRequests(requestsRes.data.items)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const resetForm = () => {
    setShowForm(false)
    setLeaveTypeId('')
    setRange(undefined)
    setIsHalfDay(false)
    setReason('')
    setAttachmentPath(null)
    setAttachmentName(null)
    setPreview(null)
  }

  const errMsg = (err: any, fallback: string) => {
    const detail = err.response?.data?.detail
    if (Array.isArray(detail)) return detail[0]?.msg || fallback
    return detail || fallback
  }

  const handleAttachmentChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const res = await uploadLeaveAttachment(file)
      setAttachmentPath(res.data.attachment_path)
      setAttachmentName(file.name)
      toast('Attachment uploaded')
    } catch (err: any) {
      toast(errMsg(err, 'Failed to upload attachment'), 'error')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handlePreview = async () => {
    if (!leaveTypeId || !range?.from) {
      toast('Select a leave type and date range first', 'error'); return
    }
    setPreviewing(true)
    setPreview(null)
    try {
      const res = await previewLeaveRequest({
        leave_type_id: parseInt(leaveTypeId),
        start_date: toISODate(range.from),
        end_date: toISODate(range.to || range.from),
        is_half_day: isHalfDay
      })
      setPreview(res.data)
    } catch (err: any) {
      toast(errMsg(err, 'Could not preview this request'), 'error')
    } finally {
      setPreviewing(false)
    }
  }

  const handleSubmit = async () => {
    if (!leaveTypeId || !range?.from) {
      toast('Select a leave type and date range first', 'error'); return
    }
    if (!reason || reason.trim().length < 3) {
      toast('Please enter a reason (at least 3 characters)', 'error'); return
    }
    if (preview?.attachment_required && !attachmentPath) {
      toast('This leave type requires an attachment for this many days', 'error'); return
    }
    setSubmitting(true)
    try {
      await createLeaveRequest({
        leave_type_id: parseInt(leaveTypeId),
        start_date: toISODate(range.from),
        end_date: toISODate(range.to || range.from),
        is_half_day: isHalfDay,
        reason: reason.trim(),
        attachment_path: attachmentPath
      })
      toast('Leave request submitted')
      resetForm()
      load()
    } catch (err: any) {
      toast(errMsg(err, 'Failed to submit leave request'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancel = async (id: number) => {
    try {
      await cancelLeaveRequest(id)
      toast('Leave request cancelled')
      load()
    } catch (err: any) {
      toast(errMsg(err, 'Failed to cancel request'), 'error')
    }
  }

  const handleDownload = async (id: number, filename: string) => {
    try {
      const res = await downloadLeaveAttachment(id)
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (err: any) {
      toast(errMsg(err, 'Failed to download attachment'), 'error')
    }
  }

  if (loading) return (
    <div className="p-8 max-w-5xl">
      <div className="h-8 w-64 bg-muted rounded animate-pulse mb-1.5" />
      <div className="h-4 w-80 bg-muted rounded animate-pulse mb-6" />
      <div className="mb-8"><CardGridSkeleton count={4} /></div>
      <Card><TableSkeleton rows={4} cols={5} /></Card>
    </div>
  )

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">Leave</h1>
          <p className="text-sm text-muted-foreground mt-1">Apply for leave and track your balance and request history</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
          <Button size="sm" onClick={() => { resetForm(); setShowForm(true) }}>
            <CalendarPlus size={14} /> Apply Leave
          </Button>
        </div>
      </div>

      {/* Balance cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {balances.map(b => (
          <Card key={b.leave_type_id}>
            <CardContent className="p-5">
              <p className="text-xs font-medium text-muted-foreground mb-1.5">{b.leave_type_display_name}</p>
              <p className="text-2xl font-display font-bold text-foreground tabular-nums">
                {Number(b.remaining_days).toFixed(1)}
                <span className="text-sm font-normal text-muted-foreground"> / {Number(b.total_credited_days).toFixed(1)}</span>
              </p>
              <p className="text-xs text-muted-foreground/70 mt-1">days remaining</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Apply leave form */}
      {showForm && (
        <Card className="mb-6 border-nebula-200 shadow-elevated animate-in fade-in slide-in-from-top-1 duration-200">
          <CardHeader className="pb-3">
            <CardTitle>Apply for Leave</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Leave Type <span className="text-destructive">*</span></Label>
                <Select value={leaveTypeId} onValueChange={v => { setLeaveTypeId(v); setPreview(null) }}>
                  <SelectTrigger><SelectValue placeholder="Select leave type" /></SelectTrigger>
                  <SelectContent>
                    {leaveTypes.map(t => <SelectItem key={t.id} value={String(t.id)}>{t.display_name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Dates <span className="text-destructive">*</span></Label>
                <LeaveDateRangePicker
                  value={range}
                  onChange={r => { setRange(r); setPreview(null) }}
                  disabledBefore={startOfToday()}
                />
              </div>
            </div>

            {selectedType?.allows_half_day && range?.from && (!range.to || range.to.getTime() === range.from.getTime()) && (
              <label className="flex items-center gap-2 text-sm text-foreground cursor-pointer w-fit">
                <input type="checkbox" checked={isHalfDay}
                  onChange={e => { setIsHalfDay(e.target.checked); setPreview(null) }}
                  className="rounded border-input" />
                Half day
              </label>
            )}

            <div className="space-y-1.5">
              <Label>Reason <span className="text-destructive">*</span></Label>
              <Textarea placeholder="Why are you requesting this leave?" rows={2}
                value={reason} onChange={e => setReason(e.target.value)} />
            </div>

            <div className="space-y-1.5">
              <Label>Attachment {preview?.attachment_required && <span className="text-destructive">*</span>}</Label>
              {attachmentName ? (
                <div className="flex items-center gap-2 text-sm">
                  <Paperclip size={14} className="text-muted-foreground" />
                  <span className="text-foreground">{attachmentName}</span>
                  <button onClick={() => { setAttachmentPath(null); setAttachmentName(null) }} className="text-muted-foreground hover:text-destructive">
                    <X size={14} />
                  </button>
                </div>
              ) : (
                /* FIX: previously used Button asChild wrapping a <span> that
                   contained the <input>. Radix Slot requires exactly ONE
                   child element, and Button's internal loading-state markup
                   plus that <span> meant Slot received more than one child,
                   throwing "Slot failed to slot onto its children" on mount.
                   Fix: drop asChild entirely — render a normal Button and put
                   the hidden file input as a sibling inside the <label>. The
                   <label> already forwards clicks to the input for free. */
                <label className="inline-flex">
                  <Button size="sm" variant="outline" type="button" loading={uploading}>
                    <Paperclip size={14} /> {uploading ? 'Uploading…' : 'Attach file'}
                  </Button>
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf,.jpg,.jpeg,.png,.docx"
                    onChange={handleAttachmentChange}
                  />
                </label>
              )}
              <p className="text-xs text-muted-foreground/70">PDF, JPG, PNG, or DOCX — max 10MB</p>
            </div>

            <div className="flex gap-2 pt-1">
              <Button size="sm" variant="outline" onClick={handlePreview} loading={previewing}>
                <CalendarClock size={14} /> Preview
              </Button>
              <Button size="sm" onClick={handleSubmit} loading={submitting} disabled={!preview}>
                Submit Request
              </Button>
              <Button size="sm" variant="ghost" onClick={resetForm}>Cancel</Button>
            </div>

            {preview && (
              <div className="rounded-lg border bg-muted/30 p-4 space-y-2 text-sm animate-in fade-in duration-200">
                <div className="flex flex-wrap gap-x-6 gap-y-1.5">
                  <span><span className="text-muted-foreground">Working days:</span> <span className="font-medium text-foreground">{Number(preview.working_days_count).toFixed(2)}</span></span>
                  {preview.current_balance !== null && (
                    <span><span className="text-muted-foreground">Balance after:</span> <span className="font-medium text-foreground">{Number(preview.current_balance).toFixed(2)} → {Number(preview.balance_after).toFixed(2)}</span></span>
                  )}
                  {preview.holidays_in_range?.length > 0 && (
                    <span><span className="text-muted-foreground">Holidays in range:</span> <span className="font-medium text-foreground">{preview.holidays_in_range.length}</span></span>
                  )}
                </div>
                {preview.warnings?.length > 0 && (
                  <ul className="space-y-1 pt-1">
                    {preview.warnings.map((w: string, i: number) => (
                      <li key={i} className="flex items-start gap-1.5 text-amber-700">
                        <AlertTriangle size={13} className="mt-0.5 shrink-0" /> {w}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Request history */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>My Requests</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {requests.length === 0 ? (
            <EmptyState
              icon={Plane}
              title="No leave requests yet"
              description='Click "Apply Leave" above to submit your first request.'
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/40">
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Dates</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Type</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Days</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Reason</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Status</th>
                    <th className="px-6 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {requests.map((r: any) => {
                    const type = leaveTypes.find(t => t.id === r.leave_type_id)
                    return (
                      <tr key={r.id} className="border-b last:border-0 hover:bg-muted/40 transition-colors">
                        <td className="px-6 py-3.5 text-muted-foreground whitespace-nowrap">
                          {formatDate(r.start_date)}{r.end_date !== r.start_date && ` – ${formatDate(r.end_date)}`}
                        </td>
                        <td className="px-6 py-3.5 font-medium text-foreground">{type?.display_name || `#${r.leave_type_id}`}</td>
                        <td className="px-6 py-3.5 text-foreground tabular-nums">{Number(r.working_days_count).toFixed(2)}</td>
                        <td className="px-6 py-3.5 text-muted-foreground max-w-[220px] truncate">{r.reason}</td>
                        <td className="px-6 py-3.5"><Badge variant={STATUS_VARIANT[r.status]} dot>{r.status}</Badge></td>
                        <td className="px-6 py-3.5 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-2">
                            {r.attachment_path && (
                              <button onClick={() => handleDownload(r.id, r.attachment_path.split('/').pop())}
                                className="text-muted-foreground hover:text-nebula-600 transition-colors" title="Download attachment">
                                <Download size={14} />
                              </button>
                            )}
                            {r.status === 'pending' && (
                              <button onClick={() => handleCancel(r.id)}
                                className="text-muted-foreground hover:text-destructive transition-colors" title="Cancel request">
                                <X size={14} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
