async function request(url, options = {}) {
  const res = await fetch('/api' + url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const data = await res.json()
  if (!res.ok) {
    // pydantic errors come back as a list
    const msg = Array.isArray(data.detail) ? data.detail.map(d => d.msg).join(', ') : data.detail
    throw new Error(msg)
  }
  return data
}

export const getRfqs = () => request('/rfqs')
export const getRfq = id => request(`/rfqs/${id}`)
export const createRfq = body => request('/rfqs', { method: 'POST', body: JSON.stringify(body) })
export const placeBid = (id, body) => request(`/rfqs/${id}/bids`, { method: 'POST', body: JSON.stringify(body) })

export const fmt = iso => (iso ? new Date(iso).toLocaleString() : '-')
