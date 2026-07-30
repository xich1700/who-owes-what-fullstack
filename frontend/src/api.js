import axios from 'axios'

const BASE_URL = 'http://localhost:8000'

const client = axios.create({ baseURL: BASE_URL })

// Attach the stored token to every request automatically.
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// If the token is invalid/expired, the backend returns 401 - clear it and
// bounce back to the login screen rather than showing a confusing error.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Pulls a readable message out of a FastAPI error response.
export function apiErrorMessage(error, fallback = 'Something went wrong.') {
  return error?.response?.data?.detail || fallback
}

// ---- Auth ----
export const signup = (payload) => client.post('/auth/signup', payload)
export const login = (payload) => client.post('/auth/login', payload)
export const forgotPasswordLookup = (payload) => client.post('/auth/forgot-password/lookup', payload)
export const forgotPasswordReset = (payload) => client.post('/auth/forgot-password/reset', payload)

// ---- Groups ----
export const listGroups = () => client.get('/groups')
export const createGroup = (payload) => client.post('/groups', payload)
export const getGroup = (groupId) => client.get(`/groups/${groupId}`)
export const deleteGroup = (groupId) => client.delete(`/groups/${groupId}`)
export const closeGroup = (groupId) => client.post(`/groups/${groupId}/close`)

// ---- People ----
export const listPeople = (groupId) => client.get(`/groups/${groupId}/people`)
export const addPerson = (groupId, payload) => client.post(`/groups/${groupId}/people`, payload)
export const removePerson = (groupId, personId) => client.delete(`/groups/${groupId}/people/${personId}`)

// ---- Expenses ----
export const listExpenses = (groupId) => client.get(`/groups/${groupId}/expenses`)
export const addExpense = (groupId, payload) => client.post(`/groups/${groupId}/expenses`, payload)
export const updateExpense = (groupId, expenseId, payload) =>
  client.put(`/groups/${groupId}/expenses/${expenseId}`, payload)
export const deleteExpense = (groupId, expenseId) =>
  client.delete(`/groups/${groupId}/expenses/${expenseId}`)
export const repeatExpense = (groupId, expenseId) =>
  client.post(`/groups/${groupId}/expenses/${expenseId}/repeat`)
export const parseExpense = (groupId, sentence) =>
  client.post(`/groups/${groupId}/expenses/parse`, { sentence })

export const scanReceipt = (groupId, file, apiKey) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('api_key', apiKey)
  // Let the browser set the multipart boundary itself - don't set Content-Type manually.
  return client.post(`/groups/${groupId}/expenses/scan-receipt`, formData)
}

// ---- Repayments ----
export const listRepayments = (groupId) => client.get(`/groups/${groupId}/repayments`)
export const addRepayment = (groupId, payload) => client.post(`/groups/${groupId}/repayments`, payload)
export const deleteRepayment = (groupId, repaymentId) =>
  client.delete(`/groups/${groupId}/repayments/${repaymentId}`)

// ---- Totals ----
export const getTotals = (groupId) => client.get(`/groups/${groupId}/totals`)

// ---- Public share link (no token needed - use a plain axios call, not the interceptor-wrapped client,
// so a stale/invalid token in localStorage never gets attached to a public request). ----
const publicClient = axios.create({ baseURL: BASE_URL })
export const getSharedGroup = (token) => publicClient.get(`/share/${token}`)
export const getSharedPeople = (token) => publicClient.get(`/share/${token}/people`)
export const getSharedExpenses = (token) => publicClient.get(`/share/${token}/expenses`)
export const getSharedTotals = (token) => publicClient.get(`/share/${token}/totals`)

export default client
