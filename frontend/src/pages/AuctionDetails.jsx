import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getRfq, placeBid, fmt } from '../api'

const triggerLabel = {
  BID: 'Bid received in last X min',
  ANY_RANK: 'Any rank change in last X min',
  L1_RANK: 'L1 change in last X min',
}

const emptyBid = {
  carrier_name: '', freight_charges: '', origin_charges: '', destination_charges: '',
  transit_days: '', quote_validity: '',
}

export default function AuctionDetails() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [bid, setBid] = useState(emptyBid)
  const [msg, setMsg] = useState('')

  const load = () => getRfq(id).then(setData)

  useEffect(() => {
    load()
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [id])

  const submit = async e => {
    e.preventDefault()
    try {
      const res = await placeBid(id, {
        ...bid,
        freight_charges: Number(bid.freight_charges),
        origin_charges: Number(bid.origin_charges || 0),
        destination_charges: Number(bid.destination_charges || 0),
        transit_days: Number(bid.transit_days),
      })
      setMsg(`Bid placed: ${res.total}` + (res.extended ? ' (auction extended)' : ''))
      setBid({ ...emptyBid, carrier_name: bid.carrier_name })
      load()
    } catch (err) {
      setMsg(err.message)
    }
  }

  if (!data) return <p>Loading...</p>
  const { rfq, ranking, bids, activity } = data
  const set = e => setBid({ ...bid, [e.target.name]: e.target.value })

  return (
    <>
      <h2>{rfq.name} <span className="muted">({rfq.ref_id})</span></h2>
      <div className="card grid">
        <div><b>Status:</b> {rfq.status}</div>
        <div><b>Bid start:</b> {fmt(rfq.bid_start)}</div>
        <div><b>Original close:</b> {fmt(rfq.original_close)}</div>
        <div><b>Current close:</b> {fmt(rfq.bid_close)}</div>
        <div><b>Forced close:</b> {fmt(rfq.forced_close)}</div>
        <div><b>Pickup date:</b> {fmt(rfq.pickup_date)}</div>
        <div><b>Trigger window (X):</b> {rfq.trigger_window} min</div>
        <div><b>Extension (Y):</b> {rfq.extension_minutes} min</div>
        <div><b>Trigger:</b> {triggerLabel[rfq.trigger_type]}</div>
      </div>

      <h3>Supplier ranking</h3>
      <table>
        <thead>
          <tr><th>Rank</th><th>Carrier</th><th>Freight</th><th>Origin</th><th>Destination</th><th>Total</th><th>Transit (days)</th><th>Valid till</th></tr>
        </thead>
        <tbody>
          {ranking.map(b => (
            <tr key={b.id}>
              <td><b>{b.rank}</b></td>
              <td>{b.carrier_name}</td>
              <td>{b.freight_charges}</td>
              <td>{b.origin_charges}</td>
              <td>{b.destination_charges}</td>
              <td><b>{b.total}</b></td>
              <td>{b.transit_days}</td>
              <td>{b.quote_validity}</td>
            </tr>
          ))}
          {ranking.length === 0 && <tr><td colSpan="8">No bids yet</td></tr>}
        </tbody>
      </table>

      {rfq.status === 'Active' && (
        <form className="card" onSubmit={submit}>
          <h3>Submit quote</h3>
          <label>Carrier Name<input name="carrier_name" value={bid.carrier_name} onChange={set} required /></label>
          <label>Freight charges<input type="number" step="0.01" name="freight_charges" value={bid.freight_charges} onChange={set} required /></label>
          <label>Origin charges<input type="number" step="0.01" name="origin_charges" value={bid.origin_charges} onChange={set} /></label>
          <label>Destination charges<input type="number" step="0.01" name="destination_charges" value={bid.destination_charges} onChange={set} /></label>
          <label>Transit time (days)<input type="number" name="transit_days" value={bid.transit_days} onChange={set} required /></label>
          <label>Quote valid till<input type="date" name="quote_validity" value={bid.quote_validity} onChange={set} required /></label>
          <button>Place bid</button>
          {msg && <p>{msg}</p>}
        </form>
      )}

      <div className="two-col">
        <div>
          <h3>All bids ({bids.length})</h3>
          <table>
            <thead><tr><th>Carrier</th><th>Total</th><th>Time</th></tr></thead>
            <tbody>
              {bids.map(b => (
                <tr key={b.id}><td>{b.carrier_name}</td><td>{b.total}</td><td>{fmt(b.created_at)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <h3>Activity log</h3>
          <ul className="log">
            {activity.map(a => (
              <li key={a.id} className={a.event === 'EXTENSION' ? 'ext' : ''}>
                <span className="muted">{fmt(a.created_at)}</span> {a.message}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </>
  )
}
