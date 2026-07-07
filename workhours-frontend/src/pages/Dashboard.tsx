import { useEffect, useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { getReportSummary, getEntries } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui/misc'
import { UserAvatar } from '@/components/ui/avatar'
import { CardGridSkeleton, TableSkeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { Clock, TrendingUp, AlertCircle, Inbox } from 'lucide-react'
import { formatDate } from '@/lib/utils'

export default function Dashboard() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [summary, setSummary] = useState<any>(null)
  const [recentEntries, setRecentEntries] = useState<any[]>([])
  const [pendingCount, setPendingCount] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const entriesRes = await getEntries({ page: 1, size: 5 })
        setRecentEntries(entriesRes.data.items)

        if (isAdmin) {
          const [summaryRes, pendingRes] = await Promise.all([
            getReportSummary(),
            getEntries({ page: 1, size: 1, status: 'pending' })
          ])
          setSummary(summaryRes.data)
          setPendingCount(pendingRes.data.total)
        } else {
          const allRes = await getEntries({ page: 1, size: 100 })
          const items = allRes.data.items
          const totalHours = items.reduce((s: number, e: any) => s + parseFloat(e.hours_worked), 0)
          const approved = items.filter((e: any) => e.status === 'approved').length
          const pending = items.filter((e: any) => e.status === 'pending').length
          setSummary({ total_hours: totalHours, total_entries: items.length, approved, pending })
          setPendingCount(pending)
        }
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [isAdmin])

  const statusVariant = (s: string) =>
    s === 'approved' ? 'success' : s === 'pending' ? 'pending' : 'destructive'

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
    { label: 'Total Entries', value: summary?.total_entries || 0, hint: 'Submissions', icon: TrendingUp, tint: 'bg-emerald-50 text-emerald-600' },
    { label: 'Pending Approval', value: pendingCount, hint: 'Awaiting review', icon: AlertCircle, tint: 'bg-amber-50 text-amber-600' },
  ]

  return (
    <div className="p-8 max-w-6xl">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">
            Good {greeting}, {user?.username}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Here's what's happening with your timesheets today</p>
        </div>
      </div>

      {/* KPI Cards */}
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

      {/* Recent entries */}
      <Card>
        <CardHeader className="pb-3 flex-row items-center justify-between space-y-0">
          <CardTitle>Recent entries</CardTitle>
          {recentEntries.length > 0 && (
            <Badge variant="pending" dot>{recentEntries.length} shown</Badge>
          )}
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
                    {isAdmin && <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Employee</th>}
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Project</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Hours</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recentEntries.map((e: any) => (
                    <tr key={e.id} className="border-b last:border-0 hover:bg-muted/40 transition-colors">
                      <td className="px-6 py-3.5 text-muted-foreground whitespace-nowrap">{formatDate(e.entry_date)}</td>
                      {isAdmin && (
                        <td className="px-6 py-3.5">
                          <div className="flex items-center gap-2.5">
                            <UserAvatar name={e.employee_username} size={22} />
                            <span className="font-medium text-foreground">{e.employee_username}</span>
                          </div>
                        </td>
                      )}
                      <td className="px-6 py-3.5 text-foreground/80">{e.project_name}</td>
                      <td className="px-6 py-3.5 text-foreground font-medium tabular-nums">{e.hours_worked}h</td>
                      <td className="px-6 py-3.5">
                        <Badge variant={statusVariant(e.status)} dot>{e.status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
