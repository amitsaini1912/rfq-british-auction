import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createRfq } from '../api'

const empty = {
  ref_id: '', name: '', bid_start: '', bid_close: '', forced_close: '', pickup_date: '',
  trigger_window: 10, extension_minutes: 5, trigger_type: 'BID',
}

export default function CreateRFQ() {
  const [form, setForm] = useState(empty)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const set = e => setForm({ ...form, [e.target.name]: e.target.value })

  const submit = async e => {
    e.preventDefault()
    setError('')
    if (form.forced_close <= form.bid_close) {
      return setError('Forced close time must be after bid close time')
    }
    // datetime-local gives local time without zone, convert to UTC iso
    const toIso = v => new Date(v).toISOString()
    try {
      const { id } = await createRfq({
        ...form,
        bid_start: toIso(form.bid_start),
        bid_close: toIso(form.bid_close),
        forced_close: toIso(form.forced_close),
        pickup_date: toIso(form.pickup_date),
        trigger_window: Number(form.trigger_window),
        extension_minutes: Number(form.extension_minutes),
      })
      navigate(`/rfq/${id}`)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>Create RFQ (British Auction)</h2>
      <label>Reference ID<input name="ref_id" value={form.ref_id} onChange={set} required /></label>
      <label>RFQ Name<input name="name" value={form.name} onChange={set} required /></label>
      <label>Bid Start<input type="datetime-local" name="bid_start" value={form.bid_start} onChange={set} required /></label>
      <label>Bid Close<input type="datetime-local" name="bid_close" value={form.bid_close} onChange={set} required /></label>
      <label>Forced Bid Close<input type="datetime-local" name="forced_close" value={form.forced_close} onChange={set} required /></label>
      <label>Pickup / Service Date<input type="datetime-local" name="pickup_date" value={form.pickup_date} onChange={set} required /></label>

      <h3>Auction config</h3>
      <label>Trigger Window X (min)<input type="number" min="1" name="trigger_window" value={form.trigger_window} onChange={set} /></label>
      <label>Extension Y (min)<input type="number" min="1" name="extension_minutes" value={form.extension_minutes} onChange={set} /></label>
      <label>Extension Trigger
        <select name="trigger_type" value={form.trigger_type} onChange={set}>
          <option value="BID">Bid received in last X min</option>
          <option value="ANY_RANK">Any supplier rank change in last X min</option>
          <option value="L1_RANK">L1 (lowest bidder) change in last X min</option>
        </select>
      </label>

      {error && <p className="error">{error}</p>}
      <button>Create</button>
    </form>
  )
}
