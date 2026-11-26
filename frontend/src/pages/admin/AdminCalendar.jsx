// Why: Stylist Schedule Calendar using FullCalendar v7.
// Shows real-time appointment blocks across all salon professionals with interactive stylist filter.

import React, { useState, useEffect, useRef } from 'react'
import FullCalendar from '@fullcalendar/react'
import timeGridPlugin from '@fullcalendar/react/timegrid'
import dayGridPlugin from '@fullcalendar/react/daygrid'
import themePlugin from '@fullcalendar/react/themes/breezy'

import '@fullcalendar/react/skeleton.css'
import '@fullcalendar/react/themes/breezy/theme.css'
import '@fullcalendar/react/themes/breezy/palettes/indigo.css'
import { XCircle, Calendar as CalendarIcon, User } from 'lucide-react'
import api from '../../api/client'
import { useToast } from '../../context/ToastContext'

const STYLIST_COLORS = {
  1: { bg: '#6366f1', border: '#4f46e5', text: '#ffffff' }, // Indigo
  2: { bg: '#10b981', border: '#059669', text: '#ffffff' }, // Emerald
  3: { bg: '#8b5cf6', border: '#7c3aed', text: '#ffffff' }, // Violet
  4: { bg: '#f59e0b', border: '#d97706', text: '#ffffff' }, // Amber
}

export default function AdminCalendar() {
  const [stylists, setStylists] = useState([])
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedStylistId, setSelectedStylistId] = useState('all')
  const [selectedEvent, setSelectedEvent] = useState(null)
  const calendarRef = useRef(null)
  const { error } = useToast()

  const fetchData = async () => {
    setLoading(true)
    try {
      const [stylResp, bookResp] = await Promise.all([
        api.get('/stylists'),
        api.get('/admin/bookings'),
      ])
      setStylists(stylResp.data || [])
      setBookings(bookResp.data || [])
    } catch (err) {
      console.error('Failed to load calendar data:', err)
      error('Could not load stylist calendar schedules.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // Filter bookings by selected stylist if not 'all'
  const filteredBookings = selectedStylistId === 'all'
    ? bookings
    : bookings.filter((b) => String(b.stylist_id) === String(selectedStylistId))

  // Map bookings to FullCalendar events
  const events = filteredBookings.map((b) => {
    const isCancelled = b.status === 'cancelled'
    const isCompleted = b.status === 'completed'
    const stylistStyle = STYLIST_COLORS[b.stylist_id] || { bg: '#6366f1', border: '#4f46e5', text: '#ffffff' }

    return {
      id: String(b.id),
      title: `${b.service_name || 'Service'} (${b.stylist_name || 'Stylist'})`,
      start: b.start_ts,
      end: b.end_ts,
      backgroundColor: isCancelled ? '#fda4af' : isCompleted ? '#94a3b8' : stylistStyle.bg,
      borderColor: isCancelled ? '#f43f5e' : isCompleted ? '#64748b' : stylistStyle.border,
      textColor: isCancelled ? '#881337' : stylistStyle.text,
      extendedProps: {
        booking: b,
      },
    }
  })

  const handleEventClick = (info) => {
    setSelectedEvent(info.event.extendedProps.booking)
  }

  return (
    <div className="space-y-6 animate-in fade-in pb-12">
      {/* Header and Filter Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-3xl border border-gray-100 shadow-xs">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <CalendarIcon className="w-5 h-5 text-indigo-600" />
            <span>Stylist Schedule Calendar</span>
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Real-time appointment schedule, booking slots, and professional availability.
          </p>
        </div>

        {/* Stylist Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 bg-gray-50 p-1.5 rounded-2xl border border-gray-200/80">
          <button
            type="button"
            onClick={() => setSelectedStylistId('all')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer ${
              selectedStylistId === 'all'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200/60'
            }`}
          >
            All Stylists ({bookings.length})
          </button>
          {stylists.map((st) => (
            <button
              key={st.id}
              type="button"
              onClick={() => setSelectedStylistId(String(st.id))}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer ${
                selectedStylistId === String(st.id)
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200/60'
              }`}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: STYLIST_COLORS[st.id]?.bg || '#6366f1' }}
              />
              <span>{st.name}</span>
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="py-24 text-center bg-white rounded-3xl border border-gray-100">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-xs text-gray-500">Loading stylist schedules...</p>
        </div>
      ) : (
        <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm overflow-hidden">
          <FullCalendar
            ref={calendarRef}
            plugins={[themePlugin, timeGridPlugin, dayGridPlugin]}
            themeSystem="breezy"
            initialView="timeGridDay"
            events={events}
            eventClick={handleEventClick}
            headerToolbar={{
              left: 'prev,next today',
              center: 'title',
              right: 'timeGridDay,timeGridWeek,dayGridMonth',
            }}
            slotMinTime="08:00:00"
            slotMaxTime="20:00:00"
            slotDuration="00:15:00"
            slotLabelInterval="01:00:00"
            allDaySlot={false}
            nowIndicator={true}
            height="auto"
          />
        </div>
      )}

      {/* EVENT DETAILS MODAL */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-4 animate-in zoom-in-95">
            <div className="flex items-center justify-between">
              <span
                className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full ${
                  selectedEvent.status === 'confirmed'
                    ? 'bg-emerald-50 text-emerald-700'
                    : selectedEvent.status === 'cancelled'
                    ? 'bg-rose-50 text-rose-700'
                    : 'bg-gray-100 text-gray-700'
                }`}
              >
                {selectedEvent.status}
              </span>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div>
              <h3 className="text-lg font-bold text-gray-900">
                {selectedEvent.service_name || `Service #${selectedEvent.service_id}`}
              </h3>
              <p className="text-xs text-indigo-700 font-medium">Booking #{selectedEvent.id}</p>
            </div>

            <div className="p-4 bg-gray-50 rounded-2xl text-xs space-y-2 border border-gray-100">
              <div className="flex justify-between">
                <span className="text-gray-500">Customer:</span>
                <span className="font-bold text-gray-900">
                  {selectedEvent.user_name || selectedEvent.customer?.name} ({selectedEvent.user_email || selectedEvent.customer?.email})
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Stylist:</span>
                <span className="font-bold text-gray-900">{selectedEvent.stylist_name || selectedEvent.stylist?.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Scheduled Time:</span>
                <span className="font-bold text-gray-900">
                  {new Date(selectedEvent.start_ts).toLocaleString([], {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}{' '}
                  &bull; {new Date(selectedEvent.end_ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Duration & Exclusivity:</span>
                <span className="font-semibold text-emerald-700">1-on-1 Dedicated (Conflict-Free)</span>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-5 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold rounded-xl transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
