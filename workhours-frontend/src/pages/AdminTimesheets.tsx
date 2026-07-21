import { useEffect, useMemo, useState } from 'react'
import {
  getEntries, approveEntry, rejectEntry, deleteEntry, exportEntriesCsv, getUsers, getProjects,
} from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, Badge, Select, SelectTrigger, SelectValue, SelectContent, SelectItem, Label, Textarea } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { UserAvatar } from '@/components/ui/avatar'
import { TableSkeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { SingleDatePicker } from '@/components/ui/date-picker'
import { MultiSelectPopover, type MultiSelectOption } from '@/components/ui/multi-select-popover'
import { RefreshCw, Check, X, Trash2, Download, Inbox, Eye, Search } from 'lucide-react'
import { formatDate, toApiDateString, titleCase } from '@/lib/utils'

const STATUS_VARIANT: Record<string, any> = {
  pending: 'pending', approved: 'success', rejected: 'destructive'
}

export default function AdminTimesheets() {
  const { toast } = useToast()
  const [entries, setEntries] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  const [selectedDate, setSelectedDate] = useState<Date>(new Date())
  const [statusFilter, setStatusFilter] = useState('all')
  const [employeeIds, setEmployeeIds] = useState<number[]>([])
  const [projectIds, setProjectIds] = useState<number[]>([])
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')

  const [employeeOptions, setEmployeeOptions] = useState<MultiSelectOption[]>([])
  const [projectOptions, setProjectOptions] = useState<MultiSelectOption[]>([])

  const [remarksDialog, setRemarksDialog] = useState<any>(null)
  const [approveDialog, setApproveDialog] = useState<any>(null)
  const [rejectDialog, setRejectDialog] = useState<any>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [deleteDialog, setDeleteDialog] = useState<any>(null)
  const [actionLoading, setActionLoading] = useState<number | null>(null)
  const [exporting, setExporting] = useState(false)

  // Debounce the free-text search box so every keystroke doesn't refetch.
  useEffect(() => {
    const handle = setTimeout(() => setSearch(searchInput), 350)
    return () => clearTimeout(handle)
  }, [searchInput])

  // Filter option lists — fetched once; independent of the date/status filters.
  useEffect(() => {
    (async () => {
      try {
        const [usersRes, projectsRes] = await Promise.all([
          getUsers({ size: 100, is_active: true }),
          getProjects({ size: 100, is_active: true }),
        ])
        setEmployeeOptions(
          usersRes.data.items.map((u: any) => ({ value: u.id, label: u.username }))
        )
        setProjectOptions(
          projectsRes.data.items.map((p: any) => ({ value: p.id, label: p.project_name }))
        )
      } catch {
        // Non-fatal — filters just show empty option lists if this fails.
      }
    })()
  }, [])

  const load = async () => {
    setLoading(true)
    try {
      const dateStr = toApiDateString(selectedDate)
      const params: any = { page: 1, size: 100, date_from: dateStr, date_to: dateStr }
      if (statusFilter !== 'all') params.status = statusFilter
      if (employeeIds.length > 0) params.employee_ids = employeeIds
      if (projectIds.length > 0) params.project_ids = projectIds
      if (search.trim()) params.search = search.trim()
      const res = await getEntries(params)
      setEntries(res.data.items)
      setTotal(res.data.total)
    } catch {
      toast('Failed to load timesheets', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [selectedDate, statusFilter, employeeIds, projectIds, search])

  const handleApprove = async () => {
    if (!approveDialog) return
    setActionLoading(approveDialog.id)
    try {
      await approveEntry(approveDialog.id)
      toast('Timesheet approved')
      setApproveDialog(null)
      load()
    } catch (err: any) {
      toast(err.response?.data?.detail || 'Failed to approve', 'error')
    } finally {
      setActionLoading(null)
    }
  }

  const handleReject = async () => {
    if (!rejectReason.trim()) { toast('Reason is required', 'error'); return }
    setActionLoading(rejectDialog.id)
    try {
      await rejectEntry(rejectDialog.id, rejectReason)
      toast('Timesheet rejected')
      setRejectDialog(null); setRejectReason(''); load()
    } catch { toast('Failed to reject', 'error') }
    finally { setActionLoading(null) }
  }

  const handleDelete = async () => {
    if (!deleteDialog) return
    setActionLoading(deleteDialog.id)
    try {
      await deleteEntry(deleteDialog.id)
      toast('Timesheet deleted')
      setDeleteDialog(null)
      load()
    } catch { toast('Failed to delete', 'error') }
    finally { setActionLoading(null) }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const dateStr = toApiDateString(selectedDate)
      const params: any = { date_from: dateStr, date_to: dateStr }
      if (statusFilter !== 'all') params.status = statusFilter
      if (employeeIds.length > 0) params.employee_ids = employeeIds
      if (projectIds.length > 0) params.project_ids = projectIds
      const res = await exportEntriesCsv(params)
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `timesheets_${toApiDateString(selectedDate)}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch {
      toast('Failed to export CSV', 'error')
    } finally {
      setExporting(false)
    }
  }

  const isToday = useMemo(
    () => selectedDate.toDateString() === new Date().toDateString(),
    [selectedDate]
  )

  return (
    <div className="p-8 max-w-7xl">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">Timesheets</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total} submission{total === 1 ? '' : 's'} {isToday ? 'today' : `on ${formatDate(toApiDateString(selectedDate))}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
          <Button variant="outline" size="sm" onClick={handleExport} loading={exporting}>
            <Download size={14} /> Export CSV
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <SingleDatePicker value={selectedDate} onChange={setSelectedDate} disabledAfter={new Date()} />

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
          </SelectContent>
        </Select>

        <MultiSelectPopover
          label="All employees"
          options={employeeOptions}
          selected={employeeIds}
          onChange={setEmployeeIds}
          searchPlaceholder="Search employees..."
        />

        <MultiSelectPopover
          label="All projects"
          options={projectOptions}
          selected={projectIds}
          onChange={setProjectIds}
          searchPlaceholder="Search projects..."
        />

        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            placeholder="Search employee or project..."
            className="h-9 w-56 pl-8 pr-3 text-sm rounded-md border border-input bg-background shadow-soft transition-all duration-150 hover:border-primary/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
          />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <TableSkeleton rows={6} cols={7} />
          ) : entries.length === 0 ? (
            <EmptyState
              icon={Inbox}
              title="No timesheets match this filter"
              description={isToday ? 'Nobody has logged hours yet today.' : 'Try a different date or filter combination.'}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/40">
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Employee</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Project</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Date</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Hours</th>
                    <th className="text-center px-5 py-3 text-xs font-medium text-muted-foreground">Remarks</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Status</th>
                    <th className="px-5 py-3 text-right text-xs font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((e: any) => (
                    <tr key={e.id} className="border-b last:border-0 hover:bg-muted/40 transition-colors">
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2.5">
                          <UserAvatar name={e.employee_username} size={24} />
                          <span className="font-medium text-foreground">{e.employee_username}</span>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-foreground/80">{e.project_name}</td>
                      <td className="px-5 py-3.5 text-muted-foreground whitespace-nowrap">{formatDate(e.entry_date)}</td>
                      <td className="px-5 py-3.5 font-medium text-foreground tabular-nums">{e.hours_worked}h</td>
                      <td className="px-5 py-3.5 text-center">
                        <button
                          onClick={() => setRemarksDialog(e)}
                          className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-30"
                          disabled={!e.remarks}
                          title={e.remarks ? 'View remarks' : 'No remarks'}
                        >
                          <Eye size={14} />
                        </button>
                      </td>
                      <td className="px-5 py-3.5"><Badge variant={STATUS_VARIANT[e.status]} dot>{titleCase(e.status)}</Badge></td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center justify-end gap-1">
                          {e.status === 'pending' && (
                            <>
                              <button
                                onClick={() => setApproveDialog(e)}
                                disabled={actionLoading === e.id}
                                className="p-1.5 rounded hover:bg-emerald-50 text-muted-foreground hover:text-emerald-600 transition-colors disabled:opacity-40"
                                title="Approve"
                              >
                                <Check size={14} />
                              </button>
                              <button
                                onClick={() => { setRejectDialog(e); setRejectReason('') }}
                                disabled={actionLoading === e.id}
                                className="p-1.5 rounded hover:bg-red-50 text-muted-foreground hover:text-red-600 transition-colors disabled:opacity-40"
                                title="Reject"
                              >
                                <X size={14} />
                              </button>
                            </>
                          )}
                          <button
                            onClick={() => setDeleteDialog(e)}
                            disabled={actionLoading === e.id}
                            className="p-1.5 rounded hover:bg-red-50 text-muted-foreground hover:text-red-500 transition-colors disabled:opacity-40"
                            title="Delete"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Remarks popup (Eye icon) */}
      <Dialog open={!!remarksDialog} onOpenChange={open => !open && setRemarksDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remarks</DialogTitle>
            <DialogDescription>
              {remarksDialog && `${remarksDialog.employee_username} · ${remarksDialog.project_name} · ${formatDate(remarksDialog.entry_date)}`}
            </DialogDescription>
          </DialogHeader>
          <p className="text-sm text-foreground whitespace-pre-wrap">{remarksDialog?.remarks}</p>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setRemarksDialog(null)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Approve confirmation */}
      <Dialog open={!!approveDialog} onOpenChange={open => !open && setApproveDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Approve this timesheet?</DialogTitle>
            <DialogDescription>
              {approveDialog && `${approveDialog.employee_username} · ${approveDialog.project_name} · ${approveDialog.hours_worked}h · ${formatDate(approveDialog.entry_date)}`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setApproveDialog(null)}>Cancel</Button>
            <Button variant="default" size="sm" onClick={handleApprove} loading={actionLoading === approveDialog?.id}>
              Approve
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject dialog (reason required) */}
      <Dialog open={!!rejectDialog} onOpenChange={open => !open && setRejectDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject timesheet</DialogTitle>
            <DialogDescription>
              {rejectDialog && `${rejectDialog.employee_username} · ${rejectDialog.project_name} · ${rejectDialog.hours_worked}h`}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label>Reason <span className="text-destructive">*</span></Label>
            <Textarea
              placeholder="Explain why this timesheet is being rejected..."
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setRejectDialog(null)}>Cancel</Button>
            <Button variant="destructive" size="sm" onClick={handleReject}
              loading={actionLoading === rejectDialog?.id}>
              Reject Timesheet
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation (upgraded from window.confirm — PM req #11) */}
      <Dialog open={!!deleteDialog} onOpenChange={open => !open && setDeleteDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this timesheet?</DialogTitle>
            <DialogDescription>
              {deleteDialog && `${deleteDialog.employee_username} · ${deleteDialog.project_name} · ${deleteDialog.hours_worked}h`}
              {' '}— this cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setDeleteDialog(null)}>Cancel</Button>
            <Button variant="destructive" size="sm" onClick={handleDelete} loading={actionLoading === deleteDialog?.id}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
