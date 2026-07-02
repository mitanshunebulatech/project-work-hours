import { useEffect, useState } from 'react'
import { getEntries, approveEntry, rejectEntry, deleteEntry } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, CardHeader, CardTitle, Badge, Select, SelectTrigger, SelectValue, SelectContent, SelectItem, Label, Textarea } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { RefreshCw, Check, X, Trash2 } from 'lucide-react'
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
          <h1 className="text-xl font-semibold text-slate-900">All Entries</h1>
          <p className="text-sm text-slate-500 mt-0.5">{total} total submissions</p>
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
            Export CSV
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-3">
              {[1,2,3,4,5].map(i => <div key={i} className="h-10 bg-slate-100 rounded animate-pulse" />)}
            </div>
          ) : entries.length === 0 ? (
            <div className="px-6 py-12 text-center text-sm text-slate-400">No entries match this filter.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-slate-50">
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Employee</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Project</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Date</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Hours</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Remarks</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Status</th>
                  <th className="px-5 py-3 text-right text-xs font-medium text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e: any) => (
                  <tr key={e.id} className="border-b last:border-0 hover:bg-slate-50 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-slate-900">{e.employee_username}</td>
                    <td className="px-5 py-3.5 text-slate-700">{e.project_name}</td>
                    <td className="px-5 py-3.5 text-slate-600 whitespace-nowrap">{formatDate(e.entry_date)}</td>
                    <td className="px-5 py-3.5 font-medium text-slate-900">{e.hours_worked}h</td>
                    <td className="px-5 py-3.5 text-slate-500 max-w-[160px] truncate">{e.remarks || '—'}</td>
                    <td className="px-5 py-3.5"><Badge variant={STATUS_VARIANT[e.status]}>{e.status}</Badge></td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center justify-end gap-1">
                        {e.status === 'pending' && (
                          <>
                            <button
                              onClick={() => handleApprove(e.id)}
                              disabled={actionLoading === e.id}
                              className="p-1.5 rounded hover:bg-emerald-50 text-slate-400 hover:text-emerald-600 transition-colors"
                              title="Approve"
                            >
                              <Check size={14} />
                            </button>
                            <button
                              onClick={() => { setRejectDialog(e); setRejectReason('') }}
                              disabled={actionLoading === e.id}
                              className="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors"
                              title="Reject"
                            >
                              <X size={14} />
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => handleDelete(e.id)}
                          disabled={actionLoading === e.id}
                          className="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors"
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
          )}
        </CardContent>
      </Card>

      {/* Reject dialog */}
      {rejectDialog && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-base font-semibold text-slate-900 mb-1">Reject entry</h2>
            <p className="text-sm text-slate-500 mb-4">
              {rejectDialog.employee_username} · {rejectDialog.project_name} · {rejectDialog.hours_worked}h
            </p>
            <div className="space-y-1.5 mb-4">
              <Label>Reason <span className="text-red-500">*</span></Label>
              <Textarea
                placeholder="Explain why this entry is being rejected..."
                value={rejectReason}
                onChange={e => setRejectReason(e.target.value)}
                rows={3}
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => setRejectDialog(null)}>Cancel</Button>
              <Button variant="destructive" size="sm" onClick={handleReject}
                disabled={actionLoading === rejectDialog.id}>
                {actionLoading === rejectDialog.id ? 'Rejecting...' : 'Reject Entry'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
