// Why: Landing page showcasing Stylify salon features, AI assistant prompt ideas,
// top services preview, and quick-booking call to actions.

import React from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, ShieldCheck, Clock } from 'lucide-react'

export default function Home() {
  return (
    <div className="space-y-16 py-8 sm:py-12">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-900 via-indigo-950 to-slate-900 text-white p-8 sm:p-16 shadow-2xl">
        <div className="relative z-10 max-w-3xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-md border border-white/10 text-indigo-300 text-xs font-medium">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
            <span>AI-Driven Salon Scheduling Copilot</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-black tracking-tight leading-tight">
            Style crafted with precision. <br />
            <span className="bg-gradient-to-r from-indigo-400 via-violet-300 to-pink-300 bg-clip-text text-transparent">
              Booked effortlessly.
            </span>
          </h1>

          <p className="text-gray-300 text-base sm:text-lg max-w-2xl leading-relaxed">
            Experience Stylify: dynamic 15-minute slot calculations, smart stylist matching,
            5-minute pre-booking holds, and an AI conversational assistant that finds your ideal appointment in seconds.
          </p>

          <div className="flex flex-wrap gap-4 pt-4">
            <Link
              to="/book"
              className="px-6 py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-2xl shadow-lg shadow-indigo-600/30 transition transform hover:-translate-y-0.5"
            >
              Book an Appointment
            </Link>
            <Link
              to="/services"
              className="px-6 py-3.5 bg-white/10 hover:bg-white/15 text-white font-semibold rounded-2xl backdrop-blur-md border border-white/10 transition"
            >
              Browse Services
            </Link>
          </div>
        </div>

        {/* Decorative background grid and blurs */}
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 right-10 -mb-20 w-80 h-80 bg-violet-500/20 rounded-full blur-3xl pointer-events-none" />
      </section>

      {/* Feature Value Props */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="p-6 bg-white rounded-2xl border border-gray-100 shadow-xs hover:shadow-md transition">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4">
            <Clock className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-gray-900 mb-2">Zero Double-Booking</h3>
          <p className="text-sm text-gray-600 leading-relaxed">
            Our pure computational slot engine checks real-time working hours, buffer times, and confirmed bookings with PostgreSQL exclusion locks.
          </p>
        </div>

        <div className="p-6 bg-white rounded-2xl border border-gray-100 shadow-xs hover:shadow-md transition">
          <div className="w-12 h-12 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center mb-4">
            <Sparkles className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-gray-900 mb-2">Explainable Recommendations</h3>
          <p className="text-sm text-gray-600 leading-relaxed">
            Get personalized slot picks scored by customer loyalty, stylist specialization, preferred time of day, and calendar gap optimization.
          </p>
        </div>

        <div className="p-6 bg-white rounded-2xl border border-gray-100 shadow-xs hover:shadow-md transition">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-gray-900 mb-2">5-Minute Slot Holds</h3>
          <p className="text-sm text-gray-600 leading-relaxed">
            Select a slot and lock it exclusively for 5 minutes while you review details. Automatically cascades to waitlisted clients upon cancellation.
          </p>
        </div>
      </section>

      {/* AI Assistant Callout */}
      <section className="p-8 sm:p-10 bg-indigo-50/70 border border-indigo-100 rounded-3xl flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 bg-white px-2.5 py-1 rounded-full shadow-xs">
            <Sparkles className="w-3.5 h-3.5" />
            Try the AI Booking Assistant
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Book in plain English</h2>
          <p className="text-sm text-gray-600 max-w-xl">
            Click the purple chat icon in the bottom-right corner and type what you need:
            <span className="italic block mt-1 text-indigo-900 font-medium">
              "Deluxe cut and styling next Tuesday morning max 80"
            </span>
          </p>
        </div>
        <Link
          to="/book"
          className="whitespace-nowrap px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-md transition"
        >
          Open Booking Wizard
        </Link>
      </section>
    </div>
  )
}
