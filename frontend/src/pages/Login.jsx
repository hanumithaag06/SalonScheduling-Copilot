// Why: User authentication sign-in page with dual Customer & Admin role portals,
// quick-fill demo buttons, email/password validation, and JSON payload submission.

import React, { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { LogIn, Scissors, Shield, User, Sparkles } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

export default function Login() {
  const [activeTab, setActiveTab] = useState('customer') // 'customer' | 'admin'
  const [email, setEmail] = useState('emma.w@example.com')
  const [password, setPassword] = useState('Password123!')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const { success, error } = useToast()
  const navigate = useNavigate()
  const location = useLocation()

  const from = location.state?.from?.pathname || '/'

  const handleSelectRole = (role) => {
    setActiveTab(role)
    if (role === 'admin') {
      setEmail('admin@stylify.com')
      setPassword('Password123!')
    } else {
      setEmail('emma.w@example.com')
      setPassword('Password123!')
    }
  }

  const handleSubmit = async (e) => {
    if (e) e.preventDefault()
    if (!email || !password) {
      error('Please provide both email and password')
      return
    }

    setLoading(true)
    try {
      const user = await login(email, password)
      success(`Welcome back, ${user.name}!`)
      if (user.role === 'admin') {
        navigate('/admin/dashboard')
      } else {
        navigate(from === '/' ? '/my-bookings' : from)
      }
    } catch (err) {
      console.error('Login failed:', err)
      let detail = err.response?.data?.detail || 'Invalid email or password'
      if (Array.isArray(detail)) {
        detail = detail.map((d) => d.msg || JSON.stringify(d)).join(', ')
      }
      error(typeof detail === 'string' ? detail : 'Authentication failed. Please check credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[75vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full bg-white p-8 rounded-3xl border border-gray-100 shadow-xl space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto shadow-xs">
            <Scissors className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-extrabold text-gray-900 tracking-tight">Sign in to Stylify</h2>
          <p className="text-xs text-gray-500">Access appointments, stylist schedules, and salon operations</p>
        </div>

        {/* Dual Role Selector Tabs */}
        <div className="grid grid-cols-2 p-1.5 bg-gray-100 rounded-2xl gap-1">
          <button
            type="button"
            onClick={() => handleSelectRole('customer')}
            className={`flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-bold transition ${
              activeTab === 'customer'
                ? 'bg-white text-indigo-700 shadow-xs'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            <User className="w-4 h-4" />
            <span>Customer Login</span>
          </button>
          <button
            type="button"
            onClick={() => handleSelectRole('admin')}
            className={`flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-bold transition ${
              activeTab === 'admin'
                ? 'bg-white text-indigo-700 shadow-xs'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            <Shield className="w-4 h-4" />
            <span>Admin Portal</span>
          </button>
        </div>

        {/* Quick Demo Credentials Info Pill */}
        <div className="p-3 bg-indigo-50/70 border border-indigo-100 rounded-2xl text-[11px] text-indigo-900 flex items-center justify-between">
          <div>
            <span className="font-bold">Active Role:</span> {activeTab === 'admin' ? 'Salon Administrator' : 'Customer Account'}
          </div>
          <button
            type="button"
            onClick={() => handleSelectRole(activeTab)}
            className="text-indigo-600 hover:text-indigo-800 font-bold underline text-[11px]"
          >
            Reset Demo
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. client@example.com"
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-semibold rounded-xl shadow-md transition flex items-center justify-center gap-2"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <>
                <LogIn className="w-4 h-4" />
                <span>Sign In as {activeTab === 'admin' ? 'Administrator' : 'Customer'}</span>
              </>
            )}
          </button>
        </form>

        <div className="text-center text-xs text-gray-500 pt-2 border-t border-gray-100">
          Don't have an account yet?{' '}
          <Link to="/register" className="font-semibold text-indigo-600 hover:text-indigo-700">
            Create customer account
          </Link>
        </div>
      </div>
    </div>
  )
}
