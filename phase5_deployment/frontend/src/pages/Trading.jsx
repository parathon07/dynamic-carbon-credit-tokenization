import React, { useState, useEffect } from 'react'

const API = '/api/v1'

export default function Trading({ token }) {
  const [orderBook, setOrderBook] = useState({ bids: [], asks: [] })
  const [price, setPrice] = useState(null)
  const [history, setHistory] = useState([])
  const [form, setForm] = useState({ participant_id: '', side: 'buy', quantity: 1, price: 25, order_type: 'limit' })
  const [msg, setMsg] = useState('')

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const load = async () => {
    try {
      const [ob, pr, hist] = await Promise.all([
        fetch(`${API}/trading/orderbook`, { headers }).then(r => r.json()),
        fetch(`${API}/trading/price`, { headers }).then(r => r.json()),
        fetch(`${API}/trading/history`, { headers }).then(r => r.json()),
      ])
      setOrderBook(ob.data || { bids: [], asks: [] })
      setPrice(pr.data)
      setHistory(hist.data || [])
    } catch (err) { console.error(err) }
  }

  useEffect(() => { load(); const iv = setInterval(load, 8000); return () => clearInterval(iv) }, [token])

  const placeOrder = async (e) => {
    e.preventDefault()
    setMsg('')
    try {
      const res = await fetch(`${API}/trading/orders`, { method: 'POST', headers, body: JSON.stringify(form) })
      const data = await res.json()
      if (res.ok) { setMsg(`✓ Order ${data.data?.order_id} placed`); load() }
      else setMsg(`✗ ${data.detail || data.message}`)
    } catch (err) { setMsg(`✗ ${err.message}`) }
  }

  return (
    <div>
      <div className="page-header">
        <h2>💱 Trading</h2>
        <p className="page-subtitle">P2P carbon credit marketplace</p>
      </div>

      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <div className="kpi-card cyan">
          <div className="kpi-label">Credit Price</div>
          <div className="kpi-value">${price?.current_price?.toFixed(2) || '—'}</div>
          <div className="kpi-sub">{price?.symbol || 'CCT'}</div>
        </div>
        <div className="kpi-card green">
          <div className="kpi-label">24h Volume</div>
          <div className="kpi-value">{price?.volume_24h || 0}</div>
          <div className="kpi-sub">trades</div>
        </div>
        <div className="kpi-card blue">
          <div className="kpi-label">Bid Count</div>
          <div className="kpi-value">{orderBook.bids?.length || 0}</div>
          <div className="kpi-sub">open bids</div>
        </div>
        <div className="kpi-card orange">
          <div className="kpi-label">Ask Count</div>
          <div className="kpi-value">{orderBook.asks?.length || 0}</div>
          <div className="kpi-sub">open asks</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Place Order</div>
          <form onSubmit={placeOrder}>
            <div className="form-group">
              <label>Participant ID</label>
              <input value={form.participant_id} onChange={e => setForm({...form, participant_id: e.target.value})} placeholder="e.g. FAC_001" required />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="form-group">
                <label>Side</label>
                <select value={form.side} onChange={e => setForm({...form, side: e.target.value})}>
                  <option value="buy">Buy</option>
                  <option value="sell">Sell</option>
                </select>
              </div>
              <div className="form-group">
                <label>Type</label>
                <select value={form.order_type} onChange={e => setForm({...form, order_type: e.target.value})}>
                  <option value="limit">Limit</option>
                  <option value="market">Market</option>
                </select>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="form-group">
                <label>Quantity (CCT)</label>
                <input type="number" step="0.01" min="0.01" value={form.quantity} onChange={e => setForm({...form, quantity: parseFloat(e.target.value)})} required />
              </div>
              <div className="form-group">
                <label>Price ($)</label>
                <input type="number" step="0.01" min="0.01" value={form.price} onChange={e => setForm({...form, price: parseFloat(e.target.value)})} />
              </div>
            </div>
            <button type="submit" className={`btn ${form.side === 'buy' ? 'btn-success' : 'btn-danger'}`} style={{ width: '100%' }}>
              {form.side === 'buy' ? '🟢 Place Buy Order' : '🔴 Place Sell Order'}
            </button>
            {msg && <p style={{ marginTop: 12, fontSize: 13, color: msg.startsWith('✓') ? 'var(--accent-green)' : 'var(--accent-red)' }}>{msg}</p>}
          </form>
        </div>

        <div className="card">
          <div className="card-title">Order Book</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <div style={{ fontSize: 12, color: 'var(--accent-green)', fontWeight: 600, marginBottom: 8 }}>BIDS (Buy)</div>
              {orderBook.bids?.length > 0 ? orderBook.bids.map((b, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 13, color: 'var(--text-secondary)' }}>
                  <span>${b.price?.toFixed(2)}</span><span>{b.quantity?.toFixed(2)}</span>
                </div>
              )) : <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No bids</p>}
            </div>
            <div>
              <div style={{ fontSize: 12, color: 'var(--accent-red)', fontWeight: 600, marginBottom: 8 }}>ASKS (Sell)</div>
              {orderBook.asks?.length > 0 ? orderBook.asks.map((a, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 13, color: 'var(--text-secondary)' }}>
                  <span>${a.price?.toFixed(2)}</span><span>{a.quantity?.toFixed(2)}</span>
                </div>
              )) : <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No asks</p>}
            </div>
          </div>
          {orderBook.spread && (
            <div style={{ marginTop: 16, padding: '8px 12px', background: 'var(--bg-secondary)', borderRadius: 8, fontSize: 12, color: 'var(--text-muted)' }}>
              Spread: ${orderBook.spread?.toFixed(2)}&nbsp;•&nbsp;Last: ${orderBook.last_price?.toFixed(2)}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
