import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getRfqs, fmt } from '../api'

export default function AuctionList() {
  const [rfqs, setRfqs] = useState([])

  useEffect(() => {
    const load = () => getRfqs().then(setRfqs)
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  return (
    <>
      <h2>British Auctions</h2>
      <table>
        <thead>
          <tr>
            <th>RFQ</th>
            <th>Lowest Bid</th>
            <th>Current Close</th>
            <th>Forced Close</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rfqs.map(r => (
            <tr key={r.id}>
              <td>
                <Link to={`/rfq/${r.id}`}>{r.name}</Link>
                <div className="muted">{r.ref_id}</div>
              </td>
              <td>{r.lowest_bid ?? '-'}</td>
              <td>{fmt(r.bid_close)}</td>
              <td>{fmt(r.forced_close)}</td>
              <td><span className={'badge ' + r.status.replace(' ', '-').toLowerCase()}>{r.status}</span></td>
            </tr>
          ))}
          {rfqs.length === 0 && <tr><td colSpan="5">No auctions yet</td></tr>}
        </tbody>
      </table>
    </>
  )
}
