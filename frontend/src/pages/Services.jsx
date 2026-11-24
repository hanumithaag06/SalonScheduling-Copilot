// Why: Services and Stylists catalog page.
// Allows browsing salon offerings by category, inspecting stylist specializations,
// and jumping directly into the booking flow with a preselected service or stylist.

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Scissors, Clock, Award } from 'lucide-react'
import api from '../api/client'
import { useToast } from '../context/ToastContext'

export default function Services() {
  const [services, setServices] = useState([])
  const [stylists, setStylists] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [loading, setLoading] = useState(true)
  const { error } = useToast()
  const navigate = useNavigate()

  useEffect(() => {
    async function fetchData() {
      try {
        const [servResp, stylResp] = await Promise.all([
          api.get('/services'),
          api.get('/stylists'),
        ])
        setServices(servResp.data || [])
        setStylists(stylResp.data || [])
      } catch (err) {
        console.error('Failed to load services & stylists:', err)
        error('Could not load salon services.')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const categories = ['All', ...new Set(services.map((s) => s.category).filter(Boolean))]

  const filteredServices =
    selectedCategory === 'All'
      ? services
      : services.filter((s) => s.category === selectedCategory)

  if (loading) {
    return (
      <div className="py-20 flex flex-col items-center justify-center gap-3">
        <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-sm text-gray-500">Loading catalog...</p>
      </div>
    )
  }

  return (
    <div className="space-y-16 py-8">
      {/* Services Section */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <span className="text-xs font-semibold text-indigo-600 uppercase tracking-widest bg-indigo-50 px-2.5 py-1 rounded-full">
              Hair, Nails & Treatments
            </span>
            <h1 className="text-3xl font-extrabold text-gray-900 mt-2 tracking-tight">
              Salon Services
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Select any service to view live openings and book with our master stylists.
            </p>
          </div>

          {/* Category Filter Pills */}
          <div className="flex flex-wrap gap-1.5 bg-gray-100 p-1.5 rounded-2xl">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                  selectedCategory === cat
                    ? 'bg-white text-indigo-700 shadow-xs'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Services Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredServices.map((s) => (
            <div
              key={s.id}
              className="bg-white rounded-2xl border border-gray-100 p-6 shadow-xs hover:shadow-md transition flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[11px] font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                    {s.category}
                  </span>
                  <span className="text-xl font-bold text-gray-900">${s.price}</span>
                </div>
                <h3 className="text-lg font-bold text-gray-900 leading-snug">{s.name}</h3>
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <span>{s.duration_min} minutes</span>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-gray-50">
                <button
                  onClick={() => navigate('/book', { state: { serviceId: s.id } })}
                  className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-xl transition shadow-xs flex items-center justify-center gap-2"
                >
                  <Scissors className="w-4 h-4" />
                  <span>Book This Service</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Stylists Section */}
      <section className="space-y-6 pt-6 border-t border-gray-100">
        <div>
          <span className="text-xs font-semibold text-violet-600 uppercase tracking-widest bg-violet-50 px-2.5 py-1 rounded-full">
            Artistry & Experience
          </span>
          <h2 className="text-2xl font-bold text-gray-900 mt-2 tracking-tight">
            Meet Our Master Stylists
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Our certified professionals specialize in modern cuts, color artistry, and restorative treatments.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {stylists.map((stylist) => (
            <div
              key={stylist.id}
              className="bg-white rounded-2xl border border-gray-100 p-6 shadow-xs hover:shadow-md transition flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 text-white flex items-center justify-center font-bold text-lg shadow-sm">
                  {stylist.name.charAt(0)}
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900">{stylist.name}</h3>
                  <div className="flex items-center gap-1.5 text-xs text-violet-700 font-medium mt-1">
                    <Award className="w-3.5 h-3.5" />
                    <span>{stylist.specialization || 'Master Stylist'}</span>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-gray-50">
                <button
                  onClick={() => navigate('/book', { state: { stylistId: stylist.id } })}
                  className="w-full py-2 bg-gray-50 hover:bg-indigo-50 hover:text-indigo-600 text-gray-700 font-semibold text-xs rounded-xl transition"
                >
                  Book with {stylist.name.split(' ')[0]}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
