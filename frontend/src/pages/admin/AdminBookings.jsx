// Why: Comprehensive admin bookings management table with filters and proxy actions:
// - Book on behalf of a customer (POST /admin/bookings)
// - Cancel booking as administrator with reason (POST /admin/bookings/{id}/cancel)

import React, { useState, useEffect } from 'react'
import {
  PlusCircle,
  AlertTriangle,
  XCircle,
} from 'lucide-react'
import api from '../../api/client'
import { useToast } from '../../context/ToastContext'

export default function AdminBookings() {
  const [bookings, setBookings] = useState([])
  const [stylists, setStylists] = useState([])
  const [services, setServices] = useState([])
  const [loading, setLoading] = useState(true)

  // Filters
  const [statusFilter, setStatusFilter] = useState('')
  const [stylistFilter, setStylistFilter] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  // Proxy Booking Modal State
  const [isProxyModalOpen, setIsProxyModalOpen] = useState(false)
  const [proxyForm, setProxyForm] = useState({
    customerId: '',
    serviceId: '',
    stylistId: '',
    date: new Date().toISOString().split('T')[0],
    time: '10:00',
  })
  const [proxySubmitting, setProxySubmitting] = useState(false)

  // Admin Cancel Modal State
  const [cancelTarget, setCancelTarget] = useState(null)
  const [cancelReason, setCancelReason] = useState('')
  const [cancelSubmitting, setCancelSubmitting] = useState(false)

  const { success, error } = useToast()

  const fetchBookings = async () => {
    setLoading(true)
    try {
      const params = {}
      if (statusFilter) params.status = statusFilter
      if (stylistFilter) params.stylist_id = stylistFilter
      if (fromDate) params.from_date = fromDate
      if (toDate) params.to_date = toDate

      const [bookResp, stylResp, servResp] = await Promise.all([
        api.get('/admin/bookings', { params }),
        api.get('/stylists'),
        api.get('/services'),
      ])
      setBookings(bookResp.data || [])
      setStylists(stylResp.data || [])
      setServices(servResp.data || [])

      if (servResp.data?.length > 0 && !proxyForm.serviceId) {
        setProxyForm((f) => ({ ...f, serviceId: servResp.data[0].id }))
      }
      if (stylResp.data?.length > 0 && !proxyForm.stylistId) {
        setProxyForm((f) => ({ ...f, stylistId: stylResp.data[0].id }))
      }
    } catch (err) {
      console.error('Failed to load admin bookings:', err)
      error('Could not load salon bookings list.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBookings()
  }, [statusFilter, stylistFilter, fromDate, toDate])

  // Submit Proxy Booking
  const handleProxyBooking = async (e) => {
    e.preventDefault()
    if (!proxyForm.customerId || !proxyForm.serviceId || !proxyForm.stylistId || !proxyForm.date || !proxyForm.time) {
      error('Please complete all proxy booking fields')
      return
    }

    setProxySubmitting(true)
    try {
      const start_ts = `${proxyForm.date}T${proxyForm.time}:00Z`
      await api.post('/admin/bookings', {
        customer_id: Number(proxyForm.customerId),
        service_id: Number(proxyForm.serviceId),
        stylist_id: Number(proxyForm.stylistId),
        start_ts,
      })
      success('Proxy booking created successfully!')
      setIsProxyModalOpen(false)
      fetchBookings()
    } catch (err) {
      console.error('Proxy booking failed:', err)
      const detail = err.response?.data?.detail || 'Proxy booking failed. Slot may be taken.'
      error(detail)
    } finally {
      setProxySubmitting(false)
    }
  }

  // Submit Admin Cancel
  const handleAdminCancel = async () => {
    if (!cancelTarget) return
    setCancelSubmitting(true)
    try {
      await api.post(`/admin/bookings/${cancelTarget.id}/cancel`, {
        reason: cancelReason || 'Administrative cancellation',
      })
      success('Booking cancelled by administrator. Waitlist notified.')
      setCancelTarget(null)
      setCancelReason('')
      fetchBookings()
    } catch (err) {
      console.error('Admin cancel failed:', err)
      const detail = err.response?.data?.detail || 'Failed to cancel booking.'
      error(detail)
    } finally {
      setCancelSubmitting(false)
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Top action row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Bookings Ledger</h2>
          <p className="text-xs text-gray-500 mt-0.5">Filter, inspect, and perform administrative proxy actions.</p>
        </div>

        <button
          onClick={() => setIsProxyModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Book on Behalf of Client</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-xs grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
        <div>
          <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
            Status
          </label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
          >
            <option value="">All Statuses</option>
            <option value="confirmed">Confirmed</option>
            <option value="cancelled">Cancelled</option>
            <option value="completed">Completed</option>
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
            Stylist
          </label>
          <select
            value={stylistFilter}
            onChange={(e) => setStylistFilter(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
          >
            <option value="">All Stylists</option>
            {stylists.map((st) => (
              <option key={st.id} value={st.id}>
                {st.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
            From Date
          </label>
          <input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
          />
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
            To Date
          </label>
          <input
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
          />
        </div>
      </div>

      {/* Bookings Table */}
      {loading ? (
        <div className="py-20 text-center">
          <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-xs text-gray-500">Loading ledger records...</p>
        </div>
      ) : bookings.length === 0 ? (
        <div className="bg-white p-12 rounded-3xl border border-gray-100 text-center text-xs text-gray-500">
          No bookings matching your active filters.
        </div>
      ) : (
        <div className="bg-white rounded-3xl border border-gray-100 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50/80 text-gray-500 font-semibold border-b border-gray-100">
                <tr>
                  <th className="py-3.5 px-4">ID</th>
                  <th className="py-3.5 px-4">Client</th>
                  <th className="py-3.5 px-4">Service</th>
                  <th className="py-3.5 px-4">Stylist</th>
                  <th className="py-3.5 px-4">Date & Time</th>
                  <th className="py-3.5 px-4">Price</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-gray-700">
                {bookings.map((b) => (
                  <tr key={b.id} className="hover:bg-gray-50/60 transition">
                    <td className="py-3.5 px-4 font-mono font-semibold text-gray-900">#{b.id}</td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-gray-900">{b.customer?.name}</div>
                      <div className="text-[10px] text-gray-400">{b.customer?.email}</div>
                    </td>
                    <td className="py-3.5 px-4 font-medium">{b.service?.name}</td>
                    <td className="py-3.5 px-4">{b.stylist?.name}</td>
                    <td className="py-3.5 px-4 font-medium text-indigo-700">
                      {new Date(b.start_ts).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-gray-900">${b.service?.price}</td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                          b.status === 'confirmed'
                            ? 'bg-emerald-50 text-emerald-700'
                            : b.status === 'cancelled'
                            ? 'bg-rose-50 text-rose-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {b.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {b.status === 'confirmed' && (
                        <button
                          onClick={() => setCancelTarget(b)}
                          className="text-xs text-rose-600 hover:text-rose-800 font-semibold"
                        >
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* PROXY BOOKING MODAL */}
      {isProxyModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-5 animate-in zoom-in-95">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-gray-900">Book on Behalf of Client</h3>
                <p className="text-xs text-gray-500">Admin proxy appointment scheduling.</p>
              </div>
              <button
                onClick={() => setIsProxyModalOpen(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleProxyBooking} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Customer ID
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  placeholder="e.g. 1"
                  value={proxyForm.customerId}
                  onChange={(e) => setProxyForm({ ...proxyForm, customerId: e.target.value })}
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Service</label>
                <select
                  value={proxyForm.serviceId}
                  onChange={(e) => setProxyForm({ ...proxyForm, serviceId: e.target.value })}
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                >
                  {services.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} (${s.price})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Stylist</label>
                <select
                  value={proxyForm.stylistId}
                  onChange={(e) => setProxyForm({ ...proxyForm, stylistId: e.target.value })}
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                >
                  {stylists.map((st) => (
                    <option key={st.id} value={st.id}>
                      {st.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Date</label>
                  <input
                    type="date"
                    required
                    value={proxyForm.date}
                    onChange={(e) => setProxyForm({ ...proxyForm, date: e.target.value })}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Time</label>
                  <input
                    type="time"
                    step="900"
                    required
                    value={proxyForm.time}
                    onChange={(e) => setProxyForm({ ...proxyForm, time: e.target.value })}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                  />
                </div>
              </div>

              <div className="flex gap-2 pt-2 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsProxyModalOpen(false)}
                  className="flex-1 py-2.5 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={proxySubmitting}
                  className="flex-1 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl transition flex items-center justify-center gap-1.5"
                >
                  {proxySubmitting ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <span>Create Booking</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ADMIN CANCEL MODAL */}
      {cancelTarget && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-4 animate-in zoom-in-95">
            <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div className="text-center space-y-1">
              <h3 className="text-lg font-bold text-gray-900">Cancel Booking #{cancelTarget.id}</h3>
              <p className="text-xs text-gray-500">
                Administrative overrides bypass customer lock-in windows and trigger immediate waitlist cascades.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                Cancellation Reason (Optional)
              </label>
              <input
                type="text"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="e.g. Stylist illness, emergency maintenance"
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>

            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setCancelTarget(null)}
                className="flex-1 py-2.5 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition"
              >
                Dismiss
              </button>
              <button
                onClick={handleAdminCancel}
                disabled={cancelSubmitting}
                className="flex-1 py-2.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-xl transition flex items-center justify-center gap-1.5"
              >
                {cancelSubmitting ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <span>Cancel Appointment</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
