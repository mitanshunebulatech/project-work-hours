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
 * `employee` object on this endpoint. An earlier draft of this component
 * assumed the queue's shape here — that was a real bug (always showed
 * "Employee #undefined"), fixed below by reading the actual fields.
 */

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
]
const WEEKDAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

// A small fixed palette so each leave type gets a stable, distinguishable
// color — cycles if there are more leave types than colors.
const TYPE_COLORS = [
  'bg-nebula-500', 'bg-emerald-500', 'bg-amber-500', 'bg-sky-500', 'bg-rose-500', 'bg-violet-500'
]

function toLocalISODate(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export default function LeaveCalendar() {
  const { toast } = useToast()
  const today = new Date()

  const [month, setMonth] = useState(today.getMonth() + 1) // 1-indexed, matches getLeaveCalendar(month, year)
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
    } catch (err: any) {
      toast('Failed to load calendar', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [month, year]) // eslint-disable-line react-hooks/exhaustive-deps

  // Color/legend is keyed by leave_type_code (the only stable identifier the
  // calendar endpoint actually returns per entry), not by id.
  const typeColor = (leaveTypeCode: string) => {
    const idx = leaveTypes.findIndex(t => t.code === leaveTypeCode)
    return idx >= 0 ? TYPE_COLORS[idx % TYPE_COLORS.length] : TYPE_COLORS[0]
  }

  // Entries whose [start_date, end_date] range includes the given day.
  const entriesForDay = (isoDate: string) =>
    entries.filter(e => e.start_date <= isoDate && e.end_date >= isoDate)

  const goPrevMonth = () => {
    if (month === 1) { setMonth(12); setYear(y => y - 1) } else { setMonth(m => m - 1) }
  }
  const goNextMonth = () => {
    if (month === 12) { setMonth(1); setYear(y => y + 1) } else { setMonth(m => m + 1) }
  }
  const goToday = () => { setMonth(today.getMonth() + 1); setYear(today.getFullYear()) }

  // Build the 6x7 grid of dates, including leading/trailing days from
  // adjacent months so every week row is fully populated.
  const firstOfMonth = new Date(year, month - 1, 1)
  const startWeekday = firstOfMonth.getDay() // 0=Sun
  const gridStart = new Date(year, month - 1, 1 - startWeekday)
  const gridDays: Date[] = Array.from({ length: 42 }, (_, i) => {
    const d = new Date(gridStart)
    d.setDate(gridStart.getDate() + i)
    return d
  })

  const todayISO = toLocalISODate(today)

  return (
    <div className="p-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">Leave Calendar</h1>
          <p className="text-sm text-muted-foreground mt-1">Org-wide view of approved leave</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={goPrevMonth}><ChevronLeft size={14} /></Button>
          <span className="text-sm font-medium text-foreground w-36 text-center">{MONTH_NAMES[month - 1]} {year}</span>
          <Button variant="outline" size="sm" onClick={goNextMonth}><ChevronRight size={14} /></Button>
          <Button variant="ghost" size="sm" onClick={goToday}>Today</Button>
        </div>
      </div>

      {/* Legend */}
      {leaveTypes.length > 0 && (
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
            <div className="p-8 text-center text-sm text-muted-foreground">Loading calendar…</div>
          ) : (
            <div className="grid grid-cols-7">
              {WEEKDAY_LABELS.map(label => (
                <div key={label} className="px-2 py-2 text-center text-xs font-medium text-muted-foreground border-b bg-muted/40">
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
                      'min-h-[88px] p-1.5 border-b border-r text-left align-top flex flex-col gap-1 transition-colors',
                      !inMonth && 'bg-muted/20 text-muted-foreground/40',
                      dayEntries.length > 0 && 'hover:bg-muted/40 cursor-pointer',
                      selectedDay === isoDate && 'bg-nebula-50 ring-1 ring-inset ring-nebula-300'
                    )}
                  >
                    <span className={cn(
                      'text-xs font-medium h-5 w-5 flex items-center justify-center rounded-full',
                      isToday && 'bg-nebula-500 text-white'
                    )}>
                      {day.getDate()}
                    </span>
                    <div className="flex flex-col gap-0.5">
                      {dayEntries.slice(0, 3).map((e, idx) => (
                        <span
                          key={`${e.employee_username}-${e.leave_type_code}-${idx}`}
                          className={cn('h-1.5 rounded-full', typeColor(e.leave_type_code))}
                          title={e.leave_type_display_name}
                        />
                      ))}
                      {dayEntries.length > 3 && (
                        <span className="text-[10px] text-muted-foreground">+{dayEntries.length - 3} more</span>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Selected day detail */}
      {selectedDay && (
        <Card className="mt-4 animate-in fade-in slide-in-from-top-1 duration-150">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <CalendarDays size={14} className="text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">
                {new Date(selectedDay + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
              </span>
            </div>
            <div className="space-y-2">
              {entriesForDay(selectedDay).map((e, idx) => (
                <div key={`${e.employee_username}-${e.leave_type_code}-${idx}`} className="flex items-center gap-2 text-sm">
                  <span className={cn('h-2 w-2 rounded-full shrink-0', typeColor(e.leave_type_code))} />
                  <span className="font-medium text-foreground">{e.employee_username}</span>
                  <Badge variant="secondary">{e.leave_type_display_name}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
