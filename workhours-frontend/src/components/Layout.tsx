import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import {
  Clock, LayoutDashboard, Users, FolderOpen,
  BarChart3, Shield, LogOut, ChevronRight
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ReactNode } from 'react'

interface NavItem { label: string; to: string; icon: ReactNode; adminOnly?: boolean }

const navItems: NavItem[] = [
  { label: 'Dashboard', to: '/dashboard', icon: <LayoutDashboard size={18} /> },
  { label: 'My Timesheets', to: '/timesheets', icon: <Clock size={18} /> },
  { label: 'Entries', to: '/admin/entries', icon: <Clock size={18} />, adminOnly: true },
  { label: 'Users', to: '/admin/users', icon: <Users size={18} />, adminOnly: true },
  { label: 'Projects', to: '/admin/projects', icon: <FolderOpen size={18} />, adminOnly: true },
  { label: 'Reports', to: '/admin/reports', icon: <BarChart3 size={18} />, adminOnly: true },
  { label: 'Audit Log', to: '/admin/audit', icon: <Shield size={18} />, adminOnly: true },
]

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  const { toast } = useToast()
  const navigate = useNavigate()
  const isAdmin = user?.role === 'admin'

  const handleLogout = async () => {
    await logout()
    toast('Signed out successfully')
    navigate('/login')
  }

  const visibleNav = navItems.filter(i => !i.adminOnly || isAdmin)

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="flex flex-col w-56 shrink-0" style={{ background: 'hsl(222 47% 11%)' }}>
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 h-14 border-b" style={{ borderColor: 'hsl(222 40% 18%)' }}>
          <div className="w-7 h-7 rounded-md bg-blue-500 flex items-center justify-center">
            <Clock size={14} className="text-white" />
          </div>
          <span className="text-white font-semibold text-sm tracking-tight">WorkHours</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {visibleNav.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors group',
                isActive
                  ? 'bg-white/10 text-white'
                  : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
              )}
            >
              {({ isActive }) => (
                <>
                  <span className={cn('transition-colors', isActive ? 'text-blue-400' : 'text-slate-500 group-hover:text-slate-300')}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                  {isActive && <ChevronRight size={14} className="ml-auto text-slate-500" />}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="px-3 py-3 border-t" style={{ borderColor: 'hsl(222 40% 18%)' }}>
          <div className="flex items-center gap-3 px-3 py-2 rounded-md">
            <div className="w-7 h-7 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs font-bold shrink-0">
              {user?.username?.[0]?.toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-xs font-medium truncate">{user?.username}</p>
              <p className="text-slate-500 text-xs capitalize">{user?.role}</p>
            </div>
            <button onClick={handleLogout} className="text-slate-500 hover:text-red-400 transition-colors">
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
