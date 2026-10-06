import { createContext, useContext, useEffect, useState } from 'react'
import api from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // Only "loading" if there is a saved token to check.
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem('token')))

  // On page load, if we have a token, ask the API who we are.
  useEffect(() => {
    if (!localStorage.getItem('token')) return
    api.get('/auth/me')
      .then((response) => setUser(response.data))
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false))
  }, [])

  async function login(email, password) {
    // The login endpoint uses the OAuth2 form format, not JSON.
    const form = new URLSearchParams({ username: email, password })
    const { data } = await api.post('/auth/login', form)
    localStorage.setItem('token', data.access_token)
    const me = await api.get('/auth/me')
    setUser(me.data)
    return me.data
  }

  async function signup(fullName, email, password) {
    await api.post('/auth/signup', { full_name: fullName, email, password })
    return login(email, password)
  }

  function logout() {
    localStorage.removeItem('token')
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, loading, login, signup, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}

// Where each role lands after logging in.
export function homeFor(user) {
  return { applicant: '/applicant', underwriter: '/underwriter', admin: '/admin' }[user?.role] || '/login'
}