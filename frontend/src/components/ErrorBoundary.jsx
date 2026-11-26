// Why: Global React Error Boundary preventing white screen of death.
// Catches unhandled rendering errors and displays a clear diagnostic card with a reload button.

import React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an unhandled render error:', error, errorInfo)
    this.setState({ errorInfo })
  }

  handleReload = () => {
    window.location.reload()
  }

  handleResetState = () => {
    localStorage.clear()
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 text-gray-900">
          <div className="max-w-lg w-full bg-white p-8 rounded-3xl border border-gray-100 shadow-xl space-y-5 text-center">
            <div className="w-14 h-14 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center mx-auto shadow-xs">
              <AlertTriangle className="w-7 h-7" />
            </div>

            <div>
              <h2 className="text-2xl font-black text-gray-900 tracking-tight">Something went wrong</h2>
              <p className="text-xs text-gray-500 mt-1">
                The application encountered an unexpected runtime error.
              </p>
            </div>

            {this.state.error && (
              <div className="p-3.5 bg-gray-50 border border-gray-100 rounded-2xl text-left overflow-x-auto text-xs text-rose-700 font-mono">
                {this.state.error.toString()}
              </div>
            )}

            <div className="flex gap-2.5 pt-2">
              <button
                onClick={this.handleReload}
                className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-1.5"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Reload Page</span>
              </button>
              <button
                onClick={this.handleResetState}
                className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold text-xs rounded-xl transition"
              >
                Reset Session & Home
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
