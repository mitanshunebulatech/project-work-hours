import axios from 'axios'

/**
 * axios's default array-param serialization uses bracket notation
 * (employee_ids[]=1&employee_ids[]=2), which FastAPI's
 * `employee_ids: list[int] = Query(None)` does NOT parse — it expects plain
 * repeated keys (employee_ids=1&employee_ids=2). Without this, the
 * Timesheet Module's multi-select employee/project filters would silently
 * send the array and have the backend receive nothing (verified against a
 * real axios 1.7.9 build before this was added — see the PR description).
 */
function serializeParams(params: Record<string, unknown>): string {
  const usp = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null) return
    if (Array.isArray(value)) {
      value.forEach(v => { if (v !== undefined && v !== null) usp.append(key, String(v)) })
    } else {
      usp.append(key, String(value))
    }
  })
  return usp.toString()
}

const api = axios.create({ baseURL: '/api/v1', timeout: 10000, paramsSerializer: { serialize: serializeParams } })

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  res => res,
  async err => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh })
          localStorage.setItem('access_token', data.access_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return api(original)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      } else {
        localStorage.clear()
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export default api

// Auth
export const login = (username: string, password: string) =>
  api.post('/auth/login', { username, password })
export const logout = (refresh_token: string) =>
  api.post('/auth/logout', { refresh_token })
export const changePassword = (current_password: string, new_password: string) =>
  api.post('/auth/change-password', { current_password, new_password })

// Profile
export const getProfile = () => api.get('/profile/me')
export const updateProfile = (data: {
  phone_number?: string | null
  emergency_contact_phone?: string | null
  present_address?: string | null
  years_of_experience?: number | null
  date_of_birth?: string | null
  pan_number?: string | null
}) => api.patch('/profile/me', data)

export const uploadMyProfilePicture = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/profile/me/picture', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
// Blob fetch, not a plain URL — GET /profile/me/picture is auth-protected,
// and <img src> doesn't carry the Authorization header the way axios calls
// do (same reasoning as downloadLeaveAttachment below). Caller is
// responsible for URL.createObjectURL(...) and revoking it on cleanup.
export const getMyProfilePicture = () =>
  api.get('/profile/me/picture', { responseType: 'blob' })

// --- Identity Documents (self-service — employee uploads their own, PM item 6/7) ---
export const getMyIdentityDocuments = () => api.get('/profile/me/identity-documents')
export const uploadMyIdentityDocument = (
  documentType: string, documentNumber: string | null, file: File
) => {
  const formData = new FormData()
  formData.append('document_type', documentType)
  if (documentNumber) formData.append('document_number', documentNumber)
  formData.append('file', file)
  return api.post('/profile/me/identity-documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
export const deleteMyIdentityDocument = (documentId: number) =>
  api.delete(`/profile/me/identity-documents/${documentId}`)
// Admin, view-only — HR oversight, not upload-on-behalf-of (see employees.py docstring)
export const getEmployeeIdentityDocuments = (profileId: number) =>
  api.get(`/employees/${profileId}/identity-documents`)

// Dashboard (admin operations view — PM req #1)
export const getDashboardSummary = () => api.get('/dashboard/summary')

// Projects
export const getProjects = (params?: object) => api.get('/projects', { params })
export const createProject = (data: object) => api.post('/projects', data)
export const updateProject = (id: number, data: object) => api.patch(`/projects/${id}`, data)
export const deleteProject = (id: number) => api.delete(`/projects/${id}`)

// Entries
export const getEntries = (params?: object) => api.get('/entries', { params })
export const createEntry = (data: object) => api.post('/entries', data)
export const updateEntry = (id: number, data: object) => api.patch(`/entries/${id}`, data)
export const deleteEntry = (id: number) => api.delete(`/entries/${id}`)
export const approveEntry = (id: number) => api.post(`/entries/${id}/approve`)
export const rejectEntry = (id: number, reason: string) =>
  api.post(`/entries/${id}/reject`, { reason })
// Points at /entries/export (supports employee_ids/project_ids multi-select),
// not /reports/export — that's a separate, older export path that only
// supports singular employee_id/project_id and doesn't know about the
// Timesheet Module's checkbox filters.
export const exportEntriesCsv = (params?: object) =>
  api.get('/entries/export', { params, responseType: 'blob' })

// Users
export const getUsers = (params?: object) => api.get('/users', { params })
export const createUser = (data: object) => api.post('/users', data)
export const updateUser = (id: number, data: object) => api.patch(`/users/${id}`, data)

// Reports
export const getReportSummary = (params?: object) => api.get('/reports/summary', { params })
export const getAuditLogs = (params?: object) => api.get('/audit', { params })

// --- Leave Types ---
export const getLeaveTypes = (includeInactive = false) =>
  api.get('/leave-types', { params: { include_inactive: includeInactive } })

// --- Leave Balances ---
export const getMyLeaveBalances = (year?: number) =>
  api.get('/leave-balances/me', { params: year ? { year } : undefined })
export const getEmployeeLeaveBalances = (employeeId: number, year?: number) =>
  api.get(`/leave-balances/employee/${employeeId}`, { params: year ? { year } : undefined })

// --- Leave Requests ---
export const previewLeaveRequest = (data: {
  leave_type_id: number; start_date: string; end_date: string
  is_half_day?: boolean; half_day_slot?: 'first_half' | 'second_half' | null
}) => api.post('/leave-requests/preview', data)

export const createLeaveRequest = (data: {
  leave_type_id: number; start_date: string; end_date: string
  is_half_day?: boolean; half_day_slot?: 'first_half' | 'second_half' | null
  reason: string; attachment_path?: string | null
}) => api.post('/leave-requests', data)

// --- Work Schedule Policy ---
export const getWorkSchedulePolicy = () => api.get('/work-schedule-policy')
export const updateWorkSchedulePolicy = (data: {
  first_half_start: string; first_half_end: string
  second_half_start: string; second_half_end: string
}) => api.patch('/work-schedule-policy', data)

export const uploadLeaveAttachment = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/leave-requests/attachments', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const downloadLeaveAttachment = (requestId: number) =>
  api.get(`/leave-requests/${requestId}/attachment`, { responseType: 'blob' })

export const getMyLeaveRequests = (params?: object) => api.get('/leave-requests', { params })

export const getPendingLeaveRequests = (params?: object) =>
  api.get('/leave-requests/pending', { params })

export const getEmployeeLeaveHistory = (employeeId: number, params?: object) =>
  api.get(`/leave-requests/employee/${employeeId}`, { params })

export const cancelLeaveRequest = (id: number) => api.post(`/leave-requests/${id}/cancel`)

export const approveLeaveRequest = (id: number, adminComment?: string) =>
  api.post(`/leave-requests/${id}/approve`, null, { params: adminComment ? { admin_comment: adminComment } : undefined })

export const rejectLeaveRequest = (id: number, adminComment: string) =>
  api.post(`/leave-requests/${id}/reject`, { admin_comment: adminComment })

export const bulkApproveLeaveRequests = (requestIds: number[], adminComment?: string) =>
  api.post('/leave-requests/bulk-approve', { request_ids: requestIds, admin_comment: adminComment })

export const bulkRejectLeaveRequests = (requestIds: number[], adminComment: string) =>
  api.post('/leave-requests/bulk-reject', { request_ids: requestIds, admin_comment: adminComment })

export const getLeaveCalendar = (month: number, year: number) =>
  api.get('/leave-requests/calendar', { params: { month, year } })

export const getLeaveStatistics = (params?: object) =>
  api.get('/leave-requests/statistics', { params })

export const exportLeaveRequestsCsv = (params?: object) =>
  api.get('/leave-requests/export', { params, responseType: 'blob' })

// --- Leave Ledger ---
export const getEmployeeLedger = (employeeId: number, params?: object) =>
  api.get(`/leave-ledger/${employeeId}`, { params })
export const createLedgerAdjustment = (data: object) => api.post('/leave-ledger/adjustments', data)
export const runAnnualGrant = (year: number) =>
  api.post('/leave-ledger/annual-grant/run', null, { params: { year } })

// --- Notifications ---
export const getMyNotifications = (params?: object) => api.get('/notifications/me', { params })
export const getUnreadNotificationCount = () => api.get('/notifications/me/unread-count')
export const markNotificationRead = (id: number) => api.patch(`/notifications/${id}/read`)
export const markAllNotificationsRead = () => api.patch('/notifications/mark-all-read')

// --- Holidays ---
export const getHolidays = (params?: object) => api.get('/holidays', { params })
export const createHoliday = (data: object) => api.post('/holidays', data)
export const updateHoliday = (id: number, data: object) => api.patch(`/holidays/${id}`, data)
export const deactivateHoliday = (id: number) => api.post(`/holidays/${id}/deactivate`)
// Employee-facing read path (PM req #4) — only ever returns a year's
// holidays once an admin has published it via publishHolidayYear below;
// an unpublished year comes back as an empty list, not an error.
export const getPublishedHolidays = (year: number) => api.get(`/holidays/published/${year}`)
// Admin-only bulk actions (PM req #3) — flips is_published on every
// active holiday in the year in one call, rather than one request per row.
export const publishHolidayYear = (year: number) => api.post(`/holidays/publish/${year}`)
export const unpublishHolidayYear = (year: number) => api.post(`/holidays/unpublish/${year}`)

// --- Leave Plans (PM req #6 — informational yearly planning, separate
// from Leave Requests/approval workflow; see LeavePlanService docstring) ---
export const getLeavePlans = (params?: object) => api.get('/leave-plans', { params })
export const getLeavePlan = (id: number) => api.get(`/leave-plans/${id}`)
export const createLeavePlan = (data: {
  leave_type_id: number
  planned_start_date: string
  planned_end_date: string
  reason?: string | null
}) => api.post('/leave-plans', data)
export const updateLeavePlan = (
  id: number,
  data: {
    leave_type_id?: number
    planned_start_date?: string
    planned_end_date?: string
    reason?: string | null
  }
) => api.patch(`/leave-plans/${id}`, data)
export const deleteLeavePlan = (id: number) => api.delete(`/leave-plans/${id}`)

// --- Departments ---
export const getDepartments = (params?: object) => api.get('/departments', { params })
export const createDepartment = (data: { name: string; description?: string | null }) =>
  api.post('/departments', data)
export const updateDepartment = (
  id: number,
  data: { name?: string; description?: string | null; is_active?: boolean }
) => api.patch(`/departments/${id}`, data)
export const deactivateDepartment = (id: number) => api.delete(`/departments/${id}`)

// --- Employees (admin-facing employee profile management) ---
export const getEmployees = (params?: object) => api.get('/employees', { params })
export const getEmployee = (profileId: number) => api.get(`/employees/${profileId}`)
// Legacy path — attaches a profile to an EXISTING user account (predates
// onboardEmployee). Prefer onboardEmployee for new hires; this stays for
// backfilling accounts created before the onboarding module existed.
export const createEmployeeProfile = (data: {
  user_id: number
  full_name: string
  department_id?: number | null
  date_of_birth?: string | null
  date_of_joining?: string | null
  phone_number?: string | null
  emergency_contact_phone?: string | null
  present_address?: string | null
  designation?: string | null
  years_of_experience?: number | null
  pan_number?: string | null
}) => api.post('/employees', data)
export const updateEmployeeProfile = (
  profileId: number,
  data: {
    full_name?: string
    department_id?: number | null
    date_of_birth?: string | null
    date_of_joining?: string | null
    phone_number?: string | null
    emergency_contact_phone?: string | null
    present_address?: string | null
    designation?: string | null
    years_of_experience?: number | null
    pan_number?: string | null
  }
) => api.patch(`/employees/${profileId}`, data)
export const getEmployeePicture = (profileId: number) =>
  api.get(`/employees/${profileId}/picture`, { responseType: 'blob' })

// PM item 7: the single combined onboarding workflow — creates User +
// EmployeeProfile + assigns role/department + sends welcome email in one
// call. Distinct from createEmployeeProfile above, which assumes a User
// already exists (kept as the "attach to existing user" secondary flow).
export const onboardEmployee = (data: {
  first_name: string
  last_name?: string | null
  email: string
  personal_phone_number?: string | null
  emergency_phone_number?: string | null
  present_address?: string | null
  joining_date?: string | null
  birth_date?: string | null
  department_id?: number | null
  designation?: string | null
  years_of_experience?: number | null
  pan_number?: string | null
  role_id: number
}) => api.post('/employees/onboard', data)

// --- Roles & Permissions ---
export const getRoles = () => api.get('/roles')
export const getRole = (roleId: number) => api.get(`/roles/${roleId}`)
export const getPermissions = () => api.get('/permissions')
export const createRole = (data: { name: string; description?: string | null; permission_codes?: string[] }) =>
  api.post('/roles', data)
export const updateRole = (
  roleId: number,
  data: { name?: string; description?: string | null; permission_codes?: string[] }
) => api.patch(`/roles/${roleId}`, data)
export const deleteRole = (roleId: number) => api.delete(`/roles/${roleId}`)
