import React, { useState, useEffect } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'

const API = '/api/v1'

function KPI({ label, value, sub, color = 'blue' }) {
  return (
    <div className={`kpi-card ${color}`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  )
}

export default function Dashboard({ token }) {
  const [overview, setOverview] = useState(null)
  const [readings, setReadings] = useState([])
  const [facilities, setFacilities] = useState([])
  const [health, setHealth] = useState(null)

  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    const load = async () => {
      try {
        const [ov, rd, fac, hl] = await Promise.all([
          fetch(`${API}/analytics/overview`, { headers }).then(r => r.json()),
          fetch(`${API}/emissions/readings?limit=50`, { headers }).then(r => r.json()),
          fetch(`${API}/emissions/facilities`, { headers }).then(r => r.json()),
          fetch(`${API}/health`).then(r => r.json()),
        ])
        setOverview(ov.data)
        setReadings(rd.data || [])
        setFacilities(fac.data || [])
        setHealth(hl)
      } catch (err) { console.error(err) }
    }
    load()
    const iv = setInterval(load, 10000)
    return () => clearInterval(iv)
  }, [token])

  const chartData = readings.slice(-30).map((r, i) => ({
    name: `#${i + 1}`,
    co2e: r.co2e_emission?.toFixed(4),
    credits: r.credits_earned?.toFixed(4),
  }))

  return (
    <div>
      <div className="page-header">
        <h2>📊 Dashboard</h2>
        <p className="page-subtitle">
          Real-time emission monitoring and system overview
          {health && <> &nbsp;•&nbsp; <span className="status-dot online"></span>System {health.status}</>}
        </p>
      </div>

      <div className="kpi-grid">
        <KPI label="Total CO₂e Emissions" value={overview?.total_emissions?.toFixed(2) || '—'} sub="kg CO₂ equivalent" color="red" />
        <KPI label="Credits Minted" value={overview?.total_credits_minted?.toFixed(4) || '—'} sub="CCT tokens" color="green" />
        <KPI label="Active Facilities" value={overview?.active_facilities || '—'} sub="monitored" color="blue" />
        <KPI label="Blockchain Blocks" value={overview?.blockchain_blocks || '—'} sub="immutable records" color="purple" />
        <KPI label="Credit Price" value={`$${overview?.current_price?.toFixed(2) || '—'}`} sub="per CCT" color="cyan" />
        <KPI label="Anomaly Rate" value={`${overview?.anomaly_rate?.toFixed(1) || '—'}%`} sub="of readings" color="orange" />
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Emission Trend (Recent)</div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="gradCo2e" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#1a2235', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, color: '#e2e8f0' }} />
                <Area type="monotone" dataKey="co2e" stroke="#3b82f6" fill="url(#gradCo2e)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Credits Earned (Recent)</div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#1a2235', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, color: '#e2e8f0' }} />
                <Bar dataKey="credits" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Facility Overview</div>
        {facilities.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Facility ID</th>
                <th>Type</th>
                <th>Readings</th>
                <th>Avg CO₂e</th>
                <th>Credit Balance</th>
              </tr>
            </thead>
            <tbody>
              {facilities.map((f, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600, color: 'var(--text-accent)' }}>{f.facility_id}</td>
                  <td><span className="badge blue">{f.facility_type}</span></td>
                  <td>{f.total_readings}</td>
                  <td>{f.avg_co2e?.toFixed(4)}</td>
                  <td style={{ color: 'var(--accent-green)' }}>{f.credit_balance?.toFixed(4)} CCT</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: 'var(--text-muted)', padding: 20, textAlign: 'center' }}>
            No facilities yet. Submit emission readings to populate data.
          </p>
        )}
      </div>
    </div>
  )
}
