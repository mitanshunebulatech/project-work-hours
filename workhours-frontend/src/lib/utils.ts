import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric'
  })
}

/**
 * Formats a Date as 'yyyy-MM-dd' using LOCAL time components (not
 * toISOString(), which converts to UTC first and can shift the date near
 * midnight IST — e.g. 00:30 IST on the 10th becomes '...T19:00Z' the 9th).
 * Used for the Timesheet date picker and any other admin date-filter param.
 */
export function toApiDateString(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function formatHours(h: number | string) {
  return `${Number(h).toFixed(1)}h`
}

/** "pending" -> "Pending" — for displaying stored (lowercase) status enum
 * values, without changing what's actually stored/filtered/indexed on. */
export function titleCase(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
