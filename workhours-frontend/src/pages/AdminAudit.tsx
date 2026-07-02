import { useEffect, useState } from 'react'
import { getAuditLogs } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { RefreshCw, Shield } from 'lucide-react'

const OP_VARIANT: Record<string, any> = {
  INSERT: 'success', UPDATE: 'pending', DELETE: 'destructive'
}

export default function AdminAudit() {
  const [logs, setLogs] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const res = await getAuditLogs({ page: 1, size: 100 })
      setLogs(res.data.items)
      setTotal(res.data.total)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const formatTs = (ts: string) =>
    new Date(ts).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    })

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Audit Log</h1>
          <p className="text-sm text-slate-500 mt-0.5">{total} events recorded</p>
        </div>
        <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-3">
              {[1,2,3,4,5].map(i => <div key={i} className="h-10 bg-slate-100 rounded animate-pulse" />)}
            </div>
          ) : logs.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <Shield size={32} className="mx-auto text-slate-200 mb-3" />
              <p className="text-sm text-slate-400">No audit events yet</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-slate-50">
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Timestamp</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Actor</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Operation</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Table</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">Record</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500">IP</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log: any) => (
                  <tr key={log.id} className="border-b last:border-0 hover:bg-slate-50 transition-colors">
                    <td className="px-5 py-3.5 text-slate-500 text-xs whitespace-nowrap">{formatTs(log.created_at)}</td>
                    <td className="px-5 py-3.5 font-medium text-slate-900">{log.actor_username || 'system'}</td>
                    <td className="px-5 py-3.5"><Badge variant={OP_VARIANT[log.operation]}>{log.operation}</Badge></td>
                    <td className="px-5 py-3.5 text-slate-600 font-mono text-xs">{log.table_name}</td>
                    <td className="px-5 py-3.5 text-slate-500 text-xs">#{log.record_id}</td>
                    <td className="px-5 py-3.5 text-slate-400 text-xs font-mono">{log.ip_address || '—'}</td>
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
