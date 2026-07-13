import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1', timeout: 10000 })

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
  date_of_birth?: string | null
  pan_number?: string | null
}) => api.patch('/profile/me', data)

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
  leave_type_id: number; start_date: string; end_date: string; is_half_day?: boolean
}) => api.post('/leave-requests/preview', data)

export const createLeaveRequest = (data: {
  leave_type_id: number; start_date: string; end_date: string
  is_half_day?: boolean; reason: string; attachment_path?: string | null
}) => api.post('/leave-requests', data)

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
export const createEmployeeProfile = (data: {
  user_id: number
  full_name: string
  department_id?: number | null
  date_of_birth?: string | null
  date_of_joining?: string | null
  phone_number?: string | null
  designation?: string | null
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
    designation?: string | null
    pan_number?: string | null
  }
) => api.patch(`/employees/${profileId}`, data)
