// Why: Recharts visual analytics dashboard for salon administrators.
// Visualizes bookings per day, revenue per service, stylist utilization %, and peak hour distribution.

import React, { useState, useEffect } from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts'
import { DollarSign, Calendar, Users, AlertCircle } from 'lucide-react'
import api from '../../api/client'
import { useToast } from '../../context/ToastContext'

export default function AdminDashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const { error } = useToast()

  const fetchDashboard = async () => {
    setLoading(true)
    try {
      const resp = await api.get('/admin/dashboard')
      setData(resp.data)
    } catch (err) {
      console.error('Failed to load dashboard analytics:', err)
      error('Could not load admin dashboard metrics.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboard()
  }, [])

  if (loading) {
    return (
      <div className="py-20 flex flex-col justify-center items-center gap-3">
        <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs text-gray-500">Compiling real-time salon metrics...</p>
      </div>
    )
  }

  if (!data) return null

  // Format chart data
  const bookingsPerDayData = (data.bookings_per_day || []).map((item) => ({
    date: item.date,
    bookings: item.count,
  }))

  const revenuePerServiceData = (data.revenue_per_service || []).map((item) => ({
    name: item.service_name.length > 15 ? item.service_name.substring(0, 15) + '...' : item.service_name,
    fullName: item.service_name,
    revenue: Number(item.revenue),
    count: item.count,
  }))

  const stylistUtilData = (data.stylist_utilization || []).map((item) => ({
    name: item.stylist_name,
    utilization: Math.round(item.utilization_pct * 10) / 10,
    bookedMinutes: item.total_booked_minutes,
  }))

  const peakHoursData = (data.peak_hours || []).map((item) => ({
    hour: `${item.hour}:00`,
    bookings: item.count,
  }))

  const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const hours = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]

  // Map heatmap data: key `${weekday}_${hour}`
  const heatmapMap = new Map()
  ;(data.heatmap || []).forEach((c) => {
    heatmapMap.set(`${c.weekday}_${c.hour}`, c.count)
  })

  return (
    <div className="space-y-8 animate-in fade-in">
      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Bookings */}
        <div className="bg-white p-5 rounded-3xl border border-gray-100 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-gray-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Bookings</span>
            <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Calendar className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black text-gray-900">{data.total_bookings}</p>
          <span className="text-[11px] text-gray-400">All registered appointments</span>
        </div>

        {/* Total Revenue */}
        <div className="bg-white p-5 rounded-3xl border border-gray-100 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-gray-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Revenue</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black text-emerald-700">${Number(data.total_revenue).toFixed(2)}</p>
          <span className="text-[11px] text-emerald-600 font-medium">Gross confirmed revenue</span>
        </div>

        {/* Cancellation Rate */}
        <div className="bg-white p-5 rounded-3xl border border-gray-100 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-gray-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Cancellation Rate</span>
            <div className="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
              <AlertCircle className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black text-rose-700">
            {(data.cancellation_rate * 100).toFixed(1)}%
          </p>
          <span className="text-[11px] text-gray-400">Within policy limits</span>
        </div>

        {/* Overall Stylist Utilization */}
        <div className="bg-white p-5 rounded-3xl border border-gray-100 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-gray-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Avg Stylist Load</span>
            <div className="w-8 h-8 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black text-violet-700">
            {stylistUtilData.length > 0
              ? (
                  stylistUtilData.reduce((acc, curr) => acc + curr.utilization, 0) /
                  stylistUtilData.length
                ).toFixed(1)
              : 0}
            %
          </p>
          <span className="text-[11px] text-violet-600 font-medium">Booked vs working hours</span>
        </div>
      </div>

      {/* Main Charts Row: Bookings per Day & Revenue per Service */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bookings Per Day Area Chart */}
        <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-xs space-y-4">
          <h3 className="font-bold text-sm text-gray-900">Bookings Trend (Per Day)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={bookingsPerDayData}>
                <defs>
                  <linearGradient id="bookingGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="bookings"
                  stroke="#4f46e5"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#bookingGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Revenue Per Service Bar Chart */}
        <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-xs space-y-4">
          <h3 className="font-bold text-sm text-gray-900">Revenue by Service Offering ($)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={revenuePerServiceData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip />
                <Bar dataKey="revenue" fill="#10b981" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Second Charts Row: Stylist Utilization & Peak Hours */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Stylist Utilization Bar Chart */}
        <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-xs space-y-4">
          <h3 className="font-bold text-sm text-gray-900">Stylist Utilization Rate (%)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stylistUtilData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip />
                <Bar dataKey="utilization" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Peak Hours Distribution */}
        <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-xs space-y-4">
          <h3 className="font-bold text-sm text-gray-900">Peak Appointment Hours</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={peakHoursData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip />
                <Bar dataKey="bookings" fill="#f59e0b" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Heatmap Section: Day-by-Hour Intensity Grid */}
      <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-xs space-y-4">
        <div>
          <h3 className="font-bold text-sm text-gray-900">Weekly Appointment Heatmap</h3>
          <p className="text-xs text-gray-500">Distribution of bookings across days and hours.</p>
        </div>

        <div className="overflow-x-auto">
          <div className="min-w-[600px] space-y-1">
            {/* Header row of hours */}
            <div className="grid grid-cols-11 gap-1 text-[11px] font-semibold text-gray-400 text-center pb-1">
              <div></div>
              {hours.map((h) => (
                <div key={h}>{h}:00</div>
              ))}
            </div>

            {/* Weekday rows */}
            {weekdays.map((dayName, dayIdx) => (
              <div key={dayIdx} className="grid grid-cols-11 gap-1 items-center">
                <span className="text-xs font-semibold text-gray-700 text-right pr-2">
                  {dayName}
                </span>
                {hours.map((h) => {
                  const count = heatmapMap.get(`${dayIdx}_${h}`) || 0
                  return (
                    <div
                      key={h}
                      title={`${dayName} at ${h}:00 — ${count} booking(s)`}
                      className={`h-8 rounded-lg flex items-center justify-center text-xs font-bold transition ${
                        count === 0
                          ? 'bg-gray-100/60 text-gray-300'
                          : count === 1
                          ? 'bg-indigo-100 text-indigo-800'
                          : count === 2
                          ? 'bg-indigo-300 text-indigo-900'
                          : 'bg-indigo-600 text-white shadow-xs'
                      }`}
                    >
                      {count > 0 ? count : ''}
                    </div>
                  )
                })}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
