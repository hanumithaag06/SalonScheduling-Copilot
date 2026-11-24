// Why: Main React application setup.
// Wraps routes in AuthProvider, ToastProvider, Navbar, AssistantChat, and ProtectedRoute guards.

import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import AssistantChat from './components/AssistantChat'
import ProtectedRoute from './components/ProtectedRoute'

import Home from './pages/Home'
import Services from './pages/Services'
import BookingWizard from './pages/BookingWizard'
import Login from './pages/Login'
import Register from './pages/Register'
import MyBookings from './pages/MyBookings'
import WaitlistPage from './pages/WaitlistPage'

import AdminLayout from './pages/admin/AdminLayout'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminCalendar from './pages/admin/AdminCalendar'
import AdminBookings from './pages/admin/AdminBookings'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <div className="min-h-screen flex flex-col bg-slate-50/50 text-gray-900 selection:bg-indigo-500 selection:text-white">
            <Navbar />
            <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8">
              <Routes>
                {/* Public Routes */}
                <Route path="/" element={<Home />} />
                <Route path="/services" element={<Services />} />
                <Route path="/book" element={<BookingWizard />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />

                {/* Customer Authenticated Routes */}
                <Route
                  path="/my-bookings"
                  element={
                    <ProtectedRoute>
                      <MyBookings />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/waitlist"
                  element={
                    <ProtectedRoute>
                      <WaitlistPage />
                    </ProtectedRoute>
                  }
                />

                {/* Protected Admin Routes */}
                <Route
                  path="/admin"
                  element={
                    <ProtectedRoute requireAdmin={true}>
                      <AdminLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<Navigate to="/admin/dashboard" replace />} />
                  <Route path="dashboard" element={<AdminDashboard />} />
                  <Route path="calendar" element={<AdminCalendar />} />
                  <Route path="bookings" element={<AdminBookings />} />
                </Route>

                {/* Fallback */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>
            <Footer />
            <AssistantChat />
          </div>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
