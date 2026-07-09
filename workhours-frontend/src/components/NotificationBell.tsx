import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, CheckCheck } from 'lucide-react'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import {
  getMyNotifications, getUnreadNotificationCount,
  markNotificationRead, markAllNotificationsRead
} from '@/lib/api'
import { cn } from '@/lib/utils'

function timeAgo(iso: string) {
  const diffSec = (Date.now() - new Date(iso).getTime()) / 1000
  if (diffSec < 60) return 'just now'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  return `${Math.floor(diffSec / 86400)}d ago`
}

// Where clicking a notification of this type should navigate.
const TYPE_ROUTE: Record<string, string> = {
  leave_request_submitted: '/admin/leave',
  leave_request_approved: '/leave',
  leave_request_rejected: '/leave',
  leave_request_cancelled: '/admin/leave',
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState<any[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const loadCount = async () => {
    try {
      const res = await getUnreadNotificationCount()
      const n = res.data?.count ?? res.data?.unread_count ?? 0
      setUnreadCount(typeof n === 'number' ? n : 0)
    } catch {
      // Silent — badge just won't update this cycle, not worth a toast.
    }
  }

  const loadList = async () => {
    setLoading(true)
    try {
      const res = await getMyNotifications({ page: 1, size: 20 })
      const items = Array.isArray(res.data) ? res.data : (res.data?.items ?? [])
      setNotifications(items)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCount()
    const interval = setInterval(loadCount, 60000)
    return () => clearInterval(interval)
  }, [])

  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen)
    if (isOpen) loadList()
  }

  const handleItemClick = async (n: any) => {
    if (!n.is_read) {
      try {
        await markNotificationRead(n.id)
        setNotifications(prev => prev.map(x => (x.id === n.id ? { ...x, is_read: true } : x)))
        setUnreadCount(c => Math.max(0, c - 1))
      } catch {
        // Non-fatal — worst case the item just stays visually unread.
      }
    }
    const route = TYPE_ROUTE[n.type]
    if (route) {
      setOpen(false)
      navigate(route)
    }
  }

  const handleMarkAll = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await markAllNotificationsRead()
      setNotifications(prev => prev.map(x => ({ ...x, is_read: true })))
      setUnreadCount(0)
    } catch {
      // Non-fatal
    }
  }

  return (
    <DropdownMenu open={open} onOpenChange={handleOpenChange}>
      <DropdownMenuTrigger
        className="relative h-9 w-9 flex items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors outline-none"
        title="Notifications"
      >
        <Bell size={16} />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 min-w-[16px] h-4 px-1 flex items-center justify-center rounded-full bg-nebula-500 text-white text-[10px] font-medium leading-none">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 max-h-96 overflow-y-auto">
        <DropdownMenuLabel className="flex items-center justify-between pr-1">
          <span>Notifications</span>
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAll}
              className="flex items-center gap-1 text-xs font-normal text-nebula-600 hover:text-nebula-700"
            >
              <CheckCheck size={12} /> Mark all read
            </button>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {loading ? (
          <div className="px-3 py-6 text-center text-xs text-muted-foreground">Loading…</div>
        ) : notifications.length === 0 ? (
          <div className="px-3 py-6 text-center text-xs text-muted-foreground">No notifications yet</div>
        ) : (
          notifications.map(n => (
            <DropdownMenuItem
              key={n.id}
              onClick={() => handleItemClick(n)}
              className={cn('flex flex-col items-start gap-0.5 whitespace-normal py-2', !n.is_read && 'bg-nebula-50/60')}
            >
              <div className="flex items-center gap-1.5 w-full">
                {!n.is_read && <span className="h-1.5 w-1.5 rounded-full bg-nebula-500 shrink-0" />}
                <span className="text-xs text-foreground leading-snug">{n.message}</span>
              </div>
              <span className="text-[11px] text-muted-foreground/70 pl-3">{timeAgo(n.created_at)}</span>
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
