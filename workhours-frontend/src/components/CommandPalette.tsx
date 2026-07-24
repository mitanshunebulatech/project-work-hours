import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { search as searchApi } from '@/lib/api'
import {
  Dialog, DialogContent,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  LayoutDashboard, Clock, Plane, CalendarDays, Users, FolderOpen, UserPlus, Wallet,
  Search as SearchIcon, User as UserIcon, FolderKanban, Building2,
} from 'lucide-react'

interface StaticEntry {
  id: string
  label: string
  icon: React.ReactNode
  to: string
  adminOnly?: boolean
  keywords?: string
}

const STATIC_ENTRIES: StaticEntry[] = [
  { id: 'nav-dashboard', label: 'Dashboard', icon: <LayoutDashboard size={15} />, to: '/dashboard' },
  { id: 'nav-timesheets', label: 'My Timesheets', icon: <Clock size={15} />, to: '/timesheets' },
  { id: 'nav-leave', label: 'Leave', icon: <Plane size={15} />, to: '/leave' },
  { id: 'nav-holidays', label: 'Holidays', icon: <CalendarDays size={15} />, to: '/holidays' },
  { id: 'action-log-hours', label: 'Log Hours', icon: <Clock size={15} />, to: '/timesheets', keywords: 'timesheet entry submit' },
  { id: 'action-request-leave', label: 'Request Leave', icon: <Plane size={15} />, to: '/leave', keywords: 'time off vacation' },
  { id: 'nav-admin-leave', label: 'Leave Approval', icon: <Plane size={15} />, to: '/admin/leave', adminOnly: true },
  { id: 'nav-admin-leave-balance', label: 'Work Leave Balance', icon: <Wallet size={15} />, to: '/admin/leave-balance', adminOnly: true },
  { id: 'nav-admin-holidays', label: 'Holiday Calendar', icon: <CalendarDays size={15} />, to: '/admin/holidays', adminOnly: true },
  { id: 'nav-employees', label: 'Employees', icon: <Users size={15} />, to: '/admin/employees', adminOnly: true },
  { id: 'action-onboard', label: 'Onboard Employee', icon: <UserPlus size={15} />, to: '/admin/employees', adminOnly: true, keywords: 'new hire add employee' },
  { id: 'nav-projects', label: 'Projects', icon: <FolderOpen size={15} />, to: '/admin/projects', adminOnly: true },
  { id: 'nav-departments', label: 'Departments', icon: <Building2 size={15} />, to: '/admin/departments', adminOnly: true },
]

const CATEGORY_ICON: Record<string, React.ReactNode> = {
  employee: <UserIcon size={15} />,
  project: <FolderKanban size={15} />,
  department: <Building2 size={15} />,
}

const CATEGORY_LABEL: Record<string, string> = {
  employee: 'Employees',
  project: 'Projects',
  department: 'Departments',
}

// Backend results don't carry a route today (no per-entity detail pages
// yet) — selecting one goes to that category's list page. Real deep
// linking (e.g. /employees/42) is a natural follow-up once those routes
// exist, not invented here.
const CATEGORY_ROUTE: Record<string, string> = {
  employee: '/admin/employees',
  project: '/admin/projects',
  department: '/admin/departments',
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  isAdmin: boolean
}

export default function CommandPalette({ open, onOpenChange, isAdmin }: Props) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [remoteResults, setRemoteResults] = useState<any[]>([])
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (open) {
      setQuery('')
      setRemoteResults([])
      setActiveIndex(0)
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [open])

  // Instant, zero-latency layer — fuzzy-matches nav/actions client-side.
  const staticMatches = useMemo(() => {
    const q = query.trim().toLowerCase()
    return STATIC_ENTRIES.filter(e => {
      if (e.adminOnly && !isAdmin) return false
      if (!q) return true
      return e.label.toLowerCase().includes(q) || e.keywords?.toLowerCase().includes(q)
    })
  }, [query, isAdmin])

  // Debounced backend entity search — only fires at 2+ characters.
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    const q = query.trim()
    if (q.length < 2) { setRemoteResults([]); return }
    debounceRef.current = setTimeout(() => {
      searchApi(q).then(res => setRemoteResults(res.data.results)).catch(() => setRemoteResults([]))
    }, 300)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [query])

  const flatResults = useMemo(
    () => [
      ...staticMatches.map(e => ({ kind: 'static' as const, entry: e })),
      ...remoteResults.map(r => ({ kind: 'remote' as const, entry: r })),
    ],
    [staticMatches, remoteResults]
  )

  const activate = (index: number) => {
    const item = flatResults[index]
    if (!item) return
    if (item.kind === 'static') {
      navigate(item.entry.to)
    } else {
      navigate(CATEGORY_ROUTE[item.entry.category] || '/dashboard')
    }
    onOpenChange(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIndex(i => Math.min(i + 1, flatResults.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActiveIndex(i => Math.max(i - 1, 0)) }
    else if (e.key === 'Enter') { e.preventDefault(); activate(activeIndex) }
    else if (e.key === 'Escape') { onOpenChange(false) }
  }

  let runningIndex = -1

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg p-0 gap-0 overflow-hidden" onKeyDown={handleKeyDown}>
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
          <SearchIcon size={16} className="text-muted-foreground shrink-0" />
          <Input
            ref={inputRef}
            value={query}
            onChange={e => { setQuery(e.target.value); setActiveIndex(0) }}
            placeholder="Search pages, employees, projects…"
            className="border-0 shadow-none focus-visible:ring-0 px-0 h-8"
          />
        </div>
        <div className="max-h-80 overflow-y-auto py-2">
          {staticMatches.length === 0 && remoteResults.length === 0 && (
            <p className="px-4 py-6 text-sm text-center text-muted-foreground">No results</p>
          )}

          {staticMatches.length > 0 && (
            <div className="px-2 pb-1">
              <p className="px-2 py-1 text-xs font-medium text-muted-foreground/70">Pages &amp; Actions</p>
              {staticMatches.map(e => {
                runningIndex += 1
                const idx = runningIndex
                return (
                  <button
                    key={e.id}
                    onClick={() => activate(idx)}
                    onMouseEnter={() => setActiveIndex(idx)}
                    className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm text-left transition-colors ${
                      idx === activeIndex ? 'bg-muted text-foreground' : 'text-foreground/80'
                    }`}
                  >
                    {e.icon}
                    {e.label}
                  </button>
                )
              })}
            </div>
          )}

          {['employee', 'project', 'department'].map(category => {
            const items = remoteResults.filter(r => r.category === category)
            if (items.length === 0) return null
            return (
              <div key={category} className="px-2 pb-1">
                <p className="px-2 py-1 text-xs font-medium text-muted-foreground/70">{CATEGORY_LABEL[category]}</p>
                {items.map((r: any) => {
                  runningIndex += 1
                  const idx = runningIndex
                  return (
                    <button
                      key={`${category}-${r.id}`}
                      onClick={() => activate(idx)}
                      onMouseEnter={() => setActiveIndex(idx)}
                      className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm text-left transition-colors ${
                        idx === activeIndex ? 'bg-muted text-foreground' : 'text-foreground/80'
                      }`}
                    >
                      {CATEGORY_ICON[category]}
                      <span className="flex-1 min-w-0">
                        <span className="block truncate">{r.label}</span>
                        {r.sublabel && <span className="block text-xs text-muted-foreground truncate">{r.sublabel}</span>}
                      </span>
                    </button>
                  )
                })}
              </div>
            )
          })}
        </div>
      </DialogContent>
    </Dialog>
  )
}
