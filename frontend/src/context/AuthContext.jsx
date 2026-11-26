// Why: Authentication context managing JWT token, current user state, login, register, and logout.
// Persists credentials in localStorage and fetches fresh user profile from /auth/me on mount.

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user')
    try {
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }, [])

  // Fetch /auth/me on initialization if token exists
  useEffect(() => {
    async function loadUser() {
      if (!token) {
        setLoading(false)
        return
      }
      try {
        const resp = await api.get('/auth/me')
        setUser(resp.data)
        localStorage.setItem('user', JSON.stringify(resp.data))
      } catch (err) {
        console.error('Failed to restore auth session:', err)
        logout()
      } finally {
        setLoading(false)
      }
    }
    loadUser()
  }, [token, logout])

  const login = useCallback(async (email, password) => {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)

    const resp = await api.post('/auth/login', formData)
    const { access_token } = resp.data
    localStorage.setItem('token', access_token)
    setToken(access_token)

    // Fetch user details
    const meResp = await api.get('/auth/me', {
      headers: { Authorization: `Bearer ${access_token}` },
    })
    setUser(meResp.data)
    localStorage.setItem('user', JSON.stringify(meResp.data))
    return meResp.data
  }, [])

  const register = useCallback(async (userData) => {
    const resp = await api.post('/auth/register', userData)
    return resp.data
  }, [])

  const isAuthenticated = Boolean(token && user)
  const isAdmin = Boolean(user && user.role === 'admin')

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        loading,
        isAuthenticated,
        isAdmin,
        login,
        register,
        logout,
        setUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
