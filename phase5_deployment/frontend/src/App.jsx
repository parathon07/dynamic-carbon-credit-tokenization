import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Trading from './pages/Trading'
import Analytics from './pages/Analytics'
import Blockchain from './pages/Blockchain'
import Login from './pages/Login'

const API = '/api/v1'

function App() {
  const getInitialToken = () => {
    try { return localStorage.getItem('token'); } catch (e) { return null; }
  };
  const [token, setToken] = useState(getInitialToken())
  const [user, setUser] = useState(null)

  useEffect(() => {
    if (token) {
      fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
        .then(r => r.ok ? r.json() : Promise.reject())
        .then(setUser)
        .catch(() => { setToken(null); localStorage.removeItem('token') })
    }
  }, [token])

  const handleLogin = (t) => {
    try { localStorage.setItem('token', t); } catch(e) {}
    setToken(t)
  }

  const handleLogout = () => {
    try { localStorage.removeItem('token'); } catch(e) {}
    setToken(null)
    setUser(null)
  }

  if (!token) return <Login onLogin={handleLogin} />

  return (
    <BrowserRouter>
      <div className="app-layout">
        <aside className="sidebar">
          <div className="sidebar-logo">
            <div className="logo-icon">🌍</div>
            <div>
              <h1>Carbon Credit</h1>
              <span className="subtitle">Trading Platform</span>
            </div>
          </div>

          <div className="nav-section">
            <div className="nav-section-title">Main</div>
            <NavLink to="/" end className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
              <span className="icon">📊</span> Dashboard
            </NavLink>
            <NavLink to="/trading" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
              <span className="icon">💱</span> Trading
            </NavLink>
            <NavLink to="/analytics" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
              <span className="icon">📈</span> Analytics
            </NavLink>
            <NavLink to="/blockchain" className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`}>
              <span className="icon">⛓️</span> Blockchain
            </NavLink>
          </div>

          <div className="nav-section" style={{ marginTop: 'auto' }}>
            <div className="nav-section-title">Account</div>
            <div className="nav-link" style={{ cursor: 'default' }}>
              <span className="icon">👤</span>
              <div>
                <div style={{ fontSize: '13px' }}>{user?.username || '...'}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{user?.role}</div>
              </div>
            </div>
            <div className="nav-link" onClick={handleLogout}>
              <span className="icon">🚪</span> Logout
            </div>
          </div>
        </aside>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard token={token} />} />
            <Route path="/trading" element={<Trading token={token} />} />
            <Route path="/analytics" element={<Analytics token={token} />} />
            <Route path="/blockchain" element={<Blockchain token={token} />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
