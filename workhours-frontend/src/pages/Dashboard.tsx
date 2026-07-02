import { useEffect, useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { getReportSummary, getEntries } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui/misc'
import { Clock, TrendingUp, CheckCircle, AlertCircle } from 'lucide-react'
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

  if (loading) return (
    <div className="p-8">
      <div className="h-8 w-48 bg-slate-100 rounded animate-pulse mb-6" />
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[1,2,3].map(i => <div key={i} className="h-28 bg-slate-100 rounded-lg animate-pulse" />)}
      </div>
    </div>
  )

  return (
    <div className="p-8 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">
          Good {new Date().getHours() < 12 ? 'morning' : 'afternoon'}, {user?.username}
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">Here's what's happening with your timesheets today</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-slate-500 mb-1">Total Hours</p>
                <p className="text-2xl font-bold text-slate-900">
                  {Number(summary?.total_hours || 0).toFixed(1)}
                </p>
                <p className="text-xs text-slate-400 mt-0.5">All time</p>
              </div>
              <div className="p-2 bg-blue-50 rounded-lg">
                <Clock size={18} className="text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-slate-500 mb-1">Total Entries</p>
                <p className="text-2xl font-bold text-slate-900">{summary?.total_entries || 0}</p>
                <p className="text-xs text-slate-400 mt-0.5">Submissions</p>
              </div>
              <div className="p-2 bg-emerald-50 rounded-lg">
                <TrendingUp size={18} className="text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-slate-500 mb-1">Pending Approval</p>
                <p className="text-2xl font-bold text-slate-900">{pendingCount}</p>
                <p className="text-xs text-slate-400 mt-0.5">Awaiting review</p>
              </div>
              <div className="p-2 bg-amber-50 rounded-lg">
                <AlertCircle size={18} className="text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent entries */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Recent entries</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {recentEntries.length === 0 ? (
            <div className="px-6 py-10 text-center text-sm text-slate-400">
              No entries yet. Start by submitting your first timesheet.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-slate-50">
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">Date</th>
                  {isAdmin && <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">Employee</th>}
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">Project</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">Hours</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">Status</th>
                </tr>
              </thead>
              <tbody>
                {recentEntries.map((e: any, i) => (
                  <tr key={e.id} className={`border-b last:border-0 hover:bg-slate-50 ${i % 2 === 0 ? '' : 'bg-slate-50/30'}`}>
                    <td className="px-6 py-3 text-slate-600">{formatDate(e.entry_date)}</td>
                    {isAdmin && <td className="px-6 py-3 font-medium text-slate-900">{e.employee_username}</td>}
                    <td className="px-6 py-3 text-slate-700">{e.project_name}</td>
                    <td className="px-6 py-3 text-slate-700 font-medium">{e.hours_worked}h</td>
                    <td className="px-6 py-3">
                      <Badge variant={statusVariant(e.status)}>{e.status}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
