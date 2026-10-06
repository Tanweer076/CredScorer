import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api' })

// Send the login token with every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Token expired or invalid: log out and go to the login page.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config.url.includes('/auth/login')) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// Turn a FastAPI error into a sentence a person can read.
export function errorMessage(error) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    // Validation errors: [{loc: ["body", "term_months"], msg: "..."}]
    return detail.map((d) => {
      const field = d.loc[d.loc.length - 1]
      const message = d.msg.replace(/^Value error, /, '')
      return field === 'body' ? message : `${field}: ${message}` // "body" = a rule about several fields
    }).join('; ')
  }
  return error.message || 'Something went wrong'
}

export default api