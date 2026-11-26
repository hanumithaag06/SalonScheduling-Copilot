// Why: Customer bookings management page.
// Allows viewing upcoming and past appointments, cancellation with 2-hour window alert,
// and slot rescheduling modal.

import React, { useState, useEffect } from 'react'
import { Calendar, Scissors, AlertTriangle, XCircle } from 'lucide-react'
import api from '../api/client'
import { useToast } from '../context/ToastContext'

export default function MyBookings() {
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('all')
  const { success, error } = useToast()

  // Reschedule Modal State
  const [rescheduleBooking, setRescheduleBooking] = useState(null)
  const [newDate, setNewDate] = useState('')
  const [availableSlots, setAvailableSlots] = useState([])
  const [selectedSlotTime, setSelectedSlotTime] = useState('')
  const [rescheduleLoading, setRescheduleLoading] = useState(false)
  const [slotsLoading, setSlotsLoading] = useState(false)

  // Cancel Confirmation Modal State
  const [cancelTarget, setCancelTarget] = useState(null)
  const [cancelLoading, setCancelLoading] = useState(false)

  const fetchBookings = async () => {
    setLoading(true)
    try {
      const params = {}
      if (statusFilter !== 'all') params.status = statusFilter
      const resp = await api.get('/bookings/me', { params })
      setBookings(resp.data || [])
    } catch (err) {
      console.error('Failed to load bookings:', err)
      error('Could not load your appointments.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBookings()
  }, [statusFilter])

  // Handle Cancel
  const handleCancelBooking = async () => {
    if (!cancelTarget) return
    setCancelLoading(true)
    try {
      await api.post(`/bookings/${cancelTarget.id}/cancel`)
      success('Appointment cancelled. Eligible waitlisted clients will be notified.')
      setCancelTarget(null)
      fetchBookings()
    } catch (err) {
      console.error('Cancellation failed:', err)
      const detail = err.response?.data?.detail || 'Cancellation failed. Must be at least 2 hours before appointment.'
      error(detail)
    } finally {
      setCancelLoading(false)
    }
  }

  // Load slots when reschedule date changes
  const handleDateChangeForReschedule = async (dateVal) => {
    setNewDate(dateVal)
    setSelectedSlotTime('')
    if (!rescheduleBooking || !dateVal) return
    setSlotsLoading(true)
    try {
      const resp = await api.get('/slots', {
        params: {
          service_id: rescheduleBooking.service_id,
          stylist_id: rescheduleBooking.stylist_id,
          date: dateVal,
        },
      })
      setAvailableSlots(resp.data || [])
    } catch (err) {
      console.error('Failed to load reschedule slots:', err)
      error('Could not load slots for this date.')
    } finally {
      setSlotsLoading(false)
    }
  }

  // Submit Reschedule
  const handleConfirmReschedule = async () => {
    if (!rescheduleBooking || !selectedSlotTime) return
    setRescheduleLoading(true)
    try {
      await api.put(`/bookings/${rescheduleBooking.id}`, {
        new_start_ts: selectedSlotTime,
      })
      success('Appointment rescheduled successfully!')
      setRescheduleBooking(null)
      fetchBookings()
    } catch (err) {
      console.error('Reschedule failed:', err)
      const detail = err.response?.data?.detail || 'Reschedule failed. Please choose another slot.'
      error(detail)
    } finally {
      setRescheduleLoading(false)
    }
  }

  const isMoreThanTwoHoursAway = (startTs) => {
    const diffHours = (new Date(startTs).getTime() - Date.now()) / (1000 * 60 * 60)
    return diffHours >= 2.0
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight">My Bookings</h1>
          <p className="text-xs text-gray-500 mt-1">Manage your upcoming visits and appointment history.</p>
        </div>

        {/* Status Filters */}
        <div className="flex bg-gray-100 p-1.5 rounded-2xl gap-1">
          {['all', 'confirmed', 'completed', 'cancelled'].map((tab) => (
            <button
              key={tab}
              onClick={() => setStatusFilter(tab)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold capitalize transition ${
                statusFilter === tab
                  ? 'bg-white text-indigo-700 shadow-xs'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="py-20 flex justify-center items-center">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : bookings.length === 0 ? (
        <div className="bg-white p-12 rounded-3xl border border-gray-100 text-center space-y-3">
          <Calendar className="w-10 h-10 text-gray-300 mx-auto" />
          <h3 className="text-base font-bold text-gray-900">No appointments found</h3>
          <p className="text-xs text-gray-500">
            {statusFilter === 'all'
              ? "You haven't booked any salon appointments yet."
              : `No appointments with status '${statusFilter}'.`}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {bookings.map((b) => {
            const canModify = b.status === 'confirmed' && isMoreThanTwoHoursAway(b.start_ts)

            return (
              <div
                key={b.id}
                className="bg-white p-6 rounded-3xl border border-gray-100 shadow-xs hover:shadow-md transition flex flex-col sm:flex-row sm:items-center justify-between gap-6"
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full ${
                        b.status === 'confirmed'
                          ? 'bg-emerald-50 text-emerald-700'
                          : b.status === 'cancelled'
                          ? 'bg-rose-50 text-rose-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {b.status}
                    </span>
                    <span className="text-xs font-mono text-gray-400">#{b.id}</span>
                  </div>

                  <h3 className="text-lg font-bold text-gray-900">
                    {b.service?.name || `Service #${b.service_id}`}
                  </h3>

                  <div className="flex flex-wrap items-center gap-4 text-xs text-gray-600">
                    <div className="flex items-center gap-1.5 font-medium text-indigo-700">
                      <Calendar className="w-4 h-4" />
                      <span>
                        {new Date(b.start_ts).toLocaleString([], {
                          weekday: 'short',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Scissors className="w-4 h-4 text-gray-400" />
                      <span>Stylist: {b.stylist?.name || `Stylist #${b.stylist_id}`}</span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                {b.status === 'confirmed' && (
                  <div className="flex items-center gap-2 self-start sm:self-center">
                    {canModify ? (
                      <>
                        <button
                          onClick={() => {
                            setRescheduleBooking(b)
                            setNewDate(b.start_ts.split('T')[0])
                            handleDateChangeForReschedule(b.start_ts.split('T')[0])
                          }}
                          className="px-3.5 py-2 text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-xl transition"
                        >
                          Reschedule
                        </button>
                        <button
                          onClick={() => setCancelTarget(b)}
                          className="px-3.5 py-2 text-xs font-semibold text-rose-600 bg-rose-50 hover:bg-rose-100 rounded-xl transition"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <span className="text-[11px] text-gray-400 italic">
                        Within 2-hr lock window
                      </span>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* CANCEL CONFIRMATION MODAL */}
      {cancelTarget && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-4 animate-in zoom-in-95">
            <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div className="text-center space-y-1">
              <h3 className="text-lg font-bold text-gray-900">Cancel Appointment?</h3>
              <p className="text-xs text-gray-500">
                Are you sure you want to cancel booking #{cancelTarget.id}?
              </p>
            </div>
            <div className="p-3 bg-gray-50 rounded-xl text-xs text-gray-600 space-y-1">
              <p>
                <strong>Service:</strong> {cancelTarget.service?.name}
              </p>
              <p>
                <strong>Time:</strong>{' '}
                {new Date(cancelTarget.start_ts).toLocaleString([], {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setCancelTarget(null)}
                className="flex-1 py-2.5 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition"
              >
                Keep Appointment
              </button>
              <button
                onClick={handleCancelBooking}
                disabled={cancelLoading}
                className="flex-1 py-2.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-xl transition flex items-center justify-center gap-1.5"
              >
                {cancelLoading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <span>Yes, Cancel</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RESCHEDULE MODAL */}
      {rescheduleBooking && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-2xl space-y-5 animate-in zoom-in-95">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-gray-900">Reschedule Appointment</h3>
                <p className="text-xs text-gray-500">Choose a new date and open slot.</p>
              </div>
              <button
                onClick={() => setRescheduleBooking(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1.5">
                  New Appointment Date
                </label>
                <input
                  type="date"
                  min={new Date().toISOString().split('T')[0]}
                  value={newDate}
                  onChange={(e) => handleDateChangeForReschedule(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1.5">
                  Select New Open Slot
                </label>
                {slotsLoading ? (
                  <div className="py-8 text-center text-xs text-gray-500">
                    <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Calculating openings...
                  </div>
                ) : availableSlots.length === 0 ? (
                  <p className="p-4 bg-gray-50 rounded-xl text-xs text-gray-500 text-center">
                    No openings found for this date.
                  </p>
                ) : (
                  <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-48 overflow-y-auto p-1">
                    {availableSlots.map((s, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setSelectedSlotTime(s.start_ts || s.start_time)}
                        className={`p-2 rounded-xl border text-xs font-bold transition ${
                          selectedSlotTime === (s.start_ts || s.start_time)
                            ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                            : 'border-gray-200 hover:border-indigo-300'
                        }`}
                      >
                        {new Date(s.start_ts || s.start_time).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-2 pt-2 border-t border-gray-100">
              <button
                onClick={() => setRescheduleBooking(null)}
                className="flex-1 py-2.5 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition"
              >
                Dismiss
              </button>
              <button
                onClick={handleConfirmReschedule}
                disabled={!selectedSlotTime || rescheduleLoading}
                className="flex-1 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl transition flex items-center justify-center gap-1.5"
              >
                {rescheduleLoading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <span>Confirm New Time</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
