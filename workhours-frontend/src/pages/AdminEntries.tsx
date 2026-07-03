import { useEffect, useState } from 'react'
import { getEntries, approveEntry, rejectEntry, deleteEntry } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, Badge, Select, SelectTrigger, SelectValue, SelectContent, SelectItem, Label, Textarea } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { UserAvatar } from '@/components/ui/avatar'
import { TableSkeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { RefreshCw, Check, X, Trash2, Download, Inbox } from 'lucide-react'
import { formatDate } from '@/lib/utils'

const STATUS_VARIANT: Record<string, any> = {
  pending: 'pending', approved: 'success', rejected: 'destructive'
}

export default function AdminEntries() {
  const { toast } = useToast()
  const [entries, setEntries] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('all')
  const [rejectDialog, setRejectDialog] = useState<any>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const params: any = { page: 1, size: 100 }
      if (statusFilter !== 'all') params.status = statusFilter
      const res = await getEntries(params)
      setEntries(res.data.items)
      setTotal(res.data.total)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [statusFilter])

  const handleApprove = async (id: number) => {
    setActionLoading(id)
    try {
      await approveEntry(id)
      toast('Entry approved')
      load()
    } catch { toast('Failed to approve', 'error') }
    finally { setActionLoading(null) }
  }

  const handleReject = async () => {
    if (!rejectReason.trim()) { toast('Reason is required', 'error'); return }
    setActionLoading(rejectDialog.id)
    try {
      await rejectEntry(rejectDialog.id, rejectReason)
      toast('Entry rejected')
      setRejectDialog(null); setRejectReason(''); load()
    } catch { toast('Failed to reject', 'error') }
    finally { setActionLoading(null) }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this entry? This cannot be undone.')) return
    setActionLoading(id)
    try {
      await deleteEntry(id)
      toast('Entry deleted')
      load()
    } catch { toast('Failed to delete', 'error') }
    finally { setActionLoading(null) }
  }

  return (
    <div className="p-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">All Entries</h1>
          <p className="text-sm text-muted-foreground mt-1">{total} total submissions</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
          <Button variant="outline" size="sm" onClick={() => window.open('/api/v1/reports/export', '_blank')}>
            <Download size={14} /> Export CSV
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <TableSkeleton rows={6} cols={7} />
          ) : entries.length === 0 ? (
            <EmptyState icon={Inbox} title="No entries match this filter" description="Try switching the status filter above." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/40">
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Employee</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Project</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Date</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Hours</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Remarks</th>
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
                      <td className="px-5 py-3.5 text-muted-foreground max-w-[160px] truncate">{e.remarks || '—'}</td>
                      <td className="px-5 py-3.5"><Badge variant={STATUS_VARIANT[e.status]} dot>{e.status}</Badge></td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center justify-end gap-1">
                          {e.status === 'pending' && (
                            <>
                              <button
                                onClick={() => handleApprove(e.id)}
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
                            onClick={() => handleDelete(e.id)}
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

      {/* Reject dialog */}
      <Dialog open={!!rejectDialog} onOpenChange={open => !open && setRejectDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject entry</DialogTitle>
            <DialogDescription>
              {rejectDialog && `${rejectDialog.employee_username} · ${rejectDialog.project_name} · ${rejectDialog.hours_worked}h`}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label>Reason <span className="text-destructive">*</span></Label>
            <Textarea
              placeholder="Explain why this entry is being rejected..."
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setRejectDialog(null)}>Cancel</Button>
            <Button variant="destructive" size="sm" onClick={handleReject}
              loading={actionLoading === rejectDialog?.id}>
              Reject Entry
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
