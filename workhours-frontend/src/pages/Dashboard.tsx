import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import { getDashboardSummary, getEntries } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui/misc'
import { UserAvatar } from '@/components/ui/avatar'
import { CardGridSkeleton, TableSkeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import HolidayWidget from '@/components/HolidayWidget'
import {
  Clock, AlertCircle, Plane, CalendarDays, UserX, Activity, Inbox, ArrowRight,
} from 'lucide-react'
import { formatDate, titleCase } from '@/lib/utils'

/**
 * Admin dashboard is operations-focused per PM req #1: no "My Timesheets"
 * entry point (admins don't log time — see the Timesheet module rework),
 * no all-time Total Entries/Total Hours cards. Everything here defaults to
 * today, backed by GET /dashboard/summary (see app/services/dashboard_service.py).
 *
 * The employee dashboard below is intentionally left as-is — this rework's
 * scope is the admin view only, and /dashboard/summary is gated by the
 * "reports:view" permission an employee account doesn't have.
 */

const statusVariant = (s: string) =>
  s === 'approved' ? 'success' : s === 'pending' ? 'pending' : s === 'rejected' ? 'destructive' : 'secondary'

function AdminDashboard() {
  const { toast } = useToast()
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await getDashboardSummary()
        setSummary(res.data)
      } catch {
        toast('Failed to load dashboard', 'error')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (loading || !summary) {
    return (
      <div className="p-8 max-w-6xl">
        <div className="h-8 w-64 bg-muted rounded animate-pulse mb-1.5" />
        <div className="h-4 w-80 bg-muted rounded animate-pulse mb-6" />
        <div className="mb-8"><CardGridSkeleton count={4} /></div>
        <Card><TableSkeleton rows={4} cols={3} /></Card>
      </div>
    )
  }

  const kpis = [
    {
      label: "Today's Timesheets", value: summary.today_timesheets.total_entries,
      hint: `${summary.today_timesheets.total_hours}h logged today`, icon: Clock,
      tint: 'bg-nebula-50 text-nebula-600',
    },
    {
      label: 'Pending Approvals', value: summary.today_timesheets.pending_approvals,
      hint: 'Dated today', icon: AlertCircle, tint: 'bg-amber-50 text-amber-600',
    },
    {
      label: 'On Leave Today', value: summary.employees_on_leave_today.length,
      hint: 'Approved', icon: Plane, tint: 'bg-sky-50 text-sky-600',
    },
    {
      label: 'Missing Timesheets', value: summary.missing_timesheets.length,
      hint: 'No entry logged today', icon: UserX, tint: 'bg-rose-50 text-rose-600',
    },
  ]

  return (
    <div className="p-8 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-2xl font-display font-semibold text-foreground">Operations Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {formatDate(summary.today)} — today's activity at a glance
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {kpis.map(k => (
          <Card key={k.label} hover>
            <CardContent className="p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1.5">{k.label}</p>
                  <p className="text-2xl font-display font-bold text-foreground tabular-nums">{k.value}</p>
                  <p className="text-xs text-muted-foreground/70 mt-1">{k.hint}</p>
                </div>
                <div className={`p-2.5 rounded-lg ${k.tint}`}>
                  <k.icon size={18} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Employees on Leave Today */}
        <Card>
          <CardHeader className="pb-3 flex-row items-center justify-between space-y-0">
            <CardTitle>On Leave Today</CardTitle>
            <Badge variant="pending" dot>{summary.employees_on_leave_today.length}</Badge>
          </CardHeader>
          <CardContent className="p-0">
            {summary.employees_on_leave_today.length === 0 ? (
              <EmptyState icon={Plane} title="No one is on leave today" />
            ) : (
              <div className="divide-y divide-border">
                {summary.employees_on_leave_today.map((e: any, i: number) => (
                  <div key={i} className="flex items-center justify-between px-6 py-3">
                    <div className="flex items-center gap-2.5">
                      <UserAvatar name={e.employee_name} size={22} />
                      <span className="font-medium text-foreground text-sm">{e.employee_name}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {e.leave_type_name}{e.is_half_day ? ` · ${e.half_day_slot === 'first_half' ? 'First Half' : 'Second Half'}` : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Missing Timesheets */}
        <Card>
          <CardHeader className="pb-3 flex-row items-center justify-between space-y-0">
            <CardTitle>Missing Timesheets</CardTitle>
            <Badge variant={summary.missing_timesheets.length > 0 ? 'destructive' : 'success'} dot>
              {summary.missing_timesheets.length}
            </Badge>
          </CardHeader>
          <CardContent className="p-0">
            {summary.missing_timesheets.length === 0 ? (
              <EmptyState icon={UserX} title="Everyone has logged today" />
            ) : (
              <div className="divide-y divide-border max-h-[280px] overflow-y-auto">
                {summary.missing_timesheets.map((e: any) => (
                  <div key={e.employee_id} className="flex items-center gap-2.5 px-6 py-3">
                    <UserAvatar name={e.employee_name} size={22} />
                    <span className="font-medium text-foreground text-sm">{e.employee_name}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activities */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Recent Activities</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {summary.recent_activities.length === 0 ? (
              <EmptyState icon={Inbox} title="No recent activity" />
            ) : (
              <div className="divide-y divide-border">
                {summary.recent_activities.map((a: any, i: number) => (
                  <div key={i} className="flex items-start gap-3 px-6 py-3">
                    <div className="mt-0.5 p-1.5 rounded-md bg-muted text-muted-foreground">
                      {a.activity_type === 'timesheet' ? <Clock size={13} /> : <Plane size={13} />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-foreground truncate">{a.description}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {new Date(a.occurred_at).toLocaleString()}
                      </p>
                    </div>
                    <Badge variant={statusVariant(a.status)} dot>{titleCase(a.status)}</Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Leave Calendar Widget — condensed list, reuses the summary endpoint's
            month-scoped data rather than re-fetching the full calendar page's data */}
        <Card>
          <CardHeader className="pb-3 flex-row items-center justify-between space-y-0">
            <CardTitle>Leave Calendar — This Month</CardTitle>
            <Link
              to="/admin/leave-calendar"
              className="text-xs font-medium text-nebula-600 hover:text-nebula-700 flex items-center gap-1"
            >
              Full calendar <ArrowRight size={12} />
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            {summary.leave_calendar_this_month.length === 0 ? (
              <EmptyState icon={CalendarDays} title="No approved leave this month" />
            ) : (
              <div className="divide-y divide-border max-h-[280px] overflow-y-auto">
                {summary.leave_calendar_this_month.map((c: any, i: number) => (
                  <div key={i} className="flex items-center justify-between px-6 py-3">
                    <div className="flex items-center gap-2.5">
                      <UserAvatar name={c.employee_name} size={22} />
                      <span className="font-medium text-foreground text-sm">{c.employee_name}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(c.start_date)}{c.start_date !== c.end_date ? ` – ${formatDate(c.end_date)}` : ''}
                      {c.is_half_day ? ' (half day)' : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-6">
        <HolidayWidget viewMoreTo="/admin/holidays" />
      </div>
    </div>
  )
}

function EmployeeDashboard() {
  const { user } = useAuth()
  const [recentEntries, setRecentEntries] = useState<any[]>([])
  const [summary, setSummary] = useState<any>(null)
  const [pendingCount, setPendingCount] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const allRes = await getEntries({ page: 1, size: 100 })
        const items = allRes.data.items
        setRecentEntries(items.slice(0, 5))
        const totalHours = items.reduce((s: number, e: any) => s + parseFloat(e.hours_worked), 0)
        const pending = items.filter((e: any) => e.status === 'pending').length
        setSummary({ total_hours: totalHours, total_entries: items.length })
        setPendingCount(pending)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const greeting = new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'

  if (loading) return (
    <div className="p-8 max-w-6xl">
      <div className="h-8 w-64 bg-muted rounded animate-pulse mb-1.5" />
      <div className="h-4 w-80 bg-muted rounded animate-pulse mb-6" />
      <div className="mb-8"><CardGridSkeleton count={3} /></div>
      <Card><TableSkeleton rows={4} cols={4} /></Card>
    </div>
  )

  const kpis = [
    { label: 'Total Hours', value: Number(summary?.total_hours || 0).toFixed(1), hint: 'All time', icon: Clock, tint: 'bg-nebula-50 text-nebula-600' },
    { label: 'Total Entries', value: summary?.total_entries || 0, hint: 'Submissions', icon: Activity, tint: 'bg-emerald-50 text-emerald-600' },
    { label: 'Pending Approval', value: pendingCount, hint: 'Awaiting review', icon: AlertCircle, tint: 'bg-amber-50 text-amber-600' },
  ]

  return (
    <div className="p-8 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-2xl font-display font-semibold text-foreground">Good {greeting}, {user?.username}</h1>
        <p className="text-sm text-muted-foreground mt-1">Here's what's happening with your timesheets today</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {kpis.map(k => (
          <Card key={k.label} hover>
            <CardContent className="p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1.5">{k.label}</p>
                  <p className="text-2xl font-display font-bold text-foreground tabular-nums">{k.value}</p>
                  <p className="text-xs text-muted-foreground/70 mt-1">{k.hint}</p>
                </div>
                <div className={`p-2.5 rounded-lg ${k.tint}`}>
                  <k.icon size={18} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="pb-3 flex-row items-center justify-between space-y-0">
          <CardTitle>Recent entries</CardTitle>
          {recentEntries.length > 0 && <Badge variant="pending" dot>{recentEntries.length} shown</Badge>}
        </CardHeader>
        <CardContent className="p-0">
          {recentEntries.length === 0 ? (
            <EmptyState
              icon={Inbox}
              title="No entries yet"
              description="Start by submitting your first timesheet from the My Timesheets page."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/40">
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Date</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Project</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Hours</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recentEntries.map((e: any) => (
                    <tr key={e.id} className="border-b last:border-0 hover:bg-muted/40 transition-colors">
                      <td className="px-6 py-3.5 text-muted-foreground whitespace-nowrap">{formatDate(e.entry_date)}</td>
                      <td className="px-6 py-3.5 text-foreground/80">{e.project_name}</td>
                      <td className="px-6 py-3.5 text-foreground font-medium tabular-nums">{e.hours_worked}h</td>
                      <td className="px-6 py-3.5">
                        <Badge variant={statusVariant(e.status)} dot>{titleCase(e.status)}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="mt-6">
        <HolidayWidget />
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  return user?.role === 'admin' ? <AdminDashboard /> : <EmployeeDashboard />
}
