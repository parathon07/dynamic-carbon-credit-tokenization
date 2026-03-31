import React, { useState } from 'react'

const API = '/api/v1'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Login failed')
      }
      const data = await res.json()
      onLogin(data.access_token)
    } catch (err) {
      setError(err.message)
    }
    setLoading(false)
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
          <div style={{
            width: 56, height: 56, margin: '0 auto 12px',
            background: 'linear-gradient(135deg, #3b82f6, #06b6d4)',
            borderRadius: 16, display: 'flex', alignItems: 'center',
            justifyContent: 'center', fontSize: 28
          }}>🌍</div>
        </div>
        <h2>Carbon Credit Platform</h2>
        <p className="login-sub">Sign in to access the trading dashboard</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Enter username"
              required
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter password"
              required
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
          {error && <p className="error-msg">{error}</p>}
        </form>

        <div style={{ marginTop: 24, padding: '16px', background: 'var(--bg-secondary)',
          borderRadius: 8, fontSize: 12, color: 'var(--text-muted)' }}>
          <strong>Demo Accounts:</strong><br />
          admin / admin123 &nbsp;•&nbsp; operator / operator123 &nbsp;•&nbsp; viewer / viewer123
        </div>
      </div>
    </div>
  )
}
