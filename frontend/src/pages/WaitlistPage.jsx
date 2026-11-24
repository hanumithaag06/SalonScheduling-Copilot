// Why: Waitlist management page.
// Allows customers to join waitlists for fully-booked days and claim 15-minute slot offers.

import React, { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Clock, Calendar, Sparkles, CheckCircle2 } from 'lucide-react'
import api from '../api/client'
import { useToast } from '../context/ToastContext'

export default function WaitlistPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { success, error } = useToast()

  const prefilled = location.state || {}

  const [services, setServices] = useState([])
  const [stylists, setStylists] = useState([])
  const [waitlistEntries, setWaitlistEntries] = useState([])
  const [loading, setLoading] = useState(true)

  // Join form state
  const [serviceId, setServiceId] = useState(prefilled.serviceId || '')
  const [stylistId, setStylistId] = useState(prefilled.stylistId || '')
  const [targetDate, setTargetDate] = useState(
    prefilled.date || new Date(Date.now() + 86400000).toISOString().split('T')[0]
  )
  const [timePref, setTimePref] = useState(prefilled.timePref || 'any')
  const [submitting, setSubmitting] = useState(false)

  // Claim loading state
  const [claimLoadingId, setClaimLoadingId] = useState(null)

  const fetchData = async () => {
    try {
      const [servResp, stylResp, wlResp] = await Promise.all([
        api.get('/services'),
        api.get('/stylists'),
        api.get('/waitlist/me'),
      ])
      setServices(servResp.data || [])
      setStylists(stylResp.data || [])
      setWaitlistEntries(wlResp.data || [])
      if (!serviceId && servResp.data?.length > 0) {
        setServiceId(servResp.data[0].id)
      }
    } catch (err) {
      console.error('Failed to load waitlist data:', err)
      error('Could not load waitlist status.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // Join Waitlist
  const handleJoin = async (e) => {
    e.preventDefault()
    if (!serviceId || !targetDate) {
      error('Please select both service and date')
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        service_id: Number(serviceId),
        date: targetDate,
        time_pref: timePref,
      }
      if (stylistId) payload.stylist_id = Number(stylistId)

      await api.post('/waitlist', payload)
      success('Joined waitlist! You will be offered a slot if an opening appears.')
      fetchData()
    } catch (err) {
      console.error('Failed to join waitlist:', err)
      const detail = err.response?.data?.detail || 'Could not join waitlist. You may already be on the queue.'
      error(detail)
    } finally {
      setSubmitting(false)
    }
  }

  // Claim Offered Slot
  const handleClaim = async (entryId) => {
    setClaimLoadingId(entryId)
    try {
      await api.post(`/waitlist/${entryId}/claim`)
      success('Slot claimed successfully! Appointment has been scheduled.')
      navigate('/my-bookings')
    } catch (err) {
      console.error('Failed to claim slot:', err)
      const detail = err.response?.data?.detail || 'Offer expired or unavailable.'
      error(detail)
      fetchData()
    } finally {
      setClaimLoadingId(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-12">
      {/* Header */}
      <div>
        <span className="text-xs font-semibold text-violet-600 uppercase tracking-widest bg-violet-50 px-2.5 py-1 rounded-full">
          First-Come, First-Served Queue
        </span>
        <h1 className="text-3xl font-black text-gray-900 mt-2 tracking-tight">Appointment Waitlist</h1>
        <p className="text-xs text-gray-500 mt-1">
          When an appointment is cancelled, Stylify automatically offers the slot to the next client in line with a 15-minute claim window.
        </p>
      </div>

      {/* Join Waitlist Form */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border border-gray-100 shadow-xl space-y-6">
        <h2 className="text-lg font-bold text-gray-900">Queue for a Future Slot</h2>

        <form onSubmit={handleJoin} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1.5">
              Service
            </label>
            <select
              value={serviceId}
              onChange={(e) => setServiceId(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
            >
              {services.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} (${s.price})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1.5">
              Target Date
            </label>
            <input
              type="date"
              min={new Date().toISOString().split('T')[0]}
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1.5">
              Preferred Stylist (Optional)
            </label>
            <select
              value={stylistId}
              onChange={(e) => setStylistId(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
            >
              <option value="">Any Available Stylist</option>
              {stylists.map((st) => (
                <option key={st.id} value={st.id}>
                  {st.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1.5">
              Time Preference
            </label>
            <select
              value={timePref}
              onChange={(e) => setTimePref(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
            >
              <option value="any">Any Time</option>
              <option value="morning">Morning (9am - 12pm)</option>
              <option value="afternoon">Afternoon (12pm - 5pm)</option>
              <option value="evening">Evening (5pm - 8pm)</option>
            </select>
          </div>

          <div className="sm:col-span-2 pt-2">
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white font-semibold rounded-xl shadow-md transition flex items-center justify-center gap-2 text-sm"
            >
              {submitting ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Join Waitlist Queue</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* My Waitlist Entries */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-gray-900">My Waitlist Status</h2>

        {loading ? (
          <div className="py-12 flex justify-center">
            <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : waitlistEntries.length === 0 ? (
          <div className="bg-white p-8 rounded-3xl border border-gray-100 text-center space-y-2">
            <Clock className="w-8 h-8 text-gray-300 mx-auto" />
            <p className="text-sm font-semibold text-gray-900">No active waitlist requests</p>
            <p className="text-xs text-gray-500">Join the queue above if a date has no available slots.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {waitlistEntries.map((w) => {
              const isOffered = w.status === 'offered'
              const service = services.find((s) => s.id === w.service_id)
              const stylist = stylists.find((s) => s.id === w.stylist_id)

              return (
                <div
                  key={w.id}
                  className={`p-6 rounded-3xl border transition flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                    isOffered
                      ? 'bg-amber-50 border-amber-300 shadow-md ring-2 ring-amber-400/40'
                      : 'bg-white border-gray-100 shadow-xs'
                  }`}
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full ${
                          isOffered
                            ? 'bg-amber-500 text-white animate-pulse'
                            : w.status === 'claimed'
                            ? 'bg-emerald-50 text-emerald-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {w.status}
                      </span>
                      <span className="text-xs font-mono text-gray-400">Entry #{w.id}</span>
                    </div>

                    <h3 className="font-bold text-base text-gray-900">
                      {service?.name || `Service #${w.service_id}`}
                    </h3>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
                      <div className="flex items-center gap-1 font-medium text-indigo-700">
                        <Calendar className="w-3.5 h-3.5" />
                        <span>Date: {w.date}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        <span>Preference: {w.time_pref}</span>
                      </div>
                      {stylist && <span>Stylist: {stylist.name}</span>}
                    </div>

                    {isOffered && w.offered_slot && (
                      <div className="mt-2 text-xs font-bold text-amber-900 bg-white/70 p-2 rounded-xl inline-block">
                        Opening Offered:{' '}
                        {new Date(w.offered_slot).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                        {w.offer_expires_at && (
                          <span className="ml-2 font-normal text-amber-700">
                            (Expires at {new Date(w.offer_expires_at).toLocaleTimeString()})
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {isOffered && (
                    <button
                      onClick={() => handleClaim(w.id)}
                      disabled={claimLoadingId === w.id}
                      className="px-5 py-2.5 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-xl shadow-md transition flex items-center justify-center gap-1.5 self-start sm:self-center"
                    >
                      {claimLoadingId === w.id ? (
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      ) : (
                        <>
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Claim Slot (15-min Window)</span>
                        </>
                      )}
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
