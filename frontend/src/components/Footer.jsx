// Why: Site footer with brand info, quick links, and college project viva attribution.

import React from 'react'
import { Scissors } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="bg-white border-t border-gray-100 py-10 mt-16 text-xs text-gray-500">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center text-white">
            <Scissors className="w-3.5 h-3.5" />
          </div>
          <span className="font-bold text-gray-900">Stylify Salon Platform</span>
          <span>&bull; Intelligent Salon Copilot</span>
        </div>

        <div className="flex gap-4">
          <Link to="/services" className="hover:text-gray-900 transition">
            Services
          </Link>
          <Link to="/book" className="hover:text-gray-900 transition">
            Book
          </Link>
          <Link to="/waitlist" className="hover:text-gray-900 transition">
            Waitlist
          </Link>
        </div>

        <div>
          <span>&copy; {new Date().getFullYear()} Stylify Inc. All rights reserved.</span>
        </div>
      </div>
    </footer>
  )
}
