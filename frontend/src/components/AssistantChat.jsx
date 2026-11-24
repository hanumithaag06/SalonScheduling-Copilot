// Why: Conversational AI salon booking assistant floating widget.
// Translates natural language queries into ranked slot suggestions using /assistant/suggest.
// Explicitly enforces that booking requires user review and cannot be created automatically.

import React, { useState, useRef, useEffect } from 'react'
import { Sparkles, Send, X, Bot, ArrowRight, AlertCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

export default function AssistantChat() {
  const [isOpen, setIsOpen] = useState(false)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'assistant',
      text: "Hi! I'm your Stylify AI Assistant. Tell me what service you're looking for (e.g., 'Classic haircut tomorrow afternoon under $50') and I'll find top recommendations for you!",
    },
  ])
  const messagesEndRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isOpen])

  const handleSend = async (e) => {
    if (e) e.preventDefault()
    const query = input.trim()
    if (!query || loading) return

    const userMsgId = Date.now().toString()
    setMessages((prev) => [...prev, { id: userMsgId, sender: 'user', text: query }])
    setInput('')
    setLoading(true)

    try {
      const resp = await api.post('/assistant/suggest', { message: query })
      const data = resp.data

      const assistantMsg = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: data.message,
        followUp: data.follow_up_question,
        suggestions: data.suggestions || [],
        intent: data.intent,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      console.error('Assistant error:', err)
      const detail = err.response?.data?.detail || 'Unable to connect to assistant right now.'
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'assistant',
          text: `Sorry, I encountered an issue: ${detail}`,
          isError: true,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleSelectSlot = (suggestion) => {
    setIsOpen(false)
    // Navigate to /book with prefilled state from assistant recommendation
    navigate('/book', {
      state: {
        serviceId: suggestion.service_id,
        stylistId: suggestion.stylist_id,
        date: suggestion.start_time.split('T')[0],
        preselectedSlot: suggestion.start_time,
      },
    })
  }

  return (
    <>
      {/* Floating Trigger Button */}
      <button
        onClick={() => setIsOpen((o) => !o)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-semibold px-4 py-3 rounded-full shadow-2xl shadow-indigo-300 hover:scale-105 active:scale-95 transition-all"
        aria-label="Toggle AI Booking Assistant"
      >
        <Sparkles className="w-5 h-5 animate-pulse" />
        <span className="hidden sm:inline">Ask Stylify AI</span>
      </button>

      {/* Floating Chat Drawer / Window */}
      {isOpen && (
        <div className="fixed bottom-20 right-4 sm:right-6 z-50 w-[92vw] sm:w-[420px] max-h-[620px] h-[82vh] bg-white rounded-3xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-4">
          {/* Header */}
          <div className="px-5 py-4 bg-gradient-to-r from-indigo-700 to-violet-700 text-white flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-sm tracking-wide">Stylify Copilot</h3>
                <p className="text-[11px] text-indigo-200">Natural language appointment finder</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-white/80 hover:text-white p-1 rounded-lg transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Architectural Guard Banner */}
          <div className="bg-amber-50 border-b border-amber-200 px-3.5 py-1.5 text-[11px] text-amber-800 flex items-center gap-1.5 font-medium">
            <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span>Assistant provides suggestions. Confirmations happen on review.</span>
          </div>

          {/* Messages Feed */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50/60">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex gap-2.5 ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {m.sender === 'assistant' && (
                  <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0 mt-1">
                    <Bot className="w-4 h-4" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl p-3.5 text-sm ${
                    m.sender === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-xs'
                      : m.isError
                      ? 'bg-rose-50 border border-rose-200 text-rose-800'
                      : 'bg-white border border-gray-100 text-gray-800 shadow-xs rounded-bl-xs'
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{m.text}</p>

                  {/* Clarifying Follow-Up Question */}
                  {m.followUp && (
                    <div className="mt-2.5 pt-2 border-t border-gray-100 text-indigo-700 font-medium text-xs flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 shrink-0" />
                      <span>{m.followUp}</span>
                    </div>
                  )}

                  {/* Recommended Slots Cards */}
                  {m.suggestions && m.suggestions.length > 0 && (
                    <div className="mt-3 space-y-2">
                      <p className="text-[11px] font-semibold uppercase text-gray-500 tracking-wider">
                        Top Recommended Picks
                      </p>
                      {m.suggestions.map((s, idx) => (
                        <div
                          key={idx}
                          className="p-2.5 bg-indigo-50/60 hover:bg-indigo-50 border border-indigo-100 rounded-xl transition flex flex-col gap-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-gray-900 text-xs">
                              {s.stylist_name}
                            </span>
                            <span className="text-[11px] font-bold text-indigo-600">
                              {new Date(s.start_time).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          </div>
                          <p className="text-[11px] text-gray-600 leading-snug">{s.reason}</p>
                          <button
                            onClick={() => handleSelectSlot(s, m.intent)}
                            className="mt-1 flex items-center justify-center gap-1 w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs py-1.5 rounded-lg shadow-xs transition"
                          >
                            <span>Book this slot</span>
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-2 text-gray-500 text-xs p-2">
                <div className="w-2 h-2 rounded-full bg-indigo-600 animate-ping"></div>
                <span>Assistant is finding optimal slots...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Box */}
          <form onSubmit={handleSend} className="p-3 bg-white border-t border-gray-100 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g. Balayage next Friday afternoon..."
              className="flex-1 px-4 py-2.5 bg-gray-100 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-gray-900"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="p-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl transition shadow-xs"
              aria-label="Send message"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}
    </>
  )
}
