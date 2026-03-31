import React, { useState, useEffect } from 'react'
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend, ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'

const API = '/api/v1'

export default function Analytics({ token }) {
  const [comp, setComp] = useState(null)
  const [forecast, setForecast] = useState(null)
  const [trend, setTrend] = useState([])

  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    const load = async () => {
      try {
        const [c, f, t] = await Promise.all([
          fetch(`${API}/analytics/comparison`, { headers }).then(r => r.json()),
          fetch(`${API}/analytics/forecast`, { headers }).then(r => r.json()),
          fetch(`${API}/analytics/emissions/trend`, { headers }).then(r => r.json()),
        ])
        setComp(c.data)
        setForecast(f.data)
        setTrend(t.data || [])
      } catch (err) { console.error(err) }
    }
    load()
  }, [token])

  const radarData = comp?.dimensions?.map(d => ({
    dimension: d.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    Proposed: comp.proposed?.[d] || 0,
    'Traditional ETS': comp.traditional_ets?.[d] || 0,
    'Static Model': comp.static_model?.[d] || 0,
  })) || []

  const forecastData = forecast?.forecast_prices?.map((p, i) => ({
    step: `T+${i + 1}`,
    price: p,
    upper: forecast.confidence_interval?.upper?.[i],
    lower: forecast.confidence_interval?.lower?.[i],
  })) || []

  const trendData = trend.slice(-50).map((t, i) => ({
    name: `#${i + 1}`,
    co2e: parseFloat(t.co2e?.toFixed(4)),
  }))

  return (
    <div>
      <div className="page-header">
        <h2>📈 Analytics</h2>
        <p className="page-subtitle">System performance, forecasting, and comparative analysis</p>
      </div>

      {comp && (
        <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
          <div className="kpi-card green">
            <div className="kpi-label">Proposed System</div>
            <div className="kpi-value">{comp.overall_scores?.proposed?.toFixed(1)}/10</div>
            <div className="kpi-sub">overall score</div>
          </div>
          <div className="kpi-card orange">
            <div className="kpi-label">Traditional ETS</div>
            <div className="kpi-value">{comp.overall_scores?.traditional_ets?.toFixed(1)}/10</div>
            <div className="kpi-sub">baseline comparison</div>
          </div>
          <div className="kpi-card red">
            <div className="kpi-label">Static Model</div>
            <div className="kpi-value">{comp.overall_scores?.static_model?.toFixed(1)}/10</div>
            <div className="kpi-sub">legacy system</div>
          </div>
        </div>
      )}

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Comparative Radar Chart</div>
          <div className="chart-container" style={{ height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(148,163,184,0.15)" />
                <PolarAngleAxis dataKey="dimension" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <PolarRadiusAxis angle={30} domain={[0, 10]} tick={{ fill: '#64748b', fontSize: 10 }} />
                <Radar name="Proposed" dataKey="Proposed" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} strokeWidth={2} />
                <Radar name="Traditional ETS" dataKey="Traditional ETS" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.1} strokeWidth={2} />
                <Radar name="Static Model" dataKey="Static Model" stroke="#ef4444" fill="#ef4444" fillOpacity={0.1} strokeWidth={2} />
                <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Price Forecast (ARIMA)</div>
          <div className="chart-container" style={{ height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={forecastData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                <XAxis dataKey="step" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#1a2235', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, color: '#e2e8f0' }} />
                <Line type="monotone" dataKey="price" stroke="#06b6d4" strokeWidth={2} dot={{ fill: '#06b6d4' }} />
                <Line type="monotone" dataKey="upper" stroke="#34d399" strokeDasharray="5 5" strokeWidth={1} dot={false} />
                <Line type="monotone" dataKey="lower" stroke="#ef4444" strokeDasharray="5 5" strokeWidth={1} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Emission Trend</div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1a2235', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, color: '#e2e8f0' }} />
              <Line type="monotone" dataKey="co2e" stroke="#8b5cf6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
