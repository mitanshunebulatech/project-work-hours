import { useMemo, useState } from 'react'
import { ChevronDown, Search, X } from 'lucide-react'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { cn } from '@/lib/utils'

export interface MultiSelectOption {
  value: number
  label: string
}

interface MultiSelectPopoverProps {
  label: string
  options: MultiSelectOption[]
  selected: number[]
  onChange: (values: number[]) => void
  className?: string
  searchPlaceholder?: string
}

/**
 * Checkbox-based multi-select for the Timesheet Module's employee/project
 * filters (PM req #2). Built as a shared component rather than inlined in
 * AdminTimesheets.tsx since the Leave Approval rework will likely want the
 * same pattern for its own employee filter later.
 */
export function MultiSelectPopover({
  label, options, selected, onChange, className, searchPlaceholder = 'Search...',
}: MultiSelectPopoverProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    if (!query.trim()) return options
    const q = query.toLowerCase()
    return options.filter(o => o.label.toLowerCase().includes(q))
  }, [options, query])

  const toggle = (value: number) => {
    if (selected.includes(value)) onChange(selected.filter(v => v !== value))
    else onChange([...selected, value])
  }

  const clear = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange([])
  }

  const buttonLabel =
    selected.length === 0 ? label : selected.length === 1
      ? options.find(o => o.value === selected[0])?.label || `1 selected`
      : `${selected.length} selected`

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            'flex h-9 items-center gap-2 rounded-md border border-input bg-background px-3 text-sm shadow-soft transition-all duration-150 hover:border-primary/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40',
            selected.length === 0 && 'text-muted-foreground',
            className
          )}
        >
          <span className="truncate max-w-[140px]">{buttonLabel}</span>
          {selected.length > 0 && (
            <span
              onClick={clear}
              className="rounded-full p-0.5 hover:bg-muted transition-colors"
              title="Clear"
            >
              <X size={12} />
            </span>
          )}
          <ChevronDown size={14} className="shrink-0 text-muted-foreground" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="p-0 w-64" align="start">
        <div className="p-2 border-b">
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full h-8 pl-8 pr-2 text-sm rounded-md border border-input bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
            />
          </div>
        </div>
        <div className="max-h-64 overflow-y-auto p-1.5">
          {filtered.length === 0 ? (
            <p className="text-xs text-muted-foreground px-2 py-3 text-center">No matches</p>
          ) : (
            filtered.map(opt => (
              <label
                key={opt.value}
                className="flex items-center gap-2.5 px-2 py-1.5 rounded-md hover:bg-muted/60 cursor-pointer transition-colors text-sm"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(opt.value)}
                  onChange={() => toggle(opt.value)}
                  className="h-3.5 w-3.5 rounded border-input accent-primary cursor-pointer"
                />
                <span className="truncate text-foreground">{opt.label}</span>
              </label>
            ))
          )}
        </div>
        {selected.length > 0 && (
          <div className="border-t p-1.5">
            <button
              type="button"
              onClick={() => onChange([])}
              className="w-full text-xs text-center py-1 text-muted-foreground hover:text-foreground transition-colors"
            >
              Clear all ({selected.length})
            </button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}
