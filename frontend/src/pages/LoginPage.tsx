import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Lock, LogIn } from 'lucide-react'
import { useAppStore } from '../lib/store'

export const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const { setUserAuth } = useAppStore()
  const [username, setUsername] = useState('coordinator@demo')
  const [password, setPassword] = useState('admin123')

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    // Mock login for Phase 1 verification
    setUserAuth('mock-jwt-token', 'coordinator')
    navigate('/coordinator')
  }

  return (
    <div className="max-w-md mx-auto px-4 py-16 space-y-6">
      <div className="text-center space-y-2">
        <div className="inline-flex p-3 rounded-2xl bg-blue-500/10 text-blue-500 mb-2">
          <Lock className="w-6 h-6" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Sign In</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Access the Disaster Response Coordinator & Volunteer Dispatch portal.
        </p>
      </div>

      <form onSubmit={handleLogin} className="bg-white dark:bg-darkCard p-6 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm space-y-4">
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300 mb-1">
            Username
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full p-3 rounded-xl border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-darkMuted text-gray-900 dark:text-white text-sm"
          />
        </div>

        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300 mb-1">
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full p-3 rounded-xl border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-darkMuted text-gray-900 dark:text-white text-sm"
          />
        </div>

        <button
          type="submit"
          className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-md transition-colors flex items-center justify-center space-x-2"
        >
          <LogIn className="w-4 h-4" />
          <span>Login to Portal</span>
        </button>
      </form>
    </div>
  )
}
