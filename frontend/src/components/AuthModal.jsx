import React, { useState } from 'react'
import { User, Lock, Mail, ShieldCheck, X, LogIn, UserPlus } from 'lucide-react'
import axios from 'axios'

export default function AuthModal({ isOpen, onClose, onLoginSuccess }) {
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  if (!isOpen) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isRegister) {
        const res = await axios.post('/auth/register', { username, email, password })
        if (res.data.status === 'success') {
          // Auto login after register
          const loginRes = await axios.post('/auth/login', { username, password })
          localStorage.setItem('user', JSON.stringify(loginRes.data.user))
          localStorage.setItem('token', loginRes.data.token)
          onLoginSuccess(loginRes.data.user)
          onClose()
        }
      } else {
        const res = await axios.post('/auth/login', { username, password })
        if (res.data.status === 'success') {
          localStorage.setItem('user', JSON.stringify(res.data.user))
          localStorage.setItem('token', res.data.token)
          onLoginSuccess(res.data.user)
          onClose()
        }
      }
    } catch (err) {
      console.error('Auth error:', err)
      setError(err.response?.data?.error || 'Authentication failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-[#0B111E] border border-slate-800 rounded-3xl max-w-md w-full p-8 space-y-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 text-slate-400 hover:text-white rounded-xl bg-slate-900 border border-slate-800"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-cyan-500/10 text-cyan-400 rounded-2xl border border-cyan-500/20">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-extrabold text-white text-lg font-heading">
              {isRegister ? 'Create Account' : 'User Account Sign In'}
            </h3>
            <p className="text-xs text-slate-400 font-mono">
              {isRegister ? 'Sign up for a separate user account' : 'Sign in to access your private scan history'}
            </p>
          </div>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs font-mono">
            ⚠️ {error}
          </div>
        )}

        {/* Form Inputs */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[11px] font-mono text-slate-400">Username</label>
            <div className="relative">
              <User className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="your_username"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 text-xs font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          {isRegister && (
            <div className="space-y-1.5">
              <label className="text-[11px] font-mono text-slate-400">Email Address</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 text-xs font-mono focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-[11px] font-mono text-slate-400">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 text-xs font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-extrabold text-xs font-heading shadow-glow-cyan transition-all disabled:opacity-50 flex items-center justify-center space-x-2"
          >
            {isRegister ? <UserPlus className="w-4 h-4" /> : <LogIn className="w-4 h-4" />}
            <span>{loading ? 'Processing...' : isRegister ? 'Create Account' : 'Sign In'}</span>
          </button>
        </form>

        {/* Toggle Mode */}
        <div className="text-center pt-2 border-t border-slate-800/80">
          <button
            onClick={() => {
              setIsRegister(!isRegister)
              setError('')
            }}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-mono"
          >
            {isRegister ? 'Already have an account? Sign In' : "Don't have an account? Create Account"}
          </button>
        </div>
      </div>
    </div>
  )
}
