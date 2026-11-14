import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import AuctionList from './pages/AuctionList'
import CreateRFQ from './pages/CreateRFQ'
import AuctionDetails from './pages/AuctionDetails'
import './style.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <nav>
      <Link to="/">Auctions</Link>
      <Link to="/new">+ New RFQ</Link>
    </nav>
    <main>
      <Routes>
        <Route path="/" element={<AuctionList />} />
        <Route path="/new" element={<CreateRFQ />} />
        <Route path="/rfq/:id" element={<AuctionDetails />} />
      </Routes>
    </main>
  </BrowserRouter>
)
