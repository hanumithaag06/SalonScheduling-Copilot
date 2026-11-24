// Why: Main responsive navigation header with brand branding, links, auth controls,
// notification bell, and mobile hamburger drawer.

import React, { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Scissors, LogOut, Menu, X, Shield } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import NotificationBell from './NotificationBell'

export default function Navbar() {
  const { user, isAuthenticated, isAdmin, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/')
    setMobileMenuOpen(false)
  }

  const isActive = (path) => location.pathname === path

  return (
    <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-gray-100 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-md shadow-indigo-100 group-hover:scale-105 transition-transform">
            <Scissors className="w-5 h-5" />
          </div>
          <div>
            <span className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-gray-900 to-indigo-950 bg-clip-text text-transparent">
              Stylify
            </span>
            <span className="hidden sm:inline-block ml-1.5 text-[10px] font-semibold text-indigo-600 uppercase tracking-widest bg-indigo-50 px-2 py-0.5 rounded-full">
              Salon Copilot
            </span>
          </div>
        </Link>

        {/* Desktop Navigation Links */}
        <nav className="hidden md:flex items-center gap-1 font-medium text-sm text-gray-600">
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
            Book Appointment
          </Link>
          {isAuthenticated && (
            <>
              <Link
                to="/my-bookings"
                className={`px-3 py-2 rounded-lg transition ${
                  isActive('/my-bookings') ? 'bg-indigo-50 text-indigo-600 font-semibold' : 'hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                My Bookings
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
          {isAdmin && (
            <Link
              to="/admin/dashboard"
              className={`flex items-center gap-1 px-3 py-2 rounded-lg transition text-indigo-700 bg-indigo-50/80 hover:bg-indigo-100 ${
                location.pathname.startsWith('/admin') ? 'ring-2 ring-indigo-500 font-semibold' : ''
              }`}
            >
              <Shield className="w-4 h-4 text-indigo-600" />
              Admin Portal
            </Link>
          )}
        </nav>

        {/* Right Action Icons & Auth Profile */}
        <div className="flex items-center gap-3">
          <NotificationBell />

          {isAuthenticated ? (
            <div className="hidden sm:flex items-center gap-3 pl-2 border-l border-gray-200">
              <div className="text-right">
                <p className="text-xs font-semibold text-gray-900 leading-tight">{user?.name}</p>
                <p className="text-[10px] text-gray-500 capitalize">{user?.role}</p>
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
                className="text-sm font-semibold text-gray-700 hover:text-indigo-600 px-3 py-2 transition"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-xl shadow-sm transition"
              >
                Register
              </Link>
            </div>
          )}

          {/* Mobile Menu Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen((o) => !o)}
            className="md:hidden p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-gray-100 bg-white px-4 pt-2 pb-6 space-y-2 animate-in slide-in-from-top-2">
          <Link
            to="/services"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-lg text-base font-medium text-gray-700 hover:bg-gray-50"
          >
            Services & Stylists
          </Link>
          <Link
            to="/book"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-lg text-base font-medium text-gray-700 hover:bg-gray-50"
          >
            Book Appointment
          </Link>
          {isAuthenticated && (
            <>
              <Link
                to="/my-bookings"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-lg text-base font-medium text-gray-700 hover:bg-gray-50"
              >
                My Bookings
              </Link>
              <Link
                to="/waitlist"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-lg text-base font-medium text-gray-700 hover:bg-gray-50"
              >
                Waitlist
              </Link>
            </>
          )}
          {isAdmin && (
            <Link
              to="/admin/dashboard"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-base font-semibold text-indigo-700 bg-indigo-50"
            >
              <Shield className="w-5 h-5" />
              Admin Portal
            </Link>
          )}

          <div className="pt-4 border-t border-gray-100">
            {isAuthenticated ? (
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-gray-900">{user?.name}</p>
                  <p className="text-xs text-gray-500">{user?.email}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="px-3 py-1.5 text-sm text-rose-600 bg-rose-50 rounded-lg font-medium"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex gap-2">
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex-1 text-center py-2 text-sm font-medium border border-gray-200 rounded-xl"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex-1 text-center py-2 text-sm font-semibold text-white bg-indigo-600 rounded-xl"
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
