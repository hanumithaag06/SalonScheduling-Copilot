// Why: Admin portal layout with navigation tabs (Dashboard, Stylist Calendar, Bookings)
// and quick CSV export download action.

import React from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { LayoutDashboard, Calendar, BookOpen, Download, Shield } from 'lucide-react'
import api from '../../api/client'
import { useToast } from '../../context/ToastContext'

export default function AdminLayout() {
  const location = useLocation()
  const { success, error } = useToast()

  const handleExportCSV = async () => {
    try {
      const resp = await api.get('/admin/export/bookings.csv', {
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([resp.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `stylify_bookings_${new Date().toISOString().split('T')[0]}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      success('Bookings CSV exported successfully!')
    } catch (err) {
      console.error('CSV export failed:', err)
      error('Failed to export bookings CSV.')
    }
  }

  const navItems = [
    { to: '/admin/dashboard', label: 'Analytics Dashboard', icon: LayoutDashboard },
    { to: '/admin/calendar', label: 'Stylist Calendar', icon: Calendar },
    { to: '/admin/bookings', label: 'Bookings Management', icon: BookOpen },
  ]

  return (
    <div className="py-8 space-y-8">
      {/* Admin Top Header Banner */}
      <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shadow-md shadow-indigo-100">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-black text-gray-900 tracking-tight">Admin Operations Portal</h1>
              <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full uppercase">
                Authorized
              </span>
            </div>
            <p className="text-xs text-gray-500">Real-time salon analytics, multi-stylist schedules, and proxy bookings.</p>
          </div>
        </div>

        {/* Global CSV Export Button */}
        <button
          onClick={handleExportCSV}
          className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 hover:bg-black text-white text-xs font-semibold rounded-xl shadow-xs transition"
        >
          <Download className="w-4 h-4" />
          <span>Export Bookings CSV</span>
        </button>
      </div>

      {/* Admin Subnav Tabs */}
      <div className="flex border-b border-gray-200 gap-2">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = location.pathname === item.to
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex items-center gap-2 pb-3 px-3 text-xs font-semibold border-b-2 transition ${
                active
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </div>

      {/* Nested Admin Page Content */}
      <Outlet />
    </div>
  )
}
