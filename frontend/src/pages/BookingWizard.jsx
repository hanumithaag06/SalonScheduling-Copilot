// Why: Complete 5-step booking wizard with service/stylist selection, slot calculation,
// explainable recommendations, 5-minute pre-booking holds, and final confirmation.

import React, { useState, useEffect } from 'react'
import { useLocation, useNavigate, Link } from 'react-router-dom'
import {
  Clock,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  ArrowLeft,
  ShieldCheck,
} from 'lucide-react'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import HoldCountdown from '../components/HoldCountdown'

export default function BookingWizard() {
  const location = useLocation()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const { success, error, info } = useToast()

  // Pre-filled state from Assistant or Services page
  const initialState = location.state || {}

  // Wizard Steps: 1: Service/Stylist, 2: Date & Preference, 3: Slots & Recommendations, 4: Hold & Review, 5: Confirmed
  const [step, setStep] = useState(initialState.preselectedSlot ? 3 : 1)

  // Catalogs
  const [services, setServices] = useState([])
  const [stylists, setStylists] = useState([])
  const [loadingCatalogs, setLoadingCatalogs] = useState(true)

  // Selections
  const [selectedServiceId, setSelectedServiceId] = useState(initialState.serviceId || '')
  const [selectedStylistId, setSelectedStylistId] = useState(initialState.stylistId || '')
  const [selectedDate, setSelectedDate] = useState(
    initialState.date || new Date(Date.now() + 86400000).toISOString().split('T')[0]
  )
  const [timePref, setTimePref] = useState('any')
  const [maxPrice, setMaxPrice] = useState('')

  // Slot Calculation & Recommendations
  const [loadingSlots, setLoadingSlots] = useState(false)
  const [availableSlots, setAvailableSlots] = useState([])
  const [recommendedSlots, setRecommendedSlots] = useState([])
  const [selectedSlot, setSelectedSlot] = useState(null)

  // Active Hold
  const [activeHold, setActiveHold] = useState(null)
  const [holdLoading, setHoldLoading] = useState(false)

  // Confirmed Booking Result
  const [confirmedBooking, setConfirmedBooking] = useState(null)
  const [confirmLoading, setConfirmLoading] = useState(false)

  // Load Services & Stylists
  useEffect(() => {
    async function loadData() {
      try {
        const [servResp, stylResp] = await Promise.all([
          api.get('/services'),
          api.get('/stylists'),
        ])
        setServices(servResp.data || [])
        setStylists(stylResp.data || [])
        if (!selectedServiceId && servResp.data?.length > 0) {
          setSelectedServiceId(servResp.data[0].id)
        }
      } catch (err) {
        console.error('Failed to load catalogs:', err)
        error('Could not load service offerings.')
      } finally {
        setLoadingCatalogs(false)
      }
    }
    loadData()
  }, [])

  // Fetch Slots & Recommendations when moving to Step 3
  const fetchSlotsAndRecommendations = async () => {
    if (!selectedServiceId || !selectedDate) return
    setLoadingSlots(true)
    setAvailableSlots([])
    setRecommendedSlots([])

    try {
      // 1. Fetch available slots from pure slot engine
      const params = {
        service_id: selectedServiceId,
        date: selectedDate,
      }
      if (selectedStylistId) params.stylist_id = selectedStylistId
      if (maxPrice) params.max_price = maxPrice

      const slotsResp = await api.get('/slots', { params })
      setAvailableSlots(slotsResp.data || [])

      // 2. Fetch explainable recommendations from pure recommender
      const recParams = {
        service_id: selectedServiceId,
        date: selectedDate,
      }
      if (timePref && timePref !== 'any') recParams.preferred_time = timePref
      if (maxPrice) recParams.max_price = maxPrice

      const recResp = await api.get('/recommend', { params: recParams })
      setRecommendedSlots(recResp.data || [])
    } catch (err) {
      console.error('Failed to load slots:', err)
      error('Could not calculate available slots for this date.')
    } finally {
      setLoadingSlots(false)
    }
  }

  // Trigger slot fetch whenever moving to step 3
  useEffect(() => {
    if (step === 3 && selectedServiceId && selectedDate) {
      fetchSlotsAndRecommendations()
    }
  }, [step, selectedServiceId, selectedStylistId, selectedDate, timePref, maxPrice])

  // Create a 5-minute Hold when selecting a slot
  const handleSelectSlotForHold = async (slot) => {
    if (!isAuthenticated) {
      info('Please sign in or create an account to reserve this slot.')
      navigate('/login', { state: { from: location } })
      return
    }

    setHoldLoading(true)
    try {
      // Release existing hold if user changes slot
      if (activeHold) {
        try {
          await api.delete(`/holds/${activeHold.id}`)
        } catch {}
      }

      const resp = await api.post('/holds', {
        stylist_id: slot.stylist_id,
        service_id: Number(selectedServiceId),
        slot_time: slot.start_time,
      })

      setActiveHold(resp.data)
      setSelectedSlot(slot)
      setStep(4) // Move to Hold & Review step
      success('Slot reserved for 5 minutes!')
    } catch (err) {
      console.error('Failed to create hold:', err)
      const detail = err.response?.data?.detail || 'This slot is no longer available.'
      error(detail)
      fetchSlotsAndRecommendations()
    } finally {
      setHoldLoading(false)
    }
  }

  // Release Hold
  const handleReleaseHold = async () => {
    if (activeHold) {
      try {
        await api.delete(`/holds/${activeHold.id}`)
        info('Slot hold released.')
      } catch {}
      setActiveHold(null)
      setSelectedSlot(null)
      setStep(3)
    }
  }

  // Handle Hold Expiry
  const handleHoldExpired = () => {
    setActiveHold(null)
    setSelectedSlot(null)
    error('Your slot hold has expired. Please select a new time slot.')
    setStep(3)
    fetchSlotsAndRecommendations()
  }

  // Final Booking Confirmation
  const handleConfirmBooking = async () => {
    if (!selectedSlot || !selectedServiceId) return
    setConfirmLoading(true)

    try {
      const payload = {
        service_id: Number(selectedServiceId),
        stylist_id: selectedSlot.stylist_id,
        start_ts: selectedSlot.start_time,
      }
      if (activeHold) {
        payload.hold_id = activeHold.id
      }

      const resp = await api.post('/bookings', payload)
      setConfirmedBooking(resp.data)
      setActiveHold(null)
      setStep(5)
      success('Appointment confirmed successfully!')
    } catch (err) {
      console.error('Booking failed:', err)
      const detail = err.response?.data?.detail || 'Booking failed. Slot may have been taken.'
      error(detail)
      setStep(3)
      fetchSlotsAndRecommendations()
    } finally {
      setConfirmLoading(false)
    }
  }

  const selectedService = services.find((s) => s.id === Number(selectedServiceId))
  const selectedStylist = stylists.find((s) => s.id === Number(selectedStylistId))

  if (loadingCatalogs) {
    return (
      <div className="py-20 flex justify-center items-center">
        <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Wizard Progress Stepper */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {[
            { num: 1, label: 'Service' },
            { num: 2, label: 'Date & Time' },
            { num: 3, label: 'Choose Slot' },
            { num: 4, label: 'Hold & Review' },
            { num: 5, label: 'Confirmed' },
          ].map((s, idx) => (
            <div key={s.num} className="flex-1 flex flex-col items-center relative">
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs transition-colors ${
                  step === s.num
                    ? 'bg-indigo-600 text-white ring-4 ring-indigo-100'
                    : step > s.num
                    ? 'bg-emerald-600 text-white'
                    : 'bg-gray-100 text-gray-500'
                }`}
              >
                {step > s.num ? <CheckCircle2 className="w-5 h-5" /> : s.num}
              </div>
              <span
                className={`text-[11px] font-medium mt-1.5 hidden sm:block ${
                  step === s.num ? 'text-indigo-600 font-semibold' : 'text-gray-500'
                }`}
              >
                {s.label}
              </span>
              {idx < 4 && (
                <div
                  className={`hidden sm:block absolute top-4 left-1/2 w-full h-[2px] -z-10 ${
                    step > s.num ? 'bg-emerald-600' : 'bg-gray-200'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* STEP 1: Select Service & Stylist */}
      {step === 1 && (
        <div className="bg-white p-6 sm:p-8 rounded-3xl border border-gray-100 shadow-xl space-y-6 animate-in fade-in">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Step 1: Choose Your Service</h2>
            <p className="text-xs text-gray-500 mt-1">Select the treatment and optional preferred stylist.</p>
          </div>

          <div className="space-y-4">
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700">
              Select Salon Service
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-72 overflow-y-auto p-1">
              {services.map((s) => (
                <div
                  key={s.id}
                  onClick={() => setSelectedServiceId(s.id)}
                  className={`p-4 rounded-2xl border transition cursor-pointer flex flex-col justify-between ${
                    selectedServiceId === s.id
                      ? 'border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-500/20'
                      : 'border-gray-200 hover:border-indigo-300 bg-white'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-gray-900">{s.name}</span>
                      <span className="font-extrabold text-sm text-indigo-700">${s.price}</span>
                    </div>
                    <span className="text-[11px] text-gray-500">{s.category}</span>
                  </div>
                  <div className="mt-2 text-xs text-gray-500 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{s.duration_min} mins</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-4 border-t border-gray-100">
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-2">
                Preferred Stylist (Optional)
              </label>
              <select
                value={selectedStylistId}
                onChange={(e) => setSelectedStylistId(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
              >
                <option value="">Any Available Stylist (Recommended for more slots)</option>
                {stylists.map((st) => (
                  <option key={st.id} value={st.id}>
                    {st.name} — {st.specialization}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end pt-4 border-t border-gray-100">
            <button
              onClick={() => setStep(2)}
              disabled={!selectedServiceId}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl shadow-md transition flex items-center gap-2 text-sm"
            >
              <span>Next: Select Date</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: Select Date, Time Preference & Budget */}
      {step === 2 && (
        <div className="bg-white p-6 sm:p-8 rounded-3xl border border-gray-100 shadow-xl space-y-6 animate-in fade-in">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Step 2: Date & Preferences</h2>
            <p className="text-xs text-gray-500 mt-1">When would you like to visit?</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1.5">
                Target Date
              </label>
              <input
                type="date"
                min={new Date().toISOString().split('T')[0]}
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-2">
                Preferred Time of Day
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { id: 'any', label: 'Any Time' },
                  { id: 'morning', label: 'Morning (9am-12pm)' },
                  { id: 'afternoon', label: 'Afternoon (12pm-5pm)' },
                  { id: 'evening', label: 'Evening (5pm-8pm)' },
                ].map((tp) => (
                  <button
                    key={tp.id}
                    type="button"
                    onClick={() => setTimePref(tp.id)}
                    className={`p-3 rounded-xl border text-xs font-medium transition ${
                      timePref === tp.id
                        ? 'border-indigo-600 bg-indigo-50 text-indigo-700 font-semibold'
                        : 'border-gray-200 hover:bg-gray-50 text-gray-700'
                    }`}
                  >
                    {tp.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1.5">
                Max Budget Constraint (Optional)
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-2.5 text-gray-400 font-bold">$</span>
                <input
                  type="number"
                  min="0"
                  step="5"
                  value={maxPrice}
                  onChange={(e) => setMaxPrice(e.target.value)}
                  placeholder="e.g. 80"
                  className="w-full pl-8 pr-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-between pt-4 border-t border-gray-100">
            <button
              onClick={() => setStep(1)}
              className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium text-sm flex items-center gap-1.5"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>
            <button
              onClick={() => setStep(3)}
              disabled={!selectedDate}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl shadow-md transition flex items-center gap-2 text-sm"
            >
              <span>View Available Slots</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: Slots List & Recommendations */}
      {step === 3 && (
        <div className="space-y-6 animate-in fade-in">
          {/* Header summary banner */}
          <div className="bg-indigo-50/80 p-4 rounded-2xl border border-indigo-100 flex flex-wrap items-center justify-between gap-3 text-xs text-indigo-900">
            <div>
              <strong>{selectedService?.name}</strong> (${selectedService?.price}) &bull;{' '}
              {new Date(selectedDate + 'T00:00:00').toLocaleDateString(undefined, {
                weekday: 'long',
                month: 'short',
                day: 'numeric',
              })}
              {selectedStylist && <span> &bull; with {selectedStylist.name}</span>}
            </div>
            <button
              onClick={() => setStep(2)}
              className="text-indigo-600 hover:text-indigo-800 font-semibold underline"
            >
              Change Date or Service
            </button>
          </div>

          {loadingSlots ? (
            <div className="py-16 text-center space-y-3 bg-white rounded-3xl border border-gray-100">
              <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
              <p className="text-xs text-gray-500">Calculating real-time 15-minute slot gaps...</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* TOP RECOMMENDED PICKS */}
              {recommendedSlots.length > 0 && (
                <div className="bg-gradient-to-br from-indigo-50 to-violet-50 p-6 rounded-3xl border border-indigo-100 shadow-xs space-y-4">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-indigo-600" />
                    <h3 className="font-bold text-gray-900 text-sm">
                      Top Recommended Picks for You
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {recommendedSlots.map((rec, idx) => (
                      <div
                        key={idx}
                        className="bg-white p-4 rounded-2xl border border-indigo-100 shadow-xs hover:border-indigo-500 transition flex flex-col justify-between"
                      >
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-indigo-700 text-sm">
                              {new Date(rec.start_time).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                            <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                              Score +{rec.score}
                            </span>
                          </div>
                          <p className="font-semibold text-xs text-gray-900">{rec.stylist_name}</p>
                          <p className="text-[11px] text-gray-600 leading-snug">{rec.reason}</p>
                        </div>
                        <button
                          onClick={() => handleSelectSlotForHold(rec)}
                          disabled={holdLoading}
                          className="mt-3 w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs rounded-xl shadow-xs transition"
                        >
                          Select & Reserve
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ALL AVAILABLE SLOTS */}
              <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm space-y-4">
                <h3 className="font-bold text-gray-900 text-sm">All Available Openings</h3>

                {availableSlots.length === 0 ? (
                  <div className="p-8 text-center space-y-3">
                    <AlertCircle className="w-8 h-8 text-amber-500 mx-auto" />
                    <p className="text-sm font-semibold text-gray-900">
                      No open slots available for this date and criteria.
                    </p>
                    <p className="text-xs text-gray-500 max-w-sm mx-auto">
                      All stylists are booked or outside working hours. Would you like to join the waitlist?
                    </p>
                    <button
                      onClick={() =>
                        navigate('/waitlist', {
                          state: {
                            serviceId: selectedServiceId,
                            stylistId: selectedStylistId,
                            date: selectedDate,
                            timePref,
                          },
                        })
                      }
                      className="px-5 py-2.5 bg-violet-600 hover:bg-violet-700 text-white font-semibold text-xs rounded-xl shadow-sm transition"
                    >
                      Join Waitlist for This Day
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-2.5">
                    {availableSlots.map((slot, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSelectSlotForHold(slot)}
                        disabled={holdLoading}
                        className="p-2.5 rounded-xl border border-gray-200 hover:border-indigo-600 hover:bg-indigo-50/50 text-left transition group"
                      >
                        <span className="block font-bold text-xs text-gray-900 group-hover:text-indigo-600">
                          {new Date(slot.start_time).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                        <span className="text-[10px] text-gray-500 block truncate">
                          {slot.stylist_name}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex justify-start">
                <button
                  onClick={() => setStep(2)}
                  className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium text-sm flex items-center gap-1.5"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back to Date Selection</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* STEP 4: 5-Minute Hold & Review */}
      {step === 4 && activeHold && selectedSlot && (
        <div className="bg-white p-6 sm:p-8 rounded-3xl border border-gray-100 shadow-xl space-y-6 animate-in fade-in">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Step 4: Hold & Review</h2>
            <p className="text-xs text-gray-500 mt-1">
              Your appointment slot is held exclusively for 5 minutes.
            </p>
          </div>

          {/* Active Hold Countdown Banner */}
          <HoldCountdown
            expiresAt={activeHold.expires_at}
            onExpired={handleHoldExpired}
            onRelease={handleReleaseHold}
          />

          {/* Appointment Summary Card */}
          <div className="p-6 bg-gray-50 rounded-2xl border border-gray-200/80 space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <span className="text-xs uppercase font-semibold text-gray-500 tracking-wider">
                Service
              </span>
              <span className="font-bold text-sm text-gray-900">{selectedService?.name}</span>
            </div>
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <span className="text-xs uppercase font-semibold text-gray-500 tracking-wider">
                Stylist
              </span>
              <span className="font-bold text-sm text-gray-900">{selectedSlot.stylist_name}</span>
            </div>
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <span className="text-xs uppercase font-semibold text-gray-500 tracking-wider">
                Date & Time
              </span>
              <span className="font-bold text-sm text-indigo-700">
                {new Date(selectedSlot.start_time).toLocaleString([], {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </div>
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <span className="text-xs uppercase font-semibold text-gray-500 tracking-wider">
                Duration
              </span>
              <span className="font-bold text-sm text-gray-900">{selectedService?.duration_min} minutes</span>
            </div>
            <div className="flex items-center justify-between pt-1">
              <span className="text-sm font-bold text-gray-900">Total Price</span>
              <span className="text-xl font-extrabold text-indigo-600">${selectedService?.price}</span>
            </div>
          </div>

          <div className="p-3.5 bg-blue-50/70 border border-blue-100 rounded-xl text-xs text-blue-900 flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <span>
              Free cancellation and rescheduling are allowed up to 2 hours before appointment time.
            </span>
          </div>

          <div className="flex justify-between pt-4 border-t border-gray-100">
            <button
              onClick={handleReleaseHold}
              className="px-4 py-2 text-rose-600 hover:text-rose-800 font-medium text-sm"
            >
              Cancel Reservation
            </button>
            <button
              onClick={handleConfirmBooking}
              disabled={confirmLoading}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl shadow-md transition flex items-center gap-2 text-sm"
            >
              {confirmLoading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Confirm Booking</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* STEP 5: Booking Confirmed */}
      {step === 5 && confirmedBooking && (
        <div className="bg-white p-8 rounded-3xl border border-gray-100 shadow-xl text-center space-y-6 animate-in zoom-in-95">
          <div className="w-16 h-16 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-10 h-10" />
          </div>

          <div className="space-y-1">
            <h2 className="text-2xl font-black text-gray-900">Booking Confirmed!</h2>
            <p className="text-xs text-gray-500">
              Confirmation ID: <span className="font-mono font-bold">#{confirmedBooking.id}</span>
            </p>
          </div>

          <div className="max-w-md mx-auto p-4 bg-gray-50 rounded-2xl border border-gray-100 text-left text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-500">Service:</span>
              <span className="font-bold text-gray-900">{selectedService?.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Stylist:</span>
              <span className="font-bold text-gray-900">{selectedSlot?.stylist_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Scheduled Time:</span>
              <span className="font-bold text-indigo-700">
                {new Date(confirmedBooking.start_ts).toLocaleString([], {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Status:</span>
              <span className="font-bold text-emerald-700 uppercase">{confirmedBooking.status}</span>
            </div>
          </div>

          <p className="text-xs text-gray-400">
            A confirmation notification has been sent. We look forward to seeing you!
          </p>

          <div className="flex justify-center gap-3 pt-2">
            <Link
              to="/my-bookings"
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl shadow-xs transition"
            >
              View My Bookings
            </Link>
            <button
              onClick={() => {
                setStep(1)
                setSelectedSlot(null)
                setActiveHold(null)
                setConfirmedBooking(null)
              }}
              className="px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold text-xs rounded-xl transition"
            >
              Book Another
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
