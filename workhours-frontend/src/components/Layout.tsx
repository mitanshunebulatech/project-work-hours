import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import { useTheme } from '@/hooks/useTheme'
import {
  Clock, LayoutDashboard, Users, FolderOpen,
  BarChart3, Shield, LogOut, ChevronLeft, ChevronRight,
  Search, Moon, Sun, Settings, User as UserIcon, Command, Plane, CalendarCheck, CalendarDays,
  Building2, Users2, ShieldCheck
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ReactNode, useState } from 'react'
import { UserAvatar } from '@/components/ui/avatar'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import NotificationBell from '@/components/NotificationBell'
import NebulaTechIcon from '@/components/NebulaTechIcon'

interface NavItem { label: string; to: string; icon: ReactNode; adminOnly?: boolean; employeeOnly?: boolean }

const navItems: NavItem[] = [
  { label: 'Dashboard', to: '/dashboard', icon: <LayoutDashboard size={18} /> },
  // employeeOnly, not just "no adminOnly flag": an admin account can still
  // technically be routed to /timesheets, but EntryService.create_entry now
  // rejects it server-side (see app/services/entry_service.py) — this nav
  // filter keeps the UI consistent with that, rather than showing a link
  // that only leads to a 403.
  { label: 'My Timesheets', to: '/timesheets', icon: <Clock size={18} />, employeeOnly: true },
  { label: 'Leave', to: '/leave', icon: <Plane size={18} /> },
  { label: 'Leave Planning', to: '/leave-plans', icon: <CalendarCheck size={18} /> },
  { label: 'Holidays', to: '/holidays', icon: <CalendarDays size={18} /> },
  { label: 'Timesheets', to: '/admin/timesheets', icon: <Clock size={18} />, adminOnly: true },
  { label: 'Leave Approvals', to: '/admin/leave', icon: <CalendarCheck size={18} />, adminOnly: true },
  { label: 'Leave Calendar', to: '/admin/leave-calendar', icon: <CalendarDays size={18} />, adminOnly: true },
  { label: 'Holiday Calendar', to: '/admin/holidays', icon: <CalendarDays size={18} />, adminOnly: true },
  { label: 'Roles', to: '/admin/roles', icon: <ShieldCheck size={18} />, adminOnly: true },
  { label: 'Departments', to: '/admin/departments', icon: <Building2 size={18} />, adminOnly: true },
  { label: 'User Accounts', to: '/admin/users', icon: <Users size={18} />, adminOnly: true },
  { label: 'Employees', to: '/admin/employees', icon: <Users2 size={18} />, adminOnly: true },
  { label: 'Projects', to: '/admin/projects', icon: <FolderOpen size={18} />, adminOnly: true },
  { label: 'Reports', to: '/admin/reports', icon: <BarChart3 size={18} />, adminOnly: true },
  { label: 'Audit Log', to: '/admin/audit', icon: <Shield size={18} />, adminOnly: true },
]

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/timesheets': 'My Timesheets',
  '/leave': 'Leave',
  '/leave-plans': 'Leave Planning',
  '/holidays': 'Holidays',
  '/profile': 'My Profile',
  '/admin/timesheets': 'Timesheets',
  '/admin/leave': 'Leave Approvals',
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

  const handleLogout = async () => {
    await logout()
    toast('Signed out successfully')
    navigate('/login')
  }

  const visibleNav = navItems.filter(i => (!i.adminOnly || isAdmin) && (!i.employeeOnly || !isAdmin))
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
          {visibleNav.map(item => (
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
          ))}
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
            onClick={() => toast('Command palette coming soon', 'info')}
          >
            <Search size={14} />
            <span className="flex-1 text-left">Search…</span>
            <span className="flex items-center gap-0.5 text-xs text-muted-foreground/70">
              <Command size={11} />K
            </span>
          </button>

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
                <DropdownMenuItem onClick={() => toast('Settings coming soon', 'info')}>
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
