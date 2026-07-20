import { useEffect, useState } from 'react'
import { useToast } from '@/hooks/useToast'
import {
  getLeaveTypes, getPendingLeaveRequests, approveLeaveRequest, rejectLeaveRequest,
  bulkApproveLeaveRequests, bulkRejectLeaveRequests, getEmployeeLeaveHistory, getEmployeeLeaveBalances,
  exportLeaveRequestsCsv, downloadLeaveAttachment
} from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, Badge, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { TableSkeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import LeaveCalendarWidget from '@/components/LeaveCalendarWidget'
import {
  RefreshCw, Check, X, Paperclip, ClipboardList,
  Download as DownloadIcon, Eye, Wallet, History, CalendarClock, PieChart
} from 'lucide-react'
import { formatDate, titleCase } from '@/lib/utils'

const STATUS_VARIANT: Record<string, any> = {
  pending: 'pending', approved: 'success', rejected: 'destructive', cancelled: 'secondary'
}

// PM req #4: status values render in title case regardless of the raw
// lowercase value the API returns (pending/approved/rejected/cancelled).

export default function AdminLeaveQueue() {
  const { toast } = useToast()

  const [loading, setLoading] = useState(true)
  const [leaveTypes, setLeaveTypes] = useState<any[]>([])
  const [requests, setRequests] = useState<any[]>([])

  const [filterLeaveTypeId, setFilterLeaveTypeId] = useState('')
  const [filterDateFrom, setFilterDateFrom] = useState('')
  const [filterDateTo, setFilterDateTo] = useState('')

  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [bulkComment, setBulkComment] = useState('')
  const [bulkSubmitting, setBulkSubmitting] = useState(false)

  // Confirmation dialog state — a real modal now (PM req #3), not an
  // inline expand-row. `action` distinguishes which one is open;
  // `comment` is required for reject, optional for approve.
  const [confirmAction, setConfirmAction] = useState<{ id: number; type: 'approve' | 'reject' } | null>(null)
  const [confirmComment, setConfirmComment] = useState('')
  const [confirmSubmitting, setConfirmSubmitting] = useState(false)

  // Wallet popup state (PM req #3 — replaces the old generic
  // employee-ID-lookup panel entirely; each row now has its own Eye icon).
  const [walletEmployee, setWalletEmployee] = useState<{ id: number; label: string } | null>(null)
  const [walletLoading, setWalletLoading] = useState(false)
  const [walletBalances, setWalletBalances] = useState<any[] | null>(null)
  const [walletHistory, setWalletHistory] = useState<any[] | null>(null)

  const [exporting, setExporting] = useState(false)

  const errMsg = (err: any, fallback: string) => {
    const detail = err.response?.data?.detail
    if (Array.isArray(detail)) return detail[0]?.msg || fallback
    return detail || fallback
  }

  const buildFilterParams = () => {
    const params: Record<string, any> = {}
    if (filterLeaveTypeId) params.leave_type_id = parseInt(filterLeaveTypeId)
    if (filterDateFrom) params.date_from = filterDateFrom
    if (filterDateTo) params.date_to = filterDateTo
    return params
  }

  const load = async () => {
    setLoading(true)
    try {
      const [typesRes, pendingRes] = await Promise.all([
        getLeaveTypes(),
        getPendingLeaveRequests(buildFilterParams()),
      ])
      setLeaveTypes(typesRes.data)
      // Backend now sorts latest-first by default (PM req #3) — no client
      // re-sort needed, just render in the order the API returns.
      const items = Array.isArray(pendingRes.data) ? pendingRes.data : (pendingRes.data?.items ?? [])
      setRequests(items)
      setSelected(new Set())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    setSelected(prev => (prev.size === requests.length ? new Set() : new Set(requests.map(r => r.id))))
  }

  const openConfirm = (id: number, type: 'approve' | 'reject') => {
    setConfirmAction({ id, type })
    setConfirmComment('')
  }

  const handleConfirmSubmit = async () => {
    if (!confirmAction) return
    if (confirmAction.type === 'reject' && !confirmComment.trim()) {
      toast('A comment is required to reject a request', 'error'); return
    }
    setConfirmSubmitting(true)
    try {
      if (confirmAction.type === 'approve') {
        await approveLeaveRequest(confirmAction.id, confirmComment.trim() || undefined)
        toast('Leave request approved')
      } else {
        await rejectLeaveRequest(confirmAction.id, confirmComment.trim())
        toast('Leave request rejected')
      }
      setConfirmAction(null)
      setConfirmComment('')
      load()
    } catch (err: any) {
      toast(errMsg(err, `Failed to ${confirmAction.type} request`), 'error')
    } finally {
      setConfirmSubmitting(false)
    }
  }

  const handleBulkApprove = async () => {
    if (selected.size === 0) return
    setBulkSubmitting(true)
    try {
      await bulkApproveLeaveRequests(Array.from(selected), bulkComment.trim() || undefined)
      toast(`${selected.size} request(s) approved`)
      setBulkComment('')
      load()
    } catch (err: any) {
      toast(errMsg(err, 'Failed to bulk approve'), 'error')
    } finally {
      setBulkSubmitting(false)
    }
  }

  // Bulk reject (PM req #9) — unlike bulk approve, the backend requires a
  // reason (BulkRejectRequest.admin_comment, min_length 3), mirroring the
  // single-reject flow's LeaveRejectRequest. Validated client-side first so
  // the error shows as a toast rather than a raw 422 from the API.
  const handleBulkReject = async () => {
    if (selected.size === 0) return
    if (bulkComment.trim().length < 3) {
      toast('A comment (min. 3 characters) is required to reject', 'error')
      return
    }
    setBulkSubmitting(true)
    try {
      const res = await bulkRejectLeaveRequests(Array.from(selected), bulkComment.trim())
      toast(`${res.data.rejected_count} request(s) rejected${res.data.failed_count ? `, ${res.data.failed_count} failed` : ''}`)
      setBulkComment('')
      load()
    } catch (err: any) {
      toast(errMsg(err, 'Failed to bulk reject'), 'error')
    } finally {
      setBulkSubmitting(false)
    }
  }

  const handleDownloadAttachment = async (id: number, filename: string) => {
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

  const handleExport = async () => {
    setExporting(true)
    try {
      const res = await exportLeaveRequestsCsv(buildFilterParams())
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `leave-requests-${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
      toast('Export downloaded')
    } catch (err: any) {
      toast(errMsg(err, 'Failed to export'), 'error')
    } finally {
      setExporting(false)
    }
  }

  const openWallet = async (employeeId: number, label: string) => {
    setWalletEmployee({ id: employeeId, label })
    setWalletLoading(true)
    setWalletBalances(null)
    setWalletHistory(null)
    try {
      const [balancesRes, historyRes] = await Promise.all([
        getEmployeeLeaveBalances(employeeId),
        getEmployeeLeaveHistory(employeeId, { page: 1, size: 20 }),
      ])
      setWalletBalances(balancesRes.data)
      const items = Array.isArray(historyRes.data) ? historyRes.data : (historyRes.data?.items ?? [])
      setWalletHistory(items)
    } catch (err: any) {
      toast(errMsg(err, 'Failed to load employee leave wallet'), 'error')
      setWalletBalances([])
      setWalletHistory([])
    } finally {
      setWalletLoading(false)
    }
  }

  // Most recent APPROVED request — "last leave taken" means leave actually
  // used, not just requested; pending/rejected/cancelled don't count.
  const lastLeaveTaken = walletHistory?.find(r => r.status === 'approved') ?? null

  if (loading) return (
    <div className="p-8 max-w-6xl">
      <div className="h-8 w-64 bg-muted rounded animate-pulse mb-1.5" />
      <div className="h-4 w-80 bg-muted rounded animate-pulse mb-6" />
      <Card><TableSkeleton rows={5} cols={7} /></Card>
    </div>
  )

  return (
    <div className="p-8 max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">Leave Approvals</h1>
          <p className="text-sm text-muted-foreground mt-1">Review, approve, or reject pending leave requests</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleExport} loading={exporting}>
            <DownloadIcon size={14} /> Export CSV
          </Button>
          <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
        </div>
      </div>

      <div className="flex gap-6 items-start">
        {/* Main column */}
        <div className="flex-1 min-w-0">
          {/* Filters */}
          <Card className="mb-4">
            <CardContent className="p-4 flex flex-wrap gap-3 items-end">
              <div className="space-y-1.5 w-48">
                <Label className="text-xs">Leave Type</Label>
                <Select value={filterLeaveTypeId} onValueChange={setFilterLeaveTypeId}>
                  <SelectTrigger><SelectValue placeholder="All types" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All types</SelectItem>
                    {leaveTypes.map(t => <SelectItem key={t.id} value={String(t.id)}>{t.display_name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">From</Label>
                <input type="date" value={filterDateFrom} onChange={e => setFilterDateFrom(e.target.value)}
                  className="h-9 px-3 rounded-md border border-input bg-background text-sm" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">To</Label>
                <input type="date" value={filterDateTo} onChange={e => setFilterDateTo(e.target.value)}
                  className="h-9 px-3 rounded-md border border-input bg-background text-sm" />
              </div>
              <Button size="sm" variant="outline" onClick={load}>Apply Filters</Button>
              {(filterLeaveTypeId || filterDateFrom || filterDateTo) && (
                <Button size="sm" variant="ghost" onClick={() => { setFilterLeaveTypeId(''); setFilterDateFrom(''); setFilterDateTo(''); load() }}>
                  Clear
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Bulk approve bar */}
          {selected.size > 0 && (
            <Card className="mb-4 border-nebula-200 animate-in fade-in duration-150">
              <CardContent className="p-4 flex items-center gap-3">
                <span className="text-sm font-medium text-foreground">{selected.size} selected</span>
                <input
                  value={bulkComment}
                  onChange={e => setBulkComment(e.target.value)}
                  placeholder="Optional comment for all…"
                  className="flex-1 h-9 px-3 rounded-md border border-input bg-background text-sm"
                />
                <Button size="sm" onClick={handleBulkApprove} loading={bulkSubmitting}>
                  <Check size={14} /> Approve Selected
                </Button>
                <Button size="sm" variant="destructive" onClick={handleBulkReject} loading={bulkSubmitting}>
                  <X size={14} /> Reject Selected
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>Clear</Button>
              </CardContent>
            </Card>
          )}

          {/* Pending queue */}
          <Card>
            <CardHeader className="pb-3"><CardTitle>Pending Requests</CardTitle></CardHeader>
            <CardContent className="p-0">
              {requests.length === 0 ? (
                <EmptyState icon={ClipboardList} title="No pending requests" description="You're all caught up." />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/40">
                        <th className="px-4 py-3 w-10">
                          <input type="checkbox" checked={selected.size === requests.length && requests.length > 0}
                            onChange={toggleSelectAll} className="rounded border-input" />
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Employee</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Dates</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Type</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Days</th>
                        <th className="px-4 py-3 w-10" />
                        <th className="px-4 py-3 w-10" />
                        <th className="px-4 py-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {requests.map((r: any) => {
                        const type = leaveTypes.find(t => t.id === r.leave_type_id)
                        const employeeLabel = r.employee?.username || `Employee #${r.employee_id}`
                        return (
                          <tr key={r.id} className="border-b last:border-0 hover:bg-muted/40 transition-colors align-top">
                            <td className="px-4 py-3.5">
                              <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleSelect(r.id)}
                                className="rounded border-input" />
                            </td>
                            <td className="px-4 py-3.5 font-medium text-foreground whitespace-nowrap">{employeeLabel}</td>
                            <td className="px-4 py-3.5 text-muted-foreground whitespace-nowrap">
                              {formatDate(r.start_date)}{r.end_date !== r.start_date && ` – ${formatDate(r.end_date)}`}
                            </td>
                            <td className="px-4 py-3.5 text-foreground whitespace-nowrap">{type?.display_name || `#${r.leave_type_id}`}</td>
                            <td className="px-4 py-3.5 tabular-nums">{Number(r.working_days_count).toFixed(2)}</td>
                            <td className="px-4 py-3.5">
                              {r.attachment_path && (
                                <button onClick={() => handleDownloadAttachment(r.id, r.attachment_path.split('/').pop())}
                                  className="text-muted-foreground hover:text-nebula-600 transition-colors" title="Download attachment">
                                  <Paperclip size={14} />
                                </button>
                              )}
                            </td>
                            <td className="px-4 py-3.5">
                              {/* Eye icon → per-employee leave wallet popup (PM req #3), replaces the old
                                  generic "type an ID" lookup and the long inline reason text. */}
                              <button onClick={() => openWallet(r.employee_id, employeeLabel)}
                                className="text-muted-foreground hover:text-nebula-600 transition-colors" title="View leave wallet & reason">
                                <Eye size={14} />
                              </button>
                            </td>
                            <td className="px-4 py-3.5 text-right whitespace-nowrap">
                              <div className="flex items-center justify-end gap-1.5">
                                <Button size="sm" variant="outline" onClick={() => openConfirm(r.id, 'approve')}>
                                  <Check size={13} /> Approve
                                </Button>
                                <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive"
                                  onClick={() => openConfirm(r.id, 'reject')}>
                                  <X size={13} /> Reject
                                </Button>
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

        {/* Sidebar: compact leave calendar, always visible (PM req #3) */}
        <div className="w-72 shrink-0 hidden lg:block sticky top-4">
          <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1.5">
            <CalendarClock size={12} /> Leave Calendar
          </p>
          <LeaveCalendarWidget compact />
        </div>
      </div>

      {/* Confirmation dialog — real modal (PM req #3), replaces the old inline expand-row */}
      <Dialog open={!!confirmAction} onOpenChange={(open: boolean) => { if (!open) setConfirmAction(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {confirmAction?.type === 'approve' ? 'Approve this leave request?' : 'Reject this leave request?'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {confirmAction?.type === 'approve'
                ? 'This will mark the request as Approved and notify the employee. This action cannot be undone from here.'
                : 'This will mark the request as Rejected and notify the employee. A reason is required.'}
            </p>
            <div className="space-y-1.5">
              <Label>{confirmAction?.type === 'reject' ? 'Reason (required)' : 'Comment (optional)'}</Label>
              <input
                value={confirmComment}
                onChange={e => setConfirmComment(e.target.value)}
                placeholder={confirmAction?.type === 'reject' ? 'Why is this being rejected…' : 'Optional comment…'}
                className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setConfirmAction(null)}>Cancel</Button>
            <Button
              size="sm"
              variant={confirmAction?.type === 'reject' ? 'destructive' : 'default'}
              onClick={handleConfirmSubmit}
              loading={confirmSubmitting}
            >
              {confirmAction?.type === 'approve' ? 'Confirm Approve' : 'Confirm Reject'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Employee Leave Wallet popup (PM req #3) */}
      <Dialog open={!!walletEmployee} onOpenChange={(open: boolean) => { if (!open) setWalletEmployee(null) }}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Wallet size={16} className="text-nebula-600" /> {walletEmployee?.label}'s Leave Wallet
            </DialogTitle>
          </DialogHeader>
          {walletLoading ? (
            <div className="py-8 text-center text-sm text-muted-foreground">Loading…</div>
          ) : (
            <div className="space-y-5">
              {/* Remaining balance + leave type summary — same underlying
                  data (per-type credited/debited/remaining) serves both. */}
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1.5">
                  <PieChart size={12} /> Remaining Leave Balance
                </p>
                {!walletBalances || walletBalances.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No leave balances found.</p>
                ) : (
                  <div className="grid grid-cols-2 gap-2">
                    {walletBalances.map((b: any) => (
                      <div key={b.leave_type_id} className="rounded-lg border p-2.5">
                        <p className="text-xs text-muted-foreground">{b.leave_type_display_name}</p>
                        <p className="text-lg font-display font-semibold text-foreground tabular-nums">
                          {Number(b.remaining_days).toFixed(1)}
                          <span className="text-xs text-muted-foreground font-normal"> / {Number(b.total_credited_days).toFixed(1)}</span>
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1.5">
                  <CalendarClock size={12} /> Last Leave Taken
                </p>
                {lastLeaveTaken ? (
                  <div className="flex items-center gap-2 text-sm">
                    <Badge variant="success" dot>Approved</Badge>
                    <span className="text-foreground">
                      {formatDate(lastLeaveTaken.start_date)}
                      {lastLeaveTaken.end_date !== lastLeaveTaken.start_date && ` – ${formatDate(lastLeaveTaken.end_date)}`}
                    </span>
                    <span className="text-muted-foreground">
                      ({leaveTypes.find(t => t.id === lastLeaveTaken.leave_type_id)?.display_name || `Type #${lastLeaveTaken.leave_type_id}`})
                    </span>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No approved leave on record.</p>
                )}
              </div>

              <div>
                <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1.5">
                  <History size={12} /> Previous Leave History
                </p>
                {!walletHistory || walletHistory.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No leave requests found for this employee.</p>
                ) : (
                  <div className="space-y-1.5 max-h-52 overflow-y-auto">
                    {walletHistory.map((r: any) => {
                      const type = leaveTypes.find(t => t.id === r.leave_type_id)
                      return (
                        <div key={r.id} className="flex items-center justify-between text-xs py-1.5 border-b last:border-0">
                          <span className="text-foreground">
                            {formatDate(r.start_date)}{r.end_date !== r.start_date && ` – ${formatDate(r.end_date)}`}
                          </span>
                          <span className="text-muted-foreground">{type?.display_name || `#${r.leave_type_id}`}</span>
                          <Badge variant={STATUS_VARIANT[r.status]} dot>{titleCase(r.status)}</Badge>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
