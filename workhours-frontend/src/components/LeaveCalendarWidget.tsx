import { useEffect, useState } from 'react'
import { useToast } from '@/hooks/useToast'
import { getLeaveCalendar, getLeaveTypes } from '@/lib/api'
import { Card, CardContent, Badge } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight, CalendarDays } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * IMPORTANT: GET /leave-requests/calendar returns LeaveCalendarEntryResponse,
 * NOT LeaveRequestResponse. Its fields are flat and DIFFERENT from the admin
 * queue's shape:
 *   { employee_username, leave_type_code, leave_type_display_name, start_date, end_date }
 * There is no `id`, no `leave_type_id`, no `employee_id`, and no nested
 * `employee` object on this endpoint.
 *
 * Extracted from the standalone LeaveCalendar page (PM req #3 — "Integrate
 * Leave Calendar" into the Leave Approval Module) so the same grid/fetch
 * logic isn't duplicated between the full calendar page and the compact
 * sidebar widget on AdminLeaveQueue. LeaveCalendar.tsx now just wraps this
 * in full mode; AdminLeaveQueue renders it with compact.
 */

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
]
const WEEKDAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const WEEKDAY_LABELS_COMPACT = ['S', 'M', 'T', 'W', 'T', 'F', 'S']

const TYPE_COLORS = [
  'bg-nebula-500', 'bg-emerald-500', 'bg-amber-500', 'bg-sky-500', 'bg-rose-500', 'bg-violet-500'
]

function toLocalISODate(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export default function LeaveCalendarWidget({ compact = false }: { compact?: boolean }) {
  const { toast } = useToast()
  const today = new Date()

  const [month, setMonth] = useState(today.getMonth() + 1)
  const [year, setYear] = useState(today.getFullYear())
  const [entries, setEntries] = useState<any[]>([])
  const [leaveTypes, setLeaveTypes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedDay, setSelectedDay] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const [calRes, typesRes] = await Promise.all([
        getLeaveCalendar(month, year),
        getLeaveTypes()
      ])
      const items = Array.isArray(calRes.data) ? calRes.data : (calRes.data?.items ?? [])
      setEntries(items)
      setLeaveTypes(typesRes.data)
    } catch {
      toast('Failed to load calendar', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [month, year]) // eslint-disable-line react-hooks/exhaustive-deps

  const typeColor = (leaveTypeCode: string) => {
    const idx = leaveTypes.findIndex(t => t.code === leaveTypeCode)
    return idx >= 0 ? TYPE_COLORS[idx % TYPE_COLORS.length] : TYPE_COLORS[0]
  }

  const entriesForDay = (isoDate: string) =>
    entries.filter(e => e.start_date <= isoDate && e.end_date >= isoDate)

  const goPrevMonth = () => {
    if (month === 1) { setMonth(12); setYear(y => y - 1) } else { setMonth(m => m - 1) }
  }
  const goNextMonth = () => {
    if (month === 12) { setMonth(1); setYear(y => y + 1) } else { setMonth(m => m + 1) }
  }
  const goToday = () => { setMonth(today.getMonth() + 1); setYear(today.getFullYear()) }

  const firstOfMonth = new Date(year, month - 1, 1)
  const startWeekday = firstOfMonth.getDay()
  const gridStart = new Date(year, month - 1, 1 - startWeekday)
  const gridDays: Date[] = Array.from({ length: 42 }, (_, i) => {
    const d = new Date(gridStart)
    d.setDate(gridStart.getDate() + i)
    return d
  })

  const todayISO = toLocalISODate(today)
  const weekdayLabels = compact ? WEEKDAY_LABELS_COMPACT : WEEKDAY_LABELS
  const cellHeight = compact ? 'min-h-[38px]' : 'min-h-[88px]'
  const maxDots = compact ? 1 : 3

  return (
    <div>
      <div className={cn('flex items-center gap-2', compact ? 'justify-between mb-2' : 'justify-between mb-4')}>
        <span className={cn('font-medium text-foreground', compact ? 'text-xs' : 'text-sm w-36 text-center')}>
          {compact ? `${MONTH_NAMES[month - 1].slice(0, 3)} ${year}` : `${MONTH_NAMES[month - 1]} ${year}`}
        </span>
        <div className="flex items-center gap-1">
          <Button variant="outline" size="sm" onClick={goPrevMonth} className={compact ? 'h-6 w-6 p-0' : ''}>
            <ChevronLeft size={compact ? 12 : 14} />
          </Button>
          {!compact && <Button variant="ghost" size="sm" onClick={goToday}>Today</Button>}
          <Button variant="outline" size="sm" onClick={goNextMonth} className={compact ? 'h-6 w-6 p-0' : ''}>
            <ChevronRight size={compact ? 12 : 14} />
          </Button>
        </div>
      </div>

      {!compact && leaveTypes.length > 0 && (
        <div className="flex flex-wrap gap-3 mb-4">
          {leaveTypes.map((t, i) => (
            <span key={t.id} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className={cn('h-2 w-2 rounded-full', TYPE_COLORS[i % TYPE_COLORS.length])} />
              {t.display_name}
            </span>
          ))}
        </div>
      )}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className={cn('text-center text-muted-foreground', compact ? 'p-4 text-xs' : 'p-8 text-sm')}>
              Loading…
            </div>
          ) : (
            <div className="grid grid-cols-7">
              {weekdayLabels.map((label, i) => (
                <div key={`${label}-${i}`} className={cn(
                  'text-center font-medium text-muted-foreground border-b bg-muted/40',
                  compact ? 'px-0.5 py-1 text-[10px]' : 'px-2 py-2 text-xs'
                )}>
                  {label}
                </div>
              ))}
              {gridDays.map((day, i) => {
                const isoDate = toLocalISODate(day)
                const inMonth = day.getMonth() === month - 1
                const dayEntries = entriesForDay(isoDate)
                const isToday = isoDate === todayISO
                return (
                  <button
                    key={i}
                    onClick={() => dayEntries.length > 0 && setSelectedDay(isoDate === selectedDay ? null : isoDate)}
                    className={cn(
                      cellHeight, 'p-1 border-b border-r text-left align-top flex flex-col gap-0.5 transition-colors',
                      !inMonth && 'bg-muted/20 text-muted-foreground/40',
                      dayEntries.length > 0 && 'hover:bg-muted/40 cursor-pointer',
                      selectedDay === isoDate && 'bg-nebula-50 ring-1 ring-inset ring-nebula-300'
                    )}
                  >
                    <span className={cn(
                      'font-medium flex items-center justify-center rounded-full',
                      compact ? 'text-[10px] h-4 w-4' : 'text-xs h-5 w-5',
                      isToday && 'bg-nebula-500 text-white'
                    )}>
                      {day.getDate()}
                    </span>
                    <div className="flex flex-col gap-0.5">
                      {dayEntries.slice(0, maxDots).map((e, idx) => (
                        <span
                          key={`${e.employee_username}-${e.leave_type_code}-${idx}`}
                          className={cn('h-1.5 rounded-full', typeColor(e.leave_type_code))}
                          title={e.leave_type_display_name}
                        />
                      ))}
                      {dayEntries.length > maxDots && (
                        <span className="text-[9px] text-muted-foreground">+{dayEntries.length - maxDots}</span>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {selectedDay && (
        <Card className="mt-3 animate-in fade-in slide-in-from-top-1 duration-150">
          <CardContent className={compact ? 'p-3' : 'p-4'}>
            <div className="flex items-center gap-2 mb-2">
              <CalendarDays size={compact ? 12 : 14} className="text-muted-foreground" />
              <span className={cn('font-medium text-foreground', compact ? 'text-xs' : 'text-sm')}>
                {/* Deliberately a richer, longer style than formatDate() elsewhere —
                    this is a standalone section header for the selected day, not a
                    table/list value, so more detail earns its place here. Locale is
                    still pinned to 'en-IN' to match every other date in the app —
                    it was previously `undefined` (browser-default locale), which
                    could render differently depending on the visitor's OS/browser
                    settings instead of consistently for everyone. */}
                {new Date(selectedDay + 'T00:00:00').toLocaleDateString('en-IN',
                  compact ? { month: 'short', day: 'numeric' } : { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
              </span>
            </div>
            <div className="space-y-1.5">
              {entriesForDay(selectedDay).map((e, idx) => (
                <div key={`${e.employee_username}-${e.leave_type_code}-${idx}`} className="flex items-center gap-2 text-xs">
                  <span className={cn('h-2 w-2 rounded-full shrink-0', typeColor(e.leave_type_code))} />
                  <span className="font-medium text-foreground truncate">{e.employee_username}</span>
                  {!compact && <Badge variant="secondary">{e.leave_type_display_name}</Badge>}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
