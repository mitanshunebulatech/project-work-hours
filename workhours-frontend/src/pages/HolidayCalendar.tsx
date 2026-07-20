import { useEffect, useState } from 'react'
import { getPublishedHolidays } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui/misc'
import { EmptyState } from '@/components/ui/empty-state'
import { CalendarDays } from 'lucide-react'
import { formatDate } from '@/lib/utils'

const CURRENT_YEAR = new Date().getFullYear()
const YEAR_OPTIONS = [CURRENT_YEAR - 1, CURRENT_YEAR, CURRENT_YEAR + 1]

function daysUntil(dateStr: string): number {
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr + 'T00:00:00')
  return Math.round((target.getTime() - today.getTime()) / 86400000)
}

/**
 * PM req #4 — this is the only source of holiday data on the employee
 * side; there is no separate/static holiday list anywhere else in the
 * app to migrate off of. Always calls GET /holidays/published/{year},
 * never /holidays (the admin listing) — an unpublished year simply
 * comes back empty here, which is the intended behavior, not a bug.
 */
export default function HolidayCalendar() {
  const { toast } = useToast()
  const [year, setYear] = useState(CURRENT_YEAR)
  const [holidays, setHolidays] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getPublishedHolidays(year)
      .then(res => setHolidays([...res.data].sort((a: any, b: any) => a.date.localeCompare(b.date))))
      .catch(() => toast('Failed to load holiday calendar', 'error'))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year])

  const todayISO = new Date().toISOString().slice(0, 10)
  const upcoming = holidays.filter(h => h.date >= todayISO)
  const past = holidays.filter(h => h.date < todayISO)

  return (
    <div className="p-8 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">Holidays</h1>
          <p className="text-sm text-muted-foreground mt-1">Company holiday calendar</p>
        </div>
        <select
          value={year}
          onChange={e => setYear(Number(e.target.value))}
          className="h-9 px-3 rounded-md border border-input bg-background text-sm"
        >
          {YEAR_OPTIONS.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
      </div>

      <Card>
        <CardHeader className="pb-3"><CardTitle>{year}</CardTitle></CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-2">
              {[1, 2, 3].map(i => <div key={i} className="h-12 bg-muted rounded-lg animate-pulse" />)}
            </div>
          ) : holidays.length === 0 ? (
            <EmptyState icon={CalendarDays} title="No holidays published yet"
              description={`The ${year} calendar hasn't been published by admin yet.`} />
          ) : (
            <div className="divide-y">
              {upcoming.map((h: any) => {
                const remaining = daysUntil(h.date)
                return (
                  <div key={h.id} className="flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-3">
                      <CalendarDays size={16} className="text-nebula-600 shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-foreground">{h.name}</p>
                        <p className="text-xs text-muted-foreground">{formatDate(h.date)}</p>
                      </div>
                    </div>
                    <Badge variant={remaining === 0 ? 'success' : 'secondary'}>
                      {remaining === 0 ? 'Today' : remaining === 1 ? 'Tomorrow' : `${remaining} days`}
                    </Badge>
                  </div>
                )
              })}
              {past.map((h: any) => (
                <div key={h.id} className="flex items-center justify-between px-4 py-3 opacity-50">
                  <div className="flex items-center gap-3">
                    <CalendarDays size={16} className="text-muted-foreground shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-foreground">{h.name}</p>
                      <p className="text-xs text-muted-foreground">{formatDate(h.date)}</p>
                    </div>
                  </div>
                  <Badge variant="outline">Past</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
