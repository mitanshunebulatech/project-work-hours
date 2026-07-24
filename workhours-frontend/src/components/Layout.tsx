import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import { useTheme } from '@/hooks/useTheme'
import {
  Clock, LayoutDashboard, Users, FolderOpen,
  BarChart3, Shield, LogOut, ChevronLeft, ChevronRight, ChevronDown,
  Search, Moon, Sun, Settings, User as UserIcon, Command, Plane, CalendarCheck, CalendarDays,
  Building2, Users2, ShieldCheck, Wallet
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { features } from '@/lib/features'
import { ReactNode, useEffect, useState } from 'react'
import { UserAvatar } from '@/components/ui/avatar'
import CommandPalette from './CommandPalette'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import NotificationBell from '@/components/NotificationBell'
import NebulaTechIcon from '@/components/NebulaTechIcon'

interface NavItem {
  label: string
  to: string
  icon: ReactNode
  adminOnly?: boolean
  employeeOnly?: boolean
  enabled?: boolean
}

interface NavGroup {
  label: string
  icon: ReactNode
  adminOnly?: boolean
  children: NavItem[]
}

type NavEntry = NavItem | NavGroup

function isNavGroup(entry: NavEntry): entry is NavGroup {
  return 'children' in entry
}

const navItems: NavEntry[] = [
  { label: 'Dashboard', to: '/dashboard', icon: <LayoutDashboard size={18} /> },
  // employeeOnly, not just "no adminOnly flag": an admin account can still
  // technically be routed to /timesheets, but EntryService.create_entry now
  // rejects it server-side (see app/services/entry_service.py) — this nav
  // filter keeps the UI consistent with that, rather than showing a link
  // that only leads to a 403.
  { label: 'My Timesheets', to: '/timesheets', icon: <Clock size={18} />, employeeOnly: true },
  { label: 'Leave', to: '/leave', icon: <Plane size={18} /> },
  { label: 'Holidays', to: '/holidays', icon: <CalendarDays size={18} /> },
  { label: 'Timesheets', to: '/admin/timesheets', icon: <Clock size={18} />, adminOnly: true },
  // Stage 5 (sidebar reorg): the 3 admin Leave-related pages collapse into
  // one group instead of sitting as 3 flat top-level items. Holiday Calendar
  // stays a single top-level item since it's already one merged page
  // (Calendar + Publisher merged in an earlier stage) — nothing left to group.
  {
    label: 'Leave',
    icon: <Plane size={18} />,
    adminOnly: true,
    children: [
      { label: 'Leave Approvals', to: '/admin/leave', icon: <CalendarCheck size={16} /> },
      { label: 'Work Leave Balance', to: '/admin/leave-balance', icon: <Wallet size={16} /> },
      { label: 'Leave Calendar', to: '/admin/leave-calendar', icon: <CalendarDays size={16} /> },
    ],
  },
  { label: 'Holiday Calendar', to: '/admin/holidays', icon: <CalendarDays size={18} />, adminOnly: true },
  { label: 'Roles', to: '/admin/roles', icon: <ShieldCheck size={18} />, adminOnly: true, enabled: features.adminRoles },
  { label: 'Departments', to: '/admin/departments', icon: <Building2 size={18} />, adminOnly: true },
  { label: 'User Accounts', to: '/admin/users', icon: <Users size={18} />, adminOnly: true },
  { label: 'Employees', to: '/admin/employees', icon: <Users2 size={18} />, adminOnly: true },
  { label: 'Projects', to: '/admin/projects', icon: <FolderOpen size={18} />, adminOnly: true },
  { label: 'Reports', to: '/admin/reports', icon: <BarChart3 size={18} />, adminOnly: true, enabled: features.adminReports },
  { label: 'Audit Log', to: '/admin/audit', icon: <Shield size={18} />, adminOnly: true, enabled: features.adminAudit },
]

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/timesheets': 'My Timesheets',
  '/leave': 'Leave',
  '/holidays': 'Holidays',
  '/profile': 'My Profile',
  '/settings': 'Settings',
  '/admin/timesheets': 'Timesheets',
  '/admin/leave': 'Leave Approvals',
  '/admin/leave-balance': 'Work Leave Balance',
  '/admin/leave-calendar': 'Leave Calendar',
  '/admin/holidays': 'Holiday Calendar',
  '/admin/roles': 'Roles',
  '/admin/departments': 'Departments',
  '/admin/users': 'User Accounts',
  '/admin/employees': 'Employees',
  '/admin/projects': 'Projects',
  '/admin/reports': 'Reports',
  '/admin/audit': 'Audit Log',
}

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  const { toast } = useToast()
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const isAdmin = user?.role === 'admin'
  const [collapsed, setCollapsed] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)

  const passesFilter = (i: { adminOnly?: boolean; employeeOnly?: boolean; enabled?: boolean }) =>
    i.enabled !== false && (!i.adminOnly || isAdmin) && (!i.employeeOnly || !isAdmin)

  const visibleNav = navItems
    .filter(passesFilter)
    .map(entry => (isNavGroup(entry) ? { ...entry, children: entry.children.filter(passesFilter) } : entry))
    .filter(entry => !isNavGroup(entry) || entry.children.length > 0)

  // Auto-expand a group if the current route is one of its children — so
  // deep-linking straight to e.g. /admin/leave-calendar doesn't leave the
  // sidebar looking collapsed with no visual trace of where you are.
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(() => {
    const initial = new Set<string>()
    for (const entry of visibleNav) {
      if (isNavGroup(entry) && entry.children.some(c => c.to === location.pathname)) {
        initial.add(entry.label)
      }
    }
    return initial
  })

  const toggleGroup = (label: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev)
      if (next.has(label)) next.delete(label)
      else next.add(label)
      return next
    })
  }

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen(open => !open)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const handleLogout = async () => {
    await logout()
    toast('Signed out successfully')
    navigate('/login')
  }

  const pageTitle = PAGE_TITLES[location.pathname] || 'WorkHours'

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          'relative flex flex-col shrink-0 bg-sidebar transition-[width] duration-200 ease-out',
          collapsed ? 'w-[72px]' : 'w-64'
        )}
      >
        {/* Logo */}
        <div className={cn('flex items-center h-14 border-b border-sidebar-border', collapsed ? 'justify-center px-0' : 'gap-2.5 px-5')}>
          <div className="w-7 h-7 rounded-md bg-white flex items-center justify-center shrink-0 shadow-sm">
            <NebulaTechIcon size={20} />
          </div>
          {!collapsed && (
            <span className="text-white font-display font-semibold text-sm tracking-tight">
              WorkHours
            </span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto overflow-x-hidden">
          {visibleNav.map(item => {
            if (isNavGroup(item)) {
              const isExpanded = expandedGroups.has(item.label)
              const isChildActive = item.children.some(c => c.to === location.pathname)
              return (
                <div key={item.label}>
                  <button
                    onClick={() => {
                      // Clicking a group while the sidebar is icon-only first
                      // expands the whole sidebar — otherwise there'd be
                      // nowhere to actually show the children that just opened.
                      if (collapsed) setCollapsed(false)
                      toggleGroup(item.label)
                    }}
                    title={collapsed ? item.label : undefined}
                    className={cn(
                      'w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors group',
                      collapsed && 'justify-center px-0',
                      isChildActive
                        ? 'text-white'
                        : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                    )}
                  >
                    <span className={cn('shrink-0 transition-colors', isChildActive ? 'text-nebula-400' : 'text-slate-500 group-hover:text-slate-300')}>
                      {item.icon}
                    </span>
                    {!collapsed && (
                      <>
                        <span className="truncate flex-1 text-left">{item.label}</span>
                        <ChevronDown size={14} className={cn('shrink-0 transition-transform', isExpanded && 'rotate-180')} />
                      </>
                    )}
                  </button>
                  {!collapsed && isExpanded && (
                    <div className="ml-3 pl-3 border-l border-white/10 space-y-0.5 mt-0.5">
                      {item.children.map(child => (
                        <NavLink
                          key={child.to}
                          to={child.to}
                          className={({ isActive }) => cn(
                            'relative flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors group',
                            isActive
                              ? 'bg-white/10 text-white'
                              : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                          )}
                        >
                          {({ isActive }) => (
                            <>
                              <span className={cn('shrink-0 transition-colors', isActive ? 'text-nebula-400' : 'text-slate-500 group-hover:text-slate-300')}>
                                {child.icon}
                              </span>
                              <span className="truncate">{child.label}</span>
                            </>
                          )}
                        </NavLink>
                      ))}
                    </div>
                  )}
                </div>
              )
            }
            return (
              <NavLink
                key={item.to}
                to={item.to}
                title={collapsed ? item.label : undefined}
                className={({ isActive }) => cn(
                  'relative flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors group',
                  collapsed && 'justify-center px-0',
                  isActive
                    ? 'bg-white/10 text-white'
                    : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                )}
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r-full bg-nebula-400" />
                    )}
                    <span className={cn('shrink-0 transition-colors', isActive ? 'text-nebula-400' : 'text-slate-500 group-hover:text-slate-300')}>
                      {item.icon}
                    </span>
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </>
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(c => !c)}
          className="mx-3 mb-2 flex items-center justify-center h-8 rounded-md text-slate-500 hover:bg-white/5 hover:text-slate-200 transition-colors"
        >
          {collapsed ? <ChevronRight size={15} /> : <><ChevronLeft size={15} /><span className="ml-1.5 text-xs">Collapse</span></>}
        </button>

        {/* User footer */}
        <div className={cn('border-t border-sidebar-border', collapsed ? 'px-2 py-3' : 'px-3 py-3')}>
          <div className={cn('flex items-center rounded-md', collapsed ? 'justify-center' : 'gap-3 px-1 py-1')}>
            <UserAvatar name={user?.username} size={28} />
            {!collapsed && (
              <>
                <div className="flex-1 min-w-0">
                  <p className="text-white text-xs font-medium truncate">{user?.username}</p>
                  <p className="text-slate-500 text-xs capitalize">{user?.role}</p>
                </div>
                <button onClick={handleLogout} className="text-slate-500 hover:text-red-400 transition-colors" title="Sign out">
                  <LogOut size={15} />
                </button>
              </>
            )}
          </div>
        </div>
      </aside>

      {/* Main column */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <header className="sticky top-0 z-30 flex items-center gap-4 h-14 px-6 border-b border-border bg-background/80 backdrop-blur-md">
          <div className="flex items-center gap-1.5 text-sm min-w-0">
            <span className="text-muted-foreground">WorkHours</span>
            <ChevronRight size={14} className="text-muted-foreground/50" />
            <span className="font-medium text-foreground truncate">{pageTitle}</span>
          </div>

          <button
            className="hidden sm:flex items-center gap-2 ml-2 h-8 px-3 rounded-md border border-input bg-muted/40 text-sm text-muted-foreground hover:border-primary/30 hover:text-foreground transition-colors w-64"
            onClick={() => setPaletteOpen(true)}
          >
            <Search size={14} />
            <span className="flex-1 text-left">Search…</span>
            <span className="flex items-center gap-0.5 text-xs text-muted-foreground/70">
              <Command size={11} />K
            </span>
          </button>

          <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} isAdmin={isAdmin} />

          <div className="ml-auto flex items-center gap-1.5">
            <button
              onClick={toggle}
              className="h-9 w-9 flex items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              title="Toggle theme"
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>

            <NotificationBell />

            <DropdownMenu>
              <DropdownMenuTrigger className="ml-1.5 flex items-center gap-2 rounded-md p-1 pr-2 hover:bg-muted transition-colors outline-none">
                <UserAvatar name={user?.username} size={28} />
                <span className="hidden md:block text-sm font-medium text-foreground">{user?.username}</span>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52">
                <DropdownMenuLabel>
                  <p className="font-medium">{user?.username}</p>
                  <p className="font-normal text-muted-foreground capitalize">{user?.role}</p>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate('/profile')}>
                  <UserIcon size={14} /> Profile
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate('/settings')}>
                  <Settings size={14} /> Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem destructive onClick={handleLogout}>
                  <LogOut size={14} /> Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page content */}
        <main key={location.pathname} className="flex-1 overflow-y-auto animate-in fade-in slide-in-from-bottom-1 duration-300">
          {children}
        </main>
      </div>
    </div>
  )
}
