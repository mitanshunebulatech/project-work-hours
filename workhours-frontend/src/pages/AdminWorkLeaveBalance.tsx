import { useEffect, useState } from 'react'
import { getEmployees, getEmployeeLeaveBalances, setLeaveBalance } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import {
  Card, CardContent, CardHeader, CardTitle, Label, Select, SelectTrigger, SelectValue,
  SelectContent, SelectItem,
} from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/ui/empty-state'
import { Wallet, RefreshCw, Pencil, Check, X } from 'lucide-react'

const CURRENT_YEAR = new Date().getFullYear()

/**
 * HRMS V3 Work Leave Balance tab (Leave module split — the other half is
 * AdminLeaveQueue.tsx / Leave Approval). Admin picks an employee, sees
 * every paid leave type's current balance (CL/SL/WFH — LOP never appears
 * here, it's unpaid/unlimited by design, see
 * app/api/v1/endpoints/leave_balances.py's _balances_for_employee), and
 * can set any one of them to an absolute value via POST
 * /leave-ledger/set-balance. This is a full override, not a +/- delta —
 * WFH is still normally auto-credited monthly by WfhMonthlyGrantService;
 * this page exists for onboarding-time allocation and manual corrections,
 * not as WFH's everyday mechanism.
 */
export default function AdminWorkLeaveBalance() {
  const { toast } = useToast()
  const [employees, setEmployees] = useState<any[]>([])
  const [loadingEmployees, setLoadingEmployees] = useState(true)
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('')

  const [balances, setBalances] = useState<any[] | null>(null)
  const [loadingBalances, setLoadingBalances] = useState(false)

  const [editingTypeId, setEditingTypeId] = useState<number | null>(null)
  const [targetDays, setTargetDays] = useState('')
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    getEmployees({ page: 1, size: 200 })
      .then(res => setEmployees(res.data.items))
      .catch(() => toast('Failed to load employees', 'error'))
      .finally(() => setLoadingEmployees(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadBalances = (employeeId: string) => {
    if (!employeeId) { setBalances(null); return }
    setLoadingBalances(true)
    getEmployeeLeaveBalances(Number(employeeId), CURRENT_YEAR)
      .then(res => setBalances(res.data))
      .catch(() => toast('Failed to load leave balances', 'error'))
      .finally(() => setLoadingBalances(false))
  }

  const handleSelectEmployee = (value: string) => {
    setSelectedEmployeeId(value)
    setEditingTypeId(null)
    loadBalances(value)
  }

  const startEdit = (b: any) => {
    setEditingTypeId(b.leave_type_id)
    setTargetDays(String(b.remaining_days))
    setReason('')
  }

  const cancelEdit = () => {
    setEditingTypeId(null)
    setTargetDays('')
    setReason('')
  }

  const handleSave = async (leaveTypeId: number) => {
    if (targetDays === '' || Number(targetDays) < 0) {
      toast('Enter a valid number of days (0 or more)', 'error')
      return
    }
    setSubmitting(true)
    try {
      await setLeaveBalance({
        employee_id: Number(selectedEmployeeId),
        leave_type_id: leaveTypeId,
        year: CURRENT_YEAR,
        target_days: Number(targetDays),
        reason: reason.trim() || null,
      })
      toast('Balance updated')
      cancelEdit()
      loadBalances(selectedEmployeeId)
    } catch (err: any) {
      const msg = err.response?.data?.detail
      toast(Array.isArray(msg) ? msg[0]?.msg : (msg || 'Failed to update balance'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const employeeLabel = (e: any) => `${e.full_name}${e.employee_code ? ` · ${e.employee_code}` : ''}`

  return (
    <div className="p-8 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">Work Leave Balance</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Set an employee's leave balance directly — used at onboarding and for manual corrections.
          </p>
        </div>
        {selectedEmployeeId && (
          <Button variant="outline" size="sm" onClick={() => loadBalances(selectedEmployeeId)}>
            <RefreshCw size={14} />
          </Button>
        )}
      </div>

      <Card className="mb-4">
        <CardContent className="p-4">
          <div className="space-y-1.5 max-w-sm">
            <Label>Employee</Label>
            <Select value={selectedEmployeeId} onValueChange={handleSelectEmployee} disabled={loadingEmployees}>
              <SelectTrigger><SelectValue placeholder="Select an employee..." /></SelectTrigger>
              <SelectContent>
                {employees.map((e: any) => (
                  <SelectItem key={e.user_id} value={String(e.user_id)}>{employeeLabel(e)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {selectedEmployeeId && (
        <Card>
          <CardHeader className="pb-3"><CardTitle>{CURRENT_YEAR} Balances</CardTitle></CardHeader>
          <CardContent className="p-0">
            {loadingBalances ? (
              <div className="p-6 space-y-2">
                {[1, 2, 3].map(i => <div key={i} className="h-12 bg-muted rounded-lg animate-pulse" />)}
              </div>
            ) : !balances || balances.length === 0 ? (
              <EmptyState icon={Wallet} title="No leave types found" description="No paid leave types are configured yet." />
            ) : (
              <div className="divide-y">
                {balances.map((b: any) => (
                  <div key={b.leave_type_id} className="flex items-center justify-between px-4 py-3.5">
                    <div>
                      <p className="text-sm font-medium text-foreground">{b.leave_type_display_name}</p>
                      <p className="text-xs text-muted-foreground">
                        Credited {Number(b.total_credited_days).toFixed(1)} · Used {Number(b.total_debited_days).toFixed(1)}
                      </p>
                    </div>
                    {editingTypeId === b.leave_type_id ? (
                      <div className="flex items-center gap-2">
                        <Input
                          type="number" min="0" step="0.5" value={targetDays}
                          onChange={e => setTargetDays(e.target.value)}
                          className="w-24 h-9"
                          autoFocus
                        />
                        <Input
                          placeholder="Reason (optional)" value={reason}
                          onChange={e => setReason(e.target.value)}
                          className="w-44 h-9"
                        />
                        <button
                          onClick={() => handleSave(b.leave_type_id)}
                          disabled={submitting}
                          className="text-emerald-600 hover:text-emerald-700 disabled:opacity-50"
                          title="Save"
                        >
                          <Check size={16} />
                        </button>
                        <button onClick={cancelEdit} className="text-muted-foreground hover:text-foreground" title="Cancel">
                          <X size={16} />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-3">
                        <span className="text-lg font-display font-semibold text-foreground tabular-nums">
                          {Number(b.remaining_days).toFixed(1)}
                          <span className="text-xs text-muted-foreground font-normal"> days</span>
                        </span>
                        <button onClick={() => startEdit(b)} className="text-muted-foreground/40 hover:text-foreground" title="Edit">
                          <Pencil size={14} />
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
