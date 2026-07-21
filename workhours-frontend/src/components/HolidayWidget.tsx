import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getPublishedHolidays } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui/misc'
import { EmptyState } from '@/components/ui/empty-state'
import { CalendarDays, ArrowRight } from 'lucide-react'
import { formatDate } from '@/lib/utils'

function daysUntil(dateStr: string): number {
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr + 'T00:00:00')
  return Math.round((target.getTime() - today.getTime()) / 86400000)
}

interface HolidayWidgetProps {
  /** Where "View More" sends the user — admins land on the management
   * page, employees on the read-only calendar (PM req #4/#5 split). */
  viewMoreTo?: string
  limit?: number
}

/**
 * PM req #5 — compact upcoming-holidays list, not a month-grid mini
 * calendar (that shape was considered and explicitly not chosen). Reused
 * as-is on both the admin and employee dashboards; only the "View More"
 * destination differs between the two callers.
 *
 * Fetches the current year and, once inside the last month of the year,
 * next year too — otherwise a holiday on Jan 1 would vanish from
 * "upcoming" for the entire month of December just because it crossed a
 * year boundary.
 */
export default function HolidayWidget({ viewMoreTo = '/holidays', limit = 5 }: HolidayWidgetProps) {
  const [holidays, setHolidays] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const now = new Date()
    const years = now.getMonth() === 11 ? [now.getFullYear(), now.getFullYear() + 1] : [now.getFullYear()]

    Promise.all(years.map(y => getPublishedHolidays(y).then(res => res.data).catch(() => [])))
      .then(results => {
        const todayISO = now.toISOString().slice(0, 10)
        const merged = results
          .flat()
          .filter((h: any) => h.date >= todayISO)
          .sort((a: any, b: any) => a.date.localeCompare(b.date))
          .slice(0, limit)
        setHolidays(merged)
      })
      .finally(() => setLoading(false))
  }, [limit])

  return (
    <Card>
      <CardHeader className="pb-3 flex-row items-center justify-between space-y-0">
        <CardTitle>Upcoming Holidays</CardTitle>
        <Link to={viewMoreTo} className="text-xs font-medium text-nebula-600 hover:text-nebula-700 flex items-center gap-1">
          View More <ArrowRight size={12} />
        </Link>
      </CardHeader>
      <CardContent className="p-0">
        {loading ? (
          <div className="p-6 space-y-2">
            {[1, 2].map(i => <div key={i} className="h-10 bg-muted rounded-lg animate-pulse" />)}
          </div>
        ) : holidays.length === 0 ? (
          <EmptyState icon={CalendarDays} title="No upcoming holidays" />
        ) : (
          <div className="divide-y divide-border">
            {holidays.map((h: any) => {
              const remaining = daysUntil(h.date)
              return (
                <div key={h.id} className="flex items-center justify-between px-6 py-3">
                  <div className="flex items-center gap-2.5">
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
          </div>
        )}
      </CardContent>
    </Card>
  )
}
