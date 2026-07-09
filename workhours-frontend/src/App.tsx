import { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/hooks/useAuth'
import { ToastProvider } from '@/hooks/useToast'
import { ThemeProvider } from '@/hooks/useTheme'
import { TooltipProvider } from '@/components/ui/tooltip'
import Layout from '@/components/Layout'
import Login from '@/pages/Login'

const Dashboard = lazy(() => import('@/pages/Dashboard'))
const Timesheets = lazy(() => import('@/pages/Timesheets'))
const Leave = lazy(() => import('@/pages/Leave'))
const AdminEntries = lazy(() => import('@/pages/AdminEntries'))
const AdminUsers = lazy(() => import('@/pages/AdminUsers'))
const AdminProjects = lazy(() => import('@/pages/AdminProjects'))
const AdminReports = lazy(() => import('@/pages/AdminReports'))
const AdminAudit = lazy(() => import('@/pages/AdminAudit'))
const AdminLeaveQueue = lazy(() => import('@/pages/AdminLeaveQueue'))
const LeaveCalendar = lazy(() => import('@/pages/LeaveCalendar'))

function FullscreenSpinner() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function PageFallback() {
  return (
    <div className="p-8">
      <div className="h-8 w-48 bg-muted rounded animate-pulse mb-6" />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[1, 2, 3].map(i => <div key={i} className="h-28 bg-muted rounded-xl animate-pulse" />)}
      </div>
    </div>
  )
}

function ProtectedRoute({ children, adminOnly = false }: { children: React.ReactNode; adminOnly?: boolean }) {
  const { user, loading } = useAuth()

  if (loading) return <FullscreenSpinner />
  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && user.role !== 'admin') return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

function AppRoutes() {
  const { user, loading } = useAuth()

  if (loading) return <FullscreenSpinner />

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <Login />} />

      <Route path="/*" element={
        <ProtectedRoute>
          <Layout>
            <Suspense fallback={<PageFallback />}>
              <Routes>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/timesheets" element={<Timesheets />} />
                <Route path="/leave" element={<Leave />} />
                <Route path="/admin/entries" element={<ProtectedRoute adminOnly><AdminEntries /></ProtectedRoute>} />
                <Route path="/admin/leave" element={<ProtectedRoute adminOnly><AdminLeaveQueue /></ProtectedRoute>} />
                <Route path="/admin/leave-calendar" element={<ProtectedRoute adminOnly><LeaveCalendar /></ProtectedRoute>} />
                <Route path="/admin/users" element={<ProtectedRoute adminOnly><AdminUsers /></ProtectedRoute>} />
                <Route path="/admin/projects" element={<ProtectedRoute adminOnly><AdminProjects /></ProtectedRoute>} />
                <Route path="/admin/reports" element={<ProtectedRoute adminOnly><AdminReports /></ProtectedRoute>} />
                <Route path="/admin/audit" element={<ProtectedRoute adminOnly><AdminAudit /></ProtectedRoute>} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </Suspense>
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <ToastProvider>
            <TooltipProvider delayDuration={200}>
              <AppRoutes />
            </TooltipProvider>
          </ToastProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}
