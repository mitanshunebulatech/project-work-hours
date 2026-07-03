import { useEffect, useState } from 'react'
import { getReportSummary } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/misc'
import { UserAvatar } from '@/components/ui/avatar'
import { CardGridSkeleton } from '@/components/ui/skeleton'
import { BarChart3, Clock, Users, FolderOpen } from 'lucide-react'

export default function AdminReports() {
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getReportSummary()
      .then(r => setSummary(r.data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="p-8 max-w-5xl">
      <div className="h-8 w-40 bg-muted rounded animate-pulse mb-1.5" />
      <div className="h-4 w-72 bg-muted rounded animate-pulse mb-6" />
      <div className="mb-8"><CardGridSkeleton count={3} /></div>
    </div>
  )

  const maxEmpHours = Math.max(...(summary?.by_employee?.map((e: any) => e.total_hours) || [1]))
  const maxProjHours = Math.max(...(summary?.by_project?.map((p: any) => p.total_hours) || [1]))

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <h1 className="text-2xl font-display font-semibold text-foreground">Reports</h1>
        <p className="text-sm text-muted-foreground mt-1">Aggregate overview of all timesheet activity</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <Card hover>
          <CardContent className="p-5 flex items-center gap-4">
            <div className="p-3 bg-nebula-50 rounded-lg"><Clock size={20} className="text-nebula-600" /></div>
            <div>
              <p className="text-xs text-muted-foreground">Total Hours</p>
              <p className="text-2xl font-display font-bold text-foreground tabular-nums">{Number(summary?.total_hours || 0).toFixed(1)}</p>
            </div>
          </CardContent>
        </Card>
        <Card hover>
          <CardContent className="p-5 flex items-center gap-4">
            <div className="p-3 bg-emerald-50 rounded-lg"><BarChart3 size={20} className="text-emerald-600" /></div>
            <div>
              <p className="text-xs text-muted-foreground">Total Entries</p>
              <p className="text-2xl font-display font-bold text-foreground tabular-nums">{summary?.total_entries || 0}</p>
            </div>
          </CardContent>
        </Card>
        <Card hover>
          <CardContent className="p-5 flex items-center gap-4">
            <div className="p-3 bg-purple-50 rounded-lg"><Users size={20} className="text-purple-600" /></div>
            <div>
              <p className="text-xs text-muted-foreground">Active Employees</p>
              <p className="text-2xl font-display font-bold text-foreground tabular-nums">{summary?.by_employee?.length || 0}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By Employee */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Users size={16} className="text-muted-foreground" />
              <CardTitle>Hours by Employee</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {summary?.by_employee?.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No data yet</p>
            ) : summary?.by_employee?.map((e: any) => (
              <div key={e.employee_username}>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <UserAvatar name={e.employee_username} size={22} />
                    <span className="text-sm text-foreground/80">{e.employee_username}</span>
                  </div>
                  <span className="text-sm font-semibold text-foreground tabular-nums">{Number(e.total_hours).toFixed(1)}h</span>
                </div>
                <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-nebula-500 to-nebula-400 rounded-full transition-all duration-500"
                    style={{ width: `${(e.total_hours / maxEmpHours) * 100}%` }} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* By Project */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <FolderOpen size={16} className="text-muted-foreground" />
              <CardTitle>Hours by Project</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {summary?.by_project?.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No data yet</p>
            ) : summary?.by_project?.map((p: any) => (
              <div key={p.project_name}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm text-foreground/80 truncate max-w-[160px]">{p.project_name}</span>
                  <span className="text-sm font-semibold text-foreground ml-2 tabular-nums">{Number(p.total_hours).toFixed(1)}h</span>
                </div>
                <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full transition-all duration-500"
                    style={{ width: `${(p.total_hours / maxProjHours) * 100}%` }} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
