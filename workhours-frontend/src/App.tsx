import { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/hooks/useAuth'
import { ToastProvider } from '@/hooks/useToast'
import { ThemeProvider } from '@/hooks/useTheme'
import { TooltipProvider } from '@/components/ui/tooltip'
import Layout from '@/components/Layout'
import Login from '@/pages/Login'
import ForcedPasswordChange from '@/pages/ForcedPasswordChange'

const Dashboard = lazy(() => import('@/pages/Dashboard'))
const Timesheets = lazy(() => import('@/pages/Timesheets'))
const Leave = lazy(() => import('@/pages/Leave'))
const Profile = lazy(() => import('@/pages/Profile'))
const AdminTimesheets = lazy(() => import('@/pages/AdminTimesheets'))
const AdminUsers = lazy(() => import('@/pages/AdminUsers'))
const AdminRoles = lazy(() => import('@/pages/AdminRoles'))
const AdminDepartments = lazy(() => import('@/pages/AdminDepartments'))
const AdminEmployees = lazy(() => import('@/pages/AdminEmployees'))
const AdminProjects = lazy(() => import('@/pages/AdminProjects'))
const AdminReports = lazy(() => import('@/pages/AdminReports'))
const AdminAudit = lazy(() => import('@/pages/AdminAudit'))
const AdminLeaveQueue = lazy(() => import('@/pages/AdminLeaveQueue'))
const LeaveCalendar = lazy(() => import('@/pages/LeaveCalendar'))
const AdminHolidays = lazy(() => import('@/pages/AdminHolidays'))
const HolidayCalendar = lazy(() => import('@/pages/HolidayCalendar'))
const LeavePlans = lazy(() => import('@/pages/LeavePlans'))

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
  const { user, loading, mustChangePassword } = useAuth()

  if (loading) return <FullscreenSpinner />
  // PM V2 Part 4: checked before the !user check below — a locked account
  // has user=null (see useAuth.tsx), so without this it would bounce to
  // /login instead of the forced-change screen.
  if (mustChangePassword) return <Navigate to="/change-password" replace />
  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && user.role !== 'admin') return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

function AppRoutes() {
  const { user, loading, mustChangePassword } = useAuth()

  if (loading) return <FullscreenSpinner />

  return (
    <Routes>
      <Route path="/login" element={
        mustChangePassword ? <Navigate to="/change-password" replace />
        : user ? <Navigate to="/dashboard" replace />
        : <Login />
      } />

      {/* PM V2 Part 4: only reachable while locked — a normal user hitting
          this URL directly gets bounced away rather than landing on a
          change-password form with no context for why. Self-service
          (voluntary) password change is a separate, future concern on the
          Profile page, not this route. */}
      <Route path="/change-password" element={
        mustChangePassword ? <ForcedPasswordChange /> : <Navigate to={user ? '/dashboard' : '/login'} replace />
      } />

      <Route path="/*" element={
        <ProtectedRoute>
          <Layout>
            <Suspense fallback={<PageFallback />}>
              <Routes>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/timesheets" element={<Timesheets />} />
                <Route path="/leave" element={<Leave />} />
                <Route path="/leave-plans" element={<LeavePlans />} />
                <Route path="/holidays" element={<HolidayCalendar />} />
                <Route path="/profile" element={<Profile />} />
                <Route path="/admin/timesheets" element={<ProtectedRoute adminOnly><AdminTimesheets /></ProtectedRoute>} />
                <Route path="/admin/leave" element={<ProtectedRoute adminOnly><AdminLeaveQueue /></ProtectedRoute>} />
                <Route path="/admin/leave-calendar" element={<ProtectedRoute adminOnly><LeaveCalendar /></ProtectedRoute>} />
                <Route path="/admin/holidays" element={<ProtectedRoute adminOnly><AdminHolidays /></ProtectedRoute>} />
                <Route path="/admin/users" element={<ProtectedRoute adminOnly><AdminUsers /></ProtectedRoute>} />
                <Route path="/admin/roles" element={<ProtectedRoute adminOnly><AdminRoles /></ProtectedRoute>} />
                <Route path="/admin/departments" element={<ProtectedRoute adminOnly><AdminDepartments /></ProtectedRoute>} />
                <Route path="/admin/employees" element={<ProtectedRoute adminOnly><AdminEmployees /></ProtectedRoute>} />
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
