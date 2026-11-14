# High Level Design

## Architecture

```mermaid
flowchart LR
    U[Buyer / Supplier<br/>Browser] --> FE[React app<br/>Vite]
    FE -- REST /api --> BE[FastAPI service]
    BE --> DB[(SQLite<br/>rfqs, bids, activity_log)]
```

```
 Browser (React)  --->  FastAPI  --->  SQLite
   - listing page        - RFQ create + validation
   - create form         - bid placement + ranking
   - details page        - extension engine
   (polls every 3-5s)    - status computed from time
```

- **Frontend**: React + react-router. Three pages (listing, create RFQ, details). Pages poll the API every few seconds so close time, ranking and the log stay current.
- **Backend**: FastAPI. All auction rules live in `place_bid()` / `maybe_extend()`.
- **DB**: SQLite for simplicity. Same schema works on Postgres.

## Bid flow

1. Lock the DB for writing (`BEGIN IMMEDIATE`) so two last-second bids can't race on the close time.
2. Reject if auction isn't Active (`bid_start <= now <= bid_close`).
3. Reject if the bid is not lower than the same carrier's previous best.
4. Take ranking snapshot before, insert bid, take snapshot after.
5. If `now >= bid_close - X`, check the configured trigger:
   - `BID` – any bid
   - `ANY_RANK` – order of carriers changed
   - `L1_RANK` – the L1 carrier changed
6. If triggered: `bid_close = min(bid_close + Y, forced_close)` and write the reason to activity log.
7. Commit.

## Status

No background job is needed. Status is derived on read:

| Condition | Status |
|---|---|
| now < bid_start | Upcoming |
| now <= bid_close | Active |
| now > bid_close and bid_close == forced_close | Force Closed |
| now > bid_close | Closed |

## Ranking

Each carrier's lowest bid counts. Sorted by total (freight + origin + destination), ties broken by who bid first. Rank labels L1, L2, ...

## If this had to scale

- Postgres with `SELECT ... FOR UPDATE` on the rfq row instead of SQLite lock
- WebSocket / SSE push instead of polling
- Redis sorted set per RFQ for ranking
- Auth with buyer / supplier roles (suppliers shouldn't see each other's names)
