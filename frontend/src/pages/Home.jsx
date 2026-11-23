// Why: Landing page — shows the app title and a live health check from the
// backend. Proves Tailwind styling AND the API proxy are working.

import { useState } from 'react'
import api from '../api/client'

export default function Home() {
  const [health, setHealth] = useState(null)

  const checkHealth = async () => {
    try {
      const res = await api.get('/health')
      setHealth(res.data)
    } catch {
      setHealth({ status: 'error', detail: 'Cannot reach backend' })
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-50 flex items-center justify-center">
      <div className="text-center space-y-6">
        <h1 className="text-5xl font-bold text-purple-700">✂️ Stylify</h1>
        <p className="text-lg text-gray-600">
          Intelligent Salon Scheduling Platform
        </p>
        <button
          onClick={checkHealth}
          className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition cursor-pointer"
        >
          Check Backend Health
        </button>
        {health && (
          <pre className="mt-4 p-4 bg-white rounded-lg shadow text-left text-sm">
            {JSON.stringify(health, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}

