import { useState } from 'react'
import { DayPicker, type DateRange } from 'react-day-picker'
import { ChevronLeft, ChevronRight, CalendarDays } from 'lucide-react'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { cn } from '@/lib/utils'

/** Tailwind-mapped class names — no default react-day-picker stylesheet is imported,
 * so the calendar matches the app's own design tokens instead of a separate theme. */
const dayPickerClassNames = {
  months: 'flex flex-col sm:flex-row gap-4',
  month: 'space-y-3',
  month_caption: 'flex justify-center items-center h-8 relative',
  caption_label: 'text-sm font-medium text-foreground',
  nav: 'flex items-center justify-between absolute inset-x-0 top-0 h-8 px-1',
  button_previous: 'h-7 w-7 flex items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-30',
  button_next: 'h-7 w-7 flex items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-30',
  month_grid: 'w-full border-collapse',
  weekdays: '',
  weekday: 'text-muted-foreground text-xs font-medium w-9 h-9 pb-1',
  weeks: '',
  week: '',
  day: 'p-0 text-center text-sm relative',
  day_button: 'h-9 w-9 rounded-md font-normal hover:bg-muted transition-colors',
  today: 'text-nebula-600 font-semibold',
  selected: 'bg-primary text-primary-foreground hover:bg-primary',
  range_start: 'bg-primary text-primary-foreground rounded-l-md',
  range_end: 'bg-primary text-primary-foreground rounded-r-md',
  range_middle: 'bg-nebula-50 text-foreground rounded-none',
  outside: 'text-muted-foreground/40',
  disabled: 'text-muted-foreground/30 line-through pointer-events-none',
  hidden: 'invisible',
}

interface LeaveDateRangePickerProps {
  value: DateRange | undefined
  onChange: (range: DateRange | undefined) => void
  disabledBefore?: Date
  className?: string
}

export function LeaveDateRangePicker({ value, onChange, disabledBefore, className }: LeaveDateRangePickerProps) {
  const [open, setOpen] = useState(false)

  const label = value?.from
    ? value.to && value.to.getTime() !== value.from.getTime()
      ? `${value.from.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })} – ${value.to.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}`
      : value.from.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
    : 'Select dates'

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            'flex h-9 w-full items-center gap-2 rounded-md border border-input bg-background px-3 text-sm shadow-soft transition-all duration-150 hover:border-primary/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40',
            !value?.from && 'text-muted-foreground',
            className
          )}
        >
          <CalendarDays size={14} className="shrink-0 text-muted-foreground" />
          <span className="truncate">{label}</span>
        </button>
      </PopoverTrigger>
      <PopoverContent className="p-3">
        <DayPicker
          mode="range"
          selected={value}
          onSelect={range => { onChange(range); if (range?.from && range?.to) setOpen(false) }}
          disabled={disabledBefore ? { before: disabledBefore } : undefined}
          classNames={dayPickerClassNames}
          components={{
            Chevron: ({ orientation }) =>
              orientation === 'left' ? <ChevronLeft size={15} /> : <ChevronRight size={15} />
          }}
        />
      </PopoverContent>
    </Popover>
  )
}
