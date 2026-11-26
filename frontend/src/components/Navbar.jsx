// Why: Main responsive navigation header with dual mode switcher (User Mode vs Admin Mode),
// brand branding, contextual links, auth controls, notification bell, and mobile drawer.

import React, { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import {
  Scissors,
  LogOut,
  Menu,
  X,
  Shield,
  User,
  LayoutDashboard,
  Calendar,
  CalendarCheck,
  Sparkles,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import NotificationBell from './NotificationBell'

export default function Navbar() {
  const { user, isAuthenticated, isAdmin, logout, switchToMode } = useAuth()
  const { success, info, error } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [switching, setSwitching] = useState(false)

  const inAdminRoute = location.pathname.startsWith('/admin')
  const currentMode = inAdminRoute || (isAdmin && !location.pathname.startsWith('/services') && !location.pathname.startsWith('/book')) ? 'admin' : 'user'

  const handleLogout = () => {
    logout()
    navigate('/')
    setMobileMenuOpen(false)
  }

  const handleModeSwitch = async (targetMode) => {
    if (switching) return
    setSwitching(true)

    try {
      if (targetMode === 'admin') {
        if (!isAdmin) {
          await switchToMode('admin')
          success('Switched to Admin Mode (Logged in as Administrator)')
        } else {
          info('Entered Admin Mode')
        }
        navigate('/admin/dashboard')
      } else {
        if (isAdmin) {
          await switchToMode('user')
          info('Switched to User Mode (Customer experience)')
        } else {
          info('Entered User Mode')
        }
        navigate('/')
      }
    } catch (err) {
      console.error('Mode switch failed:', err)
      error('Could not switch mode. Please try signing in.')
    } finally {
      setSwitching(false)
      setMobileMenuOpen(false)
    }
  }

  const isActive = (path) => location.pathname === path

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-gray-100 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-2">
        {/* Brand Logo */}
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2.5 group shrink-0">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-md shadow-indigo-100 group-hover:scale-105 transition-transform">
              <Scissors className="w-5 h-5" />
            </div>
            <div>
              <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-gray-900 to-indigo-950 bg-clip-text text-transparent">
                Stylify
              </span>
            </div>
          </Link>

          {/* DUAL MODE TOGGLE (User Mode vs Admin Mode) */}
          <div className="hidden sm:flex items-center bg-gray-100 p-1 rounded-xl border border-gray-200/80 text-xs shadow-inner ml-2">
            <button
              type="button"
              onClick={() => handleModeSwitch('user')}
              disabled={switching}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg font-semibold transition cursor-pointer ${
                currentMode === 'user'
                  ? 'bg-white text-indigo-700 shadow-xs'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              <User className="w-3.5 h-3.5 text-indigo-500" />
              <span>User Mode</span>
            </button>
            <button
              type="button"
              onClick={() => handleModeSwitch('admin')}
              disabled={switching}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg font-semibold transition cursor-pointer ${
                currentMode === 'admin'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              <Shield className="w-3.5 h-3.5 text-amber-300" />
              <span>Admin Mode</span>
            </button>
          </div>
        </div>

        {/* Navigation Links (Context-Aware for Current Mode) */}
        <nav className="hidden lg:flex items-center gap-1 font-medium text-xs text-gray-600">
          {currentMode === 'admin' ? (
            <>
              <Link
                to="/admin/dashboard"
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition ${
                  isActive('/admin/dashboard')
                    ? 'bg-indigo-50 text-indigo-700 font-semibold ring-1 ring-indigo-200'
                    : 'hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <LayoutDashboard className="w-4 h-4 text-indigo-600" />
                Dashboard Metrics
              </Link>
              <Link
                to="/admin/calendar"
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition ${
                  isActive('/admin/calendar')
                    ? 'bg-indigo-50 text-indigo-700 font-semibold ring-1 ring-indigo-200'
                    : 'hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <Calendar className="w-4 h-4 text-indigo-600" />
                Stylist Calendar
              </Link>
              <Link
                to="/admin/bookings"
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition ${
                  isActive('/admin/bookings')
                    ? 'bg-indigo-50 text-indigo-700 font-semibold ring-1 ring-indigo-200'
                    : 'hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <CalendarCheck className="w-4 h-4 text-indigo-600" />
                All Bookings & Export
              </Link>
            </>
          ) : (
            <>
              <Link
                to="/services"
                className={`px-3 py-2 rounded-lg transition ${
                  isActive('/services') ? 'bg-indigo-50 text-indigo-600 font-semibold' : 'hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                Services & Stylists
              </Link>
              <Link
                to="/book"
                className={`px-3 py-2 rounded-lg transition ${
                  isActive('/book') ? 'bg-indigo-50 text-indigo-600 font-semibold' : 'hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                Book 1-on-1 Slot
              </Link>
              {isAuthenticated && (
                <>
                  <Link
                    to="/my-bookings"
                    className={`px-3 py-2 rounded-lg transition ${
                      isActive('/my-bookings') ? 'bg-indigo-50 text-indigo-600 font-semibold' : 'hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    My Appointments
                  </Link>
                  <Link
                    to="/waitlist"
                    className={`px-3 py-2 rounded-lg transition ${
                      isActive('/waitlist') ? 'bg-indigo-50 text-indigo-600 font-semibold' : 'hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    Waitlist
                  </Link>
                </>
              )}
            </>
          )}
        </nav>

        {/* Right Action Icons & Auth Profile */}
        <div className="flex items-center gap-2 sm:gap-3">
          <NotificationBell />

          {isAuthenticated ? (
            <div className="flex items-center gap-2 pl-2 border-l border-gray-200">
              <div className="hidden sm:block text-right">
                <p className="text-xs font-semibold text-gray-900 leading-tight flex items-center justify-end gap-1">
                  <span>{user?.name}</span>
                  {user?.role === 'admin' ? (
                    <span className="text-[9px] font-bold uppercase bg-amber-100 text-amber-800 px-1.5 py-0.2 rounded">
                      Admin
                    </span>
                  ) : (
                    <span className="text-[9px] font-bold uppercase bg-indigo-50 text-indigo-700 px-1.5 py-0.2 rounded">
                      Customer
                    </span>
                  )}
                </p>
                <p className="text-[10px] text-gray-500 truncate max-w-[140px]">{user?.email}</p>
              </div>
              <button
                onClick={handleLogout}
                title="Sign out"
                className="p-2 text-gray-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="hidden sm:flex items-center gap-2">
              <Link
                to="/login"
                className="text-xs font-semibold text-gray-700 hover:text-indigo-600 px-3 py-2 transition"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 px-3.5 py-1.5 rounded-xl shadow-xs transition"
              >
                Register
              </Link>
            </div>
          )}

          {/* Mobile Menu Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen((o) => !o)}
            className="lg:hidden p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-b border-gray-100 bg-white px-4 pt-3 pb-6 space-y-3 animate-in slide-in-from-top-2">
          {/* Mobile Mode Switcher */}
          <div className="flex items-center justify-between bg-gray-50 p-2 rounded-xl border border-gray-200">
            <span className="text-xs font-semibold text-gray-600">Select Mode:</span>
            <div className="flex bg-gray-200/80 p-0.5 rounded-lg text-xs">
              <button
                onClick={() => handleModeSwitch('user')}
                className={`px-3 py-1 rounded-md font-semibold ${
                  currentMode === 'user' ? 'bg-white text-indigo-700 shadow-xs' : 'text-gray-600'
                }`}
              >
                User
              </button>
              <button
                onClick={() => handleModeSwitch('admin')}
                className={`px-3 py-1 rounded-md font-semibold ${
                  currentMode === 'admin' ? 'bg-indigo-600 text-white shadow-xs' : 'text-gray-600'
                }`}
              >
                Admin
              </button>
            </div>
          </div>

          {currentMode === 'admin' ? (
            <div className="space-y-1">
              <p className="text-[10px] font-bold uppercase tracking-wider text-indigo-600 px-3">
                Admin Management
              </p>
              <Link
                to="/admin/dashboard"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold text-gray-800 hover:bg-indigo-50"
              >
                <LayoutDashboard className="w-4 h-4 text-indigo-600" />
                Dashboard Metrics
              </Link>
              <Link
                to="/admin/calendar"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold text-gray-800 hover:bg-indigo-50"
              >
                <Calendar className="w-4 h-4 text-indigo-600" />
                Stylist Calendar
              </Link>
              <Link
                to="/admin/bookings"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold text-gray-800 hover:bg-indigo-50"
              >
                <CalendarCheck className="w-4 h-4 text-indigo-600" />
                All Bookings & Export
              </Link>
            </div>
          ) : (
            <div className="space-y-1">
              <p className="text-[10px] font-bold uppercase tracking-wider text-indigo-600 px-3">
                Customer Services
              </p>
              <Link
                to="/services"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Services & Stylists
              </Link>
              <Link
                to="/book"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Book 1-on-1 Slot
              </Link>
              {isAuthenticated && (
                <>
                  <Link
                    to="/my-bookings"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    My Appointments
                  </Link>
                  <Link
                    to="/waitlist"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Waitlist
                  </Link>
                </>
              )}
            </div>
          )}

          <div className="pt-3 border-t border-gray-100">
            {isAuthenticated ? (
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-gray-900">{user?.name}</p>
                  <p className="text-[10px] text-gray-500">{user?.email}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="px-3 py-1.5 text-xs text-rose-600 bg-rose-50 rounded-lg font-medium"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex gap-2">
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex-1 text-center py-2 text-xs font-medium border border-gray-200 rounded-xl"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex-1 text-center py-2 text-xs font-semibold text-white bg-indigo-600 rounded-xl"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  )
}
    </header>
  )
}
