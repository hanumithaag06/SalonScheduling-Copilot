// Why: Stylist Schedule Calendar using FullCalendar with a column per stylist.
// Shows real-time appointment blocks across all salon professionals.

import React, { useState, useEffect, useRef } from 'react'
import FullCalendar from '@fullcalendar/react'
import resourceTimeGridPlugin from '@fullcalendar/resource-timegrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import dayGridPlugin from '@fullcalendar/daygrid'
import { XCircle } from 'lucide-react'
import api from '../../api/client'
import { useToast } from '../../context/ToastContext'

export default function AdminCalendar() {
  const [stylists, setStylists] = useState([])
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
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

  // Map stylists to FullCalendar resources (columns)
  const resources = stylists.map((st) => ({
    id: String(st.id),
    title: st.name,
    specialization: st.specialization,
  }))

  // Map bookings to FullCalendar events assigned to each stylist resource column
  const events = bookings.map((b) => {
    const isCancelled = b.status === 'cancelled'
    const isCompleted = b.status === 'completed'

    return {
      id: String(b.id),
      resourceId: String(b.stylist_id),
      title: `${b.service?.name || 'Service'} — ${b.customer?.name || 'Client'}`,
      start: b.start_ts,
      end: b.end_ts,
      backgroundColor: isCancelled ? '#fda4af' : isCompleted ? '#94a3b8' : '#6366f1',
      borderColor: isCancelled ? '#f43f5e' : isCompleted ? '#64748b' : '#4f46e5',
      textColor: isCancelled ? '#881337' : '#ffffff',
      extendedProps: {
        booking: b,
      },
    }
  })

  const handleEventClick = (info) => {
    setSelectedEvent(info.event.extendedProps.booking)
  }

  return (
    <div className="space-y-6 animate-in fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Stylist Daily Schedules</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Resource timeline view displaying appointment allocations per stylist.
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs font-medium">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-indigo-600"></span>
            <span className="text-gray-600">Confirmed</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-rose-400"></span>
            <span className="text-gray-600">Cancelled</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-slate-400"></span>
            <span className="text-gray-600">Completed</span>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="py-24 text-center">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-xs text-gray-500">Loading stylist columns...</p>
        </div>
      ) : (
        <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm overflow-hidden">
          <FullCalendar
            ref={calendarRef}
            plugins={[resourceTimeGridPlugin, timeGridPlugin, dayGridPlugin]}
            initialView="resourceTimeGridDay"
            resources={resources}
            events={events}
            eventClick={handleEventClick}
            headerToolbar={{
              left: 'prev,next today',
              center: 'title',
              right: 'resourceTimeGridDay,timeGridWeek,dayGridMonth',
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
                {selectedEvent.service?.name || `Service #${selectedEvent.service_id}`}
              </h3>
              <p className="text-xs text-indigo-700 font-medium">Booking #{selectedEvent.id}</p>
            </div>

            <div className="p-4 bg-gray-50 rounded-2xl text-xs space-y-2 border border-gray-100">
              <div className="flex justify-between">
                <span className="text-gray-500">Customer:</span>
                <span className="font-bold text-gray-900">
                  {selectedEvent.customer?.name} ({selectedEvent.customer?.email})
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Stylist:</span>
                <span className="font-bold text-gray-900">{selectedEvent.stylist?.name}</span>
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
                  -{' '}
                  {new Date(selectedEvent.end_ts).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Service Price:</span>
                <span className="font-bold text-emerald-700">${selectedEvent.service?.price}</span>
              </div>
            </div>

            <button
              onClick={() => setSelectedEvent(null)}
              className="w-full py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold text-xs rounded-xl transition"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
