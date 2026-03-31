import React, { useState, useEffect } from 'react'

const API = '/api/v1'

export default function Blockchain({ token }) {
  const [status, setStatus] = useState(null)
  const [blocks, setBlocks] = useState([])
  const [verify, setVerify] = useState(null)
  const [verifying, setVerifying] = useState(false)

  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    const load = async () => {
      try {
        const [s, b] = await Promise.all([
          fetch(`${API}/blockchain/status`, { headers }).then(r => r.json()),
          fetch(`${API}/blockchain/blocks?limit=20`, { headers }).then(r => r.json()),
        ])
        setStatus(s.data)
        setBlocks(b.data || [])
      } catch (err) { console.error(err) }
    }
    load()
    const iv = setInterval(load, 15000)
    return () => clearInterval(iv)
  }, [token])

  const runVerify = async () => {
    setVerifying(true)
    try {
      const res = await fetch(`${API}/blockchain/verify`, { headers })
      const data = await res.json()
      setVerify(data.data)
    } catch (err) { console.error(err) }
    setVerifying(false)
  }

  return (
    <div>
      <div className="page-header">
        <h2>⛓️ Blockchain Explorer</h2>
        <p className="page-subtitle">Immutable ledger status and block inspection</p>
      </div>

      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <div className="kpi-card purple">
          <div className="kpi-label">Chain Length</div>
          <div className="kpi-value">{status?.chain_length || '—'}</div>
          <div className="kpi-sub">total blocks</div>
        </div>
        <div className="kpi-card green">
          <div className="kpi-label">Chain Valid</div>
          <div className="kpi-value">{status ? (status.is_valid ? '✓ Yes' : '✗ No') : '—'}</div>
          <div className="kpi-sub">integrity check</div>
        </div>
        <div className="kpi-card blue">
          <div className="kpi-label">Difficulty</div>
          <div className="kpi-value">{status?.difficulty || '—'}</div>
          <div className="kpi-sub">proof-of-work</div>
        </div>
        <div className="kpi-card orange">
          <div className="kpi-label">Transactions</div>
          <div className="kpi-value">{status?.total_transactions || '—'}</div>
          <div className="kpi-sub">emission records</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Chain Verification</div>
          <button className="btn btn-primary" onClick={runVerify} disabled={verifying} style={{ marginBottom: 16 }}>
            {verifying ? '🔄 Verifying...' : '🔍 Verify Full Chain'}
          </button>
          {verify && (
            <div style={{ padding: 16, background: 'var(--bg-secondary)', borderRadius: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span className={`status-dot ${verify.is_valid ? 'online' : 'offline'}`}></span>
                <span style={{ fontWeight: 600, color: verify.is_valid ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                  {verify.is_valid ? 'Chain Integrity Verified' : 'Chain Compromised'}
                </span>
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                Blocks verified: {verify.chain_length}<br />
                Genesis hash: <code style={{ color: 'var(--text-accent)', fontSize: 11 }}>{verify.genesis_hash}</code>
              </div>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">Latest Hash</div>
          <div style={{ padding: 16, background: 'var(--bg-secondary)', borderRadius: 8, wordBreak: 'break-all' }}>
            <code style={{ color: 'var(--text-accent)', fontSize: 13, lineHeight: 1.8 }}>
              {status?.latest_hash || '—'}
            </code>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Recent Blocks</div>
        {blocks.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Index</th>
                <th>Timestamp</th>
                <th>Type</th>
                <th>Hash</th>
                <th>Previous Hash</th>
              </tr>
            </thead>
            <tbody>
              {blocks.map((b, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 700, color: 'var(--accent-purple)' }}>#{b.index}</td>
                  <td>{b.timestamp?.slice(0, 19)}</td>
                  <td><span className="badge blue">{b.data_type}</span></td>
                  <td><code style={{ fontSize: 11, color: 'var(--text-accent)' }}>{b.hash}</code></td>
                  <td><code style={{ fontSize: 11, color: 'var(--text-muted)' }}>{b.previous_hash}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: 'var(--text-muted)', padding: 20, textAlign: 'center' }}>Loading blocks...</p>
        )}
      </div>
    </div>
  )
}
