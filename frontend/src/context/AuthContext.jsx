import { createContext, useContext, useState, useCallback } from 'react'
import * as api from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('access_token'))

  const doLogin = useCallback(async (username, password) => {
    const response = await api.login({ username, password })
    localStorage.setItem('access_token', response.data.access_token)
    setToken(response.data.access_token)
  }, [])

  const doSignup = useCallback(async (username, password, securityQuestion, securityAnswer) => {
    const response = await api.signup({
      username,
      password,
      security_question: securityQuestion,
      security_answer: securityAnswer,
    })
    localStorage.setItem('access_token', response.data.access_token)
    setToken(response.data.access_token)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    setToken(null)
  }, [])

  const value = {
    isAuthenticated: Boolean(token),
    login: doLogin,
    signup: doSignup,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used inside an AuthProvider')
  }
  return ctx
}
