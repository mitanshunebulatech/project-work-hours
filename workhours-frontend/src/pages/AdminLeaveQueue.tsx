import { useEffect, useState } from 'react'
import { useToast } from '@/hooks/useToast'
import {
  getLeaveTypes, getPendingLeaveRequests, approveLeaveRequest, rejectLeaveRequest,
  bulkApproveLeaveRequests, getEmployeeLeaveHistory, getLeaveStatistics, exportLeaveRequestsCsv,
  downloadLeaveAttachment
} from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, Badge, Label, Select, SelectTrigger, SelectValue, SelectContent, SelectItem, Textarea } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { TableSkeleton, CardGridSkeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import {
  RefreshCw, Check, X, Paperclip, Download, ClipboardList,
  Search, Download as DownloadIcon, Users, BarChart3
} from 'lucide-react'
import { formatDate } from '@/lib/utils'

const STATUS_VARIANT: Record<string, any> = {
  pending: 'pending', approved: 'success', rejected: 'destructive', cancelled: 'secondary'
}

export default function AdminLeaveQueue() {
  const { toast } = useToast()

  const [loading, setLoading] = useState(true)
  const [leaveTypes, setLeaveTypes] = useState<any[]>([])
  const [requests, setRequests] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)

  // Filters — leave_type_id and date_from/date_to are all now real backend
  // params on /leave-requests/pending. There is still no "all requests, any
  // status" endpoint — only /leave-requests/pending (fixed to pending) — so
  // this filters *within* pending, not across all statuses.
  const [filterLeaveTypeId, setFilterLeaveTypeId] = useState('')
  const [filterDateFrom, setFilterDateFrom] = useState('')
  const [filterDateTo, setFilterDateTo] = useState('')

  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [bulkComment, setBulkComment] = useState('')
  const [bulkSubmitting, setBulkSubmitting] = useState(false)

  const [approvingId, setApprovingId] = useState<number | null>(null)
  const [approveComment, setApproveComment] = useState('')
  const [rejectingId, setRejectingId] = useState<number | null>(null)
  const [rejectComment, setRejectComment] = useState('')
  const [rowSubmitting, setRowSubmitting] = useState<number | null>(null)

  const [historyOpen, setHistoryOpen] = useState(false)
  const [historyEmployeeId, setHistoryEmployeeId] = useState('')
  const [historyResults, setHistoryResults] = useState<any[] | null>(null)
  const [historyLoading, setHistoryLoading] = useState(false)

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
      const [typesRes, pendingRes, statsRes] = await Promise.all([
        getLeaveTypes(),
        getPendingLeaveRequests(buildFilterParams()),
        getLeaveStatistics(buildFilterParams()).catch(() => ({ data: null })) // stats view is a bonus, don't block the queue if it 404s
      ])
      setLeaveTypes(typesRes.data)
      const items = Array.isArray(pendingRes.data) ? pendingRes.data : (pendingRes.data?.items ?? [])
      setRequests(items)
      setStats(statsRes.data)
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

  const handleApprove = async (id: number) => {
    setRowSubmitting(id)
    try {
      await approveLeaveRequest(id, approveComment.trim() || undefined)
      toast('Leave request approved')
      setApprovingId(null)
      setApproveComment('')
      load()
    } catch (err: any) {
      toast(errMsg(err, 'Failed to approve request'), 'error')
    } finally {
      setRowSubmitting(null)
    }
  }

  const handleReject = async (id: number) => {
    if (!rejectComment.trim()) {
      toast('A comment is required to reject a request', 'error'); return
    }
    setRowSubmitting(id)
    try {
      await rejectLeaveRequest(id, rejectComment.trim())
      toast('Leave request rejected')
      setRejectingId(null)
      setRejectComment('')
      load()
    } catch (err: any) {
      toast(errMsg(err, 'Failed to reject request'), 'error')
    } finally {
      setRowSubmitting(null)
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

  const handleLoadHistory = async () => {
    const id = parseInt(historyEmployeeId)
    if (!id || isNaN(id)) {
      toast('Enter a valid employee ID', 'error'); return
    }
    setHistoryLoading(true)
    setHistoryResults(null)
    try {
      const res = await getEmployeeLeaveHistory(id, { page: 1, size: 50 })
      const items = Array.isArray(res.data) ? res.data : (res.data?.items ?? [])
      setHistoryResults(items)
    } catch (err: any) {
      toast(errMsg(err, 'Failed to load employee history'), 'error')
      setHistoryResults([])
    } finally {
      setHistoryLoading(false)
    }
  }

  if (loading) return (
    <div className="p-8 max-w-6xl">
      <div className="h-8 w-64 bg-muted rounded animate-pulse mb-1.5" />
      <div className="h-4 w-80 bg-muted rounded animate-pulse mb-6" />
      <div className="mb-6"><CardGridSkeleton count={2} /></div>
      <Card><TableSkeleton rows={5} cols={7} /></Card>
    </div>
  )

  return (
    <div className="p-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">Leave Approvals</h1>
          <p className="text-sm text-muted-foreground mt-1">Review, approve, or reject pending leave requests</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setHistoryOpen(o => !o)}>
            <Users size={14} /> Employee History
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport} loading={exporting}>
            <DownloadIcon size={14} /> Export CSV
          </Button>
          <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="p-5">
              <p className="text-xs font-medium text-muted-foreground mb-1.5 flex items-center gap-1.5"><BarChart3 size={12} /> Total Requests</p>
              <p className="text-2xl font-display font-bold text-foreground tabular-nums">{stats.total_requests ?? '—'}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-xs font-medium text-muted-foreground mb-1.5">Total Days</p>
              <p className="text-2xl font-display font-bold text-foreground tabular-nums">
                {stats.total_days !== undefined ? Number(stats.total_days).toFixed(1) : '—'}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Employee history lookup */}
      {historyOpen && (
        <Card className="mb-6 animate-in fade-in slide-in-from-top-1 duration-200">
          <CardHeader className="pb-3"><CardTitle>Employee Leave History</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2 items-end">
              <div className="flex-1 max-w-xs space-y-1.5">
                <Label>Employee ID</Label>
                <input
                  type="number"
                  value={historyEmployeeId}
                  onChange={e => setHistoryEmployeeId(e.target.value)}
                  placeholder="e.g. 4"
                  className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm"
                />
              </div>
              <Button size="sm" onClick={handleLoadHistory} loading={historyLoading}>
                <Search size={14} /> Look Up
              </Button>
            </div>
            {historyResults && (
              historyResults.length === 0 ? (
                <p className="text-sm text-muted-foreground">No leave requests found for this employee.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/40">
                        <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Dates</th>
                        <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Type</th>
                        <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Days</th>
                        <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {historyResults.map((r: any) => {
                        const type = leaveTypes.find(t => t.id === r.leave_type_id)
                        return (
                          <tr key={r.id} className="border-b last:border-0">
                            <td className="px-4 py-2.5 text-muted-foreground whitespace-nowrap">
                              {formatDate(r.start_date)}{r.end_date !== r.start_date && ` – ${formatDate(r.end_date)}`}
                            </td>
                            <td className="px-4 py-2.5 text-foreground">{type?.display_name || `#${r.leave_type_id}`}</td>
                            <td className="px-4 py-2.5 tabular-nums">{Number(r.working_days_count).toFixed(2)}</td>
                            <td className="px-4 py-2.5"><Badge variant={STATUS_VARIANT[r.status]} dot>{r.status}</Badge></td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )
            )}
          </CardContent>
        </Card>
      )}

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
                    <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Reason</th>
                    <th className="px-4 py-3 w-10" />
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {requests.map((r: any) => {
                    const type = leaveTypes.find(t => t.id === r.leave_type_id)
                    // Backend now eager-loads and serializes r.employee (see
                    // EmployeeBrief in leave_request.py schema) — falls back
                    // to a bare ID only if that's ever missing.
                    const employeeLabel = r.employee?.username || `Employee #${r.employee_id}`
                    return (
                      <>
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
                          <td className="px-4 py-3.5 text-muted-foreground max-w-[240px]">
                            <span className="line-clamp-2">{r.reason}</span>
                          </td>
                          <td className="px-4 py-3.5">
                            {r.attachment_path && (
                              <button onClick={() => handleDownloadAttachment(r.id, r.attachment_path.split('/').pop())}
                                className="text-muted-foreground hover:text-nebula-600 transition-colors" title="Download attachment">
                                <Paperclip size={14} />
                              </button>
                            )}
                          </td>
                          <td className="px-4 py-3.5 text-right whitespace-nowrap">
                            <div className="flex items-center justify-end gap-1.5">
                              <Button size="sm" variant="outline" onClick={() => { setApprovingId(approvingId === r.id ? null : r.id); setRejectingId(null) }}>
                                <Check size={13} /> Approve
                              </Button>
                              <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive"
                                onClick={() => { setRejectingId(rejectingId === r.id ? null : r.id); setApprovingId(null) }}>
                                <X size={13} /> Reject
                              </Button>
                            </div>
                          </td>
                        </tr>
                        {approvingId === r.id && (
                          <tr className="border-b bg-muted/20">
                            <td colSpan={8} className="px-4 py-3">
                              <div className="flex items-center gap-2 max-w-lg">
                                <input
                                  value={approveComment}
                                  onChange={e => setApproveComment(e.target.value)}
                                  placeholder="Optional comment…"
                                  className="flex-1 h-8 px-3 rounded-md border border-input bg-background text-sm"
                                />
                                <Button size="sm" onClick={() => handleApprove(r.id)} loading={rowSubmitting === r.id}>Confirm Approve</Button>
                                <Button size="sm" variant="ghost" onClick={() => { setApprovingId(null); setApproveComment('') }}>Cancel</Button>
                              </div>
                            </td>
                          </tr>
                        )}
                        {rejectingId === r.id && (
                          <tr className="border-b bg-destructive/5">
                            <td colSpan={8} className="px-4 py-3">
                              <div className="flex items-center gap-2 max-w-lg">
                                <input
                                  value={rejectComment}
                                  onChange={e => setRejectComment(e.target.value)}
                                  placeholder="Reason for rejection (required)…"
                                  className="flex-1 h-8 px-3 rounded-md border border-input bg-background text-sm"
                                />
                                <Button size="sm" variant="destructive" onClick={() => handleReject(r.id)} loading={rowSubmitting === r.id}>Confirm Reject</Button>
                                <Button size="sm" variant="ghost" onClick={() => { setRejectingId(null); setRejectComment('') }}>Cancel</Button>
                              </div>
                            </td>
                          </tr>
                        )}
                      </>
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
