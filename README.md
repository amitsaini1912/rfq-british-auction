# RFQ System with British Auction

Simplified RFQ system where suppliers bid against each other and the auction auto-extends on late activity, but never past the forced close time.

- Backend: FastAPI + SQLite
- Frontend: React (Vite)
- Design docs: [HLD](docs/HLD.md), [Schema](docs/SCHEMA.md)

## Run

Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 (api calls are proxied to :8000).

Tests
```bash
cd backend && pytest
```

## Features

- Create RFQ with bid start, bid close, forced close, pickup date
- Auction config: trigger window X, extension Y, trigger type
  - bid received in last X min
  - any supplier rank change in last X min
  - L1 change in last X min
- Validation: forced close > bid close, extension capped at forced close
- Listing page: RFQ, lowest bid, current close, forced close, status (Active / Closed / Force Closed)
- Details page: ranking L1/L2/.., quote details, all bids, X/Y config, activity log with extension reasons

## API

| Method | Path | |
|---|---|---|
| POST | /api/rfqs | create RFQ |
| GET | /api/rfqs | list auctions |
| GET | /api/rfqs/{id} | details, ranking, bids, activity |
| POST | /api/rfqs/{id}/bids | submit quote |

## Assumptions

- Extension adds Y minutes to the current close time (6:00 -> 6:05), not to the bid time.
- A supplier can rebid, but only lower than their own previous best. Their best bid is used for ranking.
- Ranking is by total = freight + origin + destination.
- No login, supplier just types carrier name.
