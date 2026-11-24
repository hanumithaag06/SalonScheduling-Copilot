// Why: Visual 5-minute hold timer component displaying countdown clock and release button.
// Alerts the customer when the slot hold is expiring or has expired.

import React, { useState, useEffect } from 'react'
import { Clock, AlertTriangle } from 'lucide-react'

export default function HoldCountdown({ expiresAt, onExpired, onRelease }) {
  const [timeLeft, setTimeLeft] = useState(() => {
    const diff = Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000))
    return diff
  })

  useEffect(() => {
    const timer = setInterval(() => {
      const remaining = Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000))
      setTimeLeft(remaining)
      if (remaining <= 0) {
        clearInterval(timer)
        if (onExpired) onExpired()
      }
    }, 1000)

    return () => clearInterval(timer)
  }, [expiresAt, onExpired])

  const minutes = Math.floor(timeLeft / 60)
  const seconds = timeLeft % 60
  const isExpiringSoon = timeLeft < 60 && timeLeft > 0

  return (
    <div
      className={`flex flex-col sm:flex-row items-center justify-between p-3.5 rounded-xl border transition-colors ${
        timeLeft === 0
          ? 'bg-rose-50 border-rose-200 text-rose-800'
          : isExpiringSoon
          ? 'bg-amber-50 border-amber-300 text-amber-900 animate-pulse'
          : 'bg-indigo-50 border-indigo-200 text-indigo-900'
      }`}
    >
      <div className="flex items-center gap-2.5 mb-2 sm:mb-0">
        {timeLeft === 0 ? (
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
        ) : (
          <Clock className="w-5 h-5 text-indigo-600 shrink-0" />
        )}
        <div className="text-sm">
          {timeLeft > 0 ? (
            <span>
              Slot held for you! Complete booking in{' '}
              <strong className="font-mono text-base">
                {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
              </strong>
            </span>
          ) : (
            <span className="font-semibold">Hold expired. The slot has been released.</span>
          )}
        </div>
      </div>
      {onRelease && timeLeft > 0 && (
        <button
          onClick={onRelease}
          className="text-xs text-gray-500 hover:text-rose-600 underline transition"
        >
          Cancel Hold
        </button>
      )}
    </div>
  )
}
