import { useEffect, useState } from 'react'
import { getAuditLogs } from '@/lib/api'
import { Card, CardContent, Badge } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { TableSkeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
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
          <h1 className="text-2xl font-display font-semibold text-foreground">Audit Log</h1>
          <p className="text-sm text-muted-foreground mt-1">{total} events recorded</p>
        </div>
        <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <TableSkeleton rows={6} cols={6} />
          ) : logs.length === 0 ? (
            <EmptyState icon={Shield} title="No audit events yet" description="Activity across users, entries and projects will appear here." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/40">
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Timestamp</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Actor</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Operation</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Table</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">Record</th>
                    <th className="text-left px-5 py-3 text-xs font-medium text-muted-foreground">IP</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log: any) => (
                    <tr key={log.id} className="border-b last:border-0 hover:bg-muted/40 transition-colors">
                      <td className="px-5 py-3.5 text-muted-foreground text-xs whitespace-nowrap">{formatTs(log.created_at)}</td>
                      <td className="px-5 py-3.5 font-medium text-foreground">{log.actor_username || 'system'}</td>
                      <td className="px-5 py-3.5"><Badge variant={OP_VARIANT[log.operation]} dot>{log.operation}</Badge></td>
                      <td className="px-5 py-3.5 text-foreground/70 font-mono text-xs">{log.table_name}</td>
                      <td className="px-5 py-3.5 text-muted-foreground text-xs">#{log.record_id}</td>
                      <td className="px-5 py-3.5 text-muted-foreground/70 text-xs font-mono">{log.ip_address || '—'}</td>
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
