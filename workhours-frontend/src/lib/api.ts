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
