// Why: Centralized Axios instance. Every API call imports this instead of
// raw axios, so the base URL and auth headers are set in one place.

import axios from 'axios'

const api = axios.create({
  baseURL: '/api',  // Vite proxy rewrites /api → http://localhost:8000
})

// Request interceptor: attaches the JWT token from localStorage to every
// outgoing request so the backend knows who the user is.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default api

