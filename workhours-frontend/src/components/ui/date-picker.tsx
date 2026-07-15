import { useState } from 'react'
import { DayPicker } from 'react-day-picker'
import { ChevronLeft, ChevronRight, CalendarDays } from 'lucide-react'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { cn } from '@/lib/utils'

/** Same class map as LeaveDateRangePicker (components/ui/date-range-picker.tsx) —
 * kept in sync manually since this is a single-date variant, not a shared
 * base, to avoid a premature abstraction over two fairly different DayPicker
 * `mode`s (range vs single). */
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
  outside: 'text-muted-foreground/40',
  disabled: 'text-muted-foreground/30 line-through pointer-events-none',
  hidden: 'invisible',
}

interface SingleDatePickerProps {
  value: Date
  onChange: (date: Date) => void
  disabledAfter?: Date
  className?: string
}

export function SingleDatePicker({ value, onChange, disabledAfter, className }: SingleDatePickerProps) {
  const [open, setOpen] = useState(false)

  const label = value.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
  const isToday = value.toDateString() === new Date().toDateString()

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            'flex h-9 items-center gap-2 rounded-md border border-input bg-background px-3 text-sm shadow-soft transition-all duration-150 hover:border-primary/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40',
            className
          )}
        >
          <CalendarDays size={14} className="shrink-0 text-muted-foreground" />
          <span className="truncate">{isToday ? 'Today' : label}</span>
        </button>
      </PopoverTrigger>
      <PopoverContent className="p-3">
        <DayPicker
          mode="single"
          selected={value}
          onSelect={date => { if (date) { onChange(date); setOpen(false) } }}
          disabled={disabledAfter ? { after: disabledAfter } : undefined}
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
