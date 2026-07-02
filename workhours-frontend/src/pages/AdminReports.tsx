import { useEffect, useState } from 'react'
import { getReportSummary } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/misc'
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
    <div className="p-8">
      <div className="h-8 w-48 bg-slate-100 rounded animate-pulse mb-6" />
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[1,2,3].map(i => <div key={i} className="h-28 bg-slate-100 rounded-lg animate-pulse" />)}
      </div>
    </div>
  )

  const maxEmpHours = Math.max(...(summary?.by_employee?.map((e: any) => e.total_hours) || [1]))
  const maxProjHours = Math.max(...(summary?.by_project?.map((p: any) => p.total_hours) || [1]))

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">Reports</h1>
        <p className="text-sm text-slate-500 mt-0.5">Aggregate overview of all timesheet activity</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <Card>
          <CardContent className="p-5 flex items-center gap-4">
            <div className="p-3 bg-blue-50 rounded-lg"><Clock size={20} className="text-blue-600" /></div>
            <div>
              <p className="text-xs text-slate-500">Total Hours</p>
              <p className="text-2xl font-bold text-slate-900">{Number(summary?.total_hours || 0).toFixed(1)}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5 flex items-center gap-4">
            <div className="p-3 bg-emerald-50 rounded-lg"><BarChart3 size={20} className="text-emerald-600" /></div>
            <div>
              <p className="text-xs text-slate-500">Total Entries</p>
              <p className="text-2xl font-bold text-slate-900">{summary?.total_entries || 0}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5 flex items-center gap-4">
            <div className="p-3 bg-purple-50 rounded-lg"><Users size={20} className="text-purple-600" /></div>
            <div>
              <p className="text-xs text-slate-500">Active Employees</p>
              <p className="text-2xl font-bold text-slate-900">{summary?.by_employee?.length || 0}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* By Employee */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Users size={16} className="text-slate-400" />
              <CardTitle>Hours by Employee</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {summary?.by_employee?.length === 0 ? (
              <p className="text-sm text-slate-400 py-4 text-center">No data yet</p>
            ) : summary?.by_employee?.map((e: any) => (
              <div key={e.employee_username}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 text-xs font-bold">
                      {e.employee_username[0].toUpperCase()}
                    </div>
                    <span className="text-sm text-slate-700">{e.employee_username}</span>
                  </div>
                  <span className="text-sm font-semibold text-slate-900">{Number(e.total_hours).toFixed(1)}h</span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full transition-all"
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
              <FolderOpen size={16} className="text-slate-400" />
              <CardTitle>Hours by Project</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {summary?.by_project?.length === 0 ? (
              <p className="text-sm text-slate-400 py-4 text-center">No data yet</p>
            ) : summary?.by_project?.map((p: any) => (
              <div key={p.project_name}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-slate-700 truncate max-w-[160px]">{p.project_name}</span>
                  <span className="text-sm font-semibold text-slate-900 ml-2">{Number(p.total_hours).toFixed(1)}h</span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full transition-all"
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
