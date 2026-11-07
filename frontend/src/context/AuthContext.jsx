// Login state for the whole app, shared through React context
import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, TOKEN_KEY } from '../api/client'

// localStorage key for the saved user profile
const USER_KEY = 'campusbite_user'
const AuthContext = createContext(null)

// Where each role lands after logging in
export const HOME_BY_ROLE = { customer: '/restaurants', owner: '/owner', delivery: '/delivery' }

// Provides the current user plus login, register and logout to every component below it
export function AuthProvider({ children }) {
  // Read the saved login once, so a page refresh keeps the user logged in
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem(USER_KEY)
    const savedToken = localStorage.getItem(TOKEN_KEY)
    // Only restore the user if the token is also there
    if (savedUser && savedToken) return JSON.parse(savedUser)
    return null
  })

  // Stores the token and user returned by the backend, then updates state
  const saveSession = (data) => {
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    setUser(data.user)
    return data.user
  }

  // Logs in with email and password and returns the user
  const login = async (email, password) => {
    const data = await api('/auth/login', { method: 'POST', body: { email, password } })
    return saveSession(data)
  }

  // Creates an account and logs straight in, returning the user
  const register = async (form) => {
    const data = await api('/auth/register', { method: 'POST', body: form })
    return saveSession(data)
  }

  // Forgets the saved login; useCallback keeps it stable for the event listener below
  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setUser(null)
  }, [])

  // The API client fires this when the backend says the token is no longer valid
  useEffect(() => {
    window.addEventListener('auth:logout', logout)
    return () => window.removeEventListener('auth:logout', logout)
  }, [logout])

  return <AuthContext.Provider value={{ user, login, register, logout }}>{children}</AuthContext.Provider>
}

// Hook for reading the auth state in any component
export const useAuth = () => useContext(AuthContext)
