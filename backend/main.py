from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from db import get_conn, init_db

app = FastAPI(title="RFQ British Auction")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
init_db()

FMT = "%Y-%m-%dT%H:%M:%SZ"


def now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime(FMT)


def parse(s):
    return datetime.strptime(s, FMT).replace(tzinfo=timezone.utc)


class RFQIn(BaseModel):
    ref_id: str
    name: str
    bid_start: datetime
    bid_close: datetime
    forced_close: datetime
    pickup_date: datetime
    trigger_window: int = Field(gt=0)
    extension_minutes: int = Field(gt=0)
    trigger_type: Literal["BID", "ANY_RANK", "L1_RANK"]

    @model_validator(mode="after")
    def check_times(self):
        if self.bid_close <= self.bid_start:
            raise ValueError("Bid close time must be after bid start time")
        if self.forced_close <= self.bid_close:
            raise ValueError("Forced close time must be after bid close time")
        return self


class BidIn(BaseModel):
    carrier_name: str = Field(min_length=1)
    freight_charges: float = Field(ge=0)
    origin_charges: float = Field(ge=0)
    destination_charges: float = Field(ge=0)
    transit_days: int = Field(gt=0)
    quote_validity: str


def status_of(rfq, t=None):
    t = t or now()
    if t < parse(rfq["bid_start"]):
        return "Upcoming"
    if t <= parse(rfq["bid_close"]):
        return "Active"
    # if the close time got pushed all the way to forced close, call it force closed
    return "Force Closed" if rfq["bid_close"] == rfq["forced_close"] else "Closed"


def ranking(conn, rfq_id):
    """Each carrier's best (lowest) bid, sorted. Ties go to whoever bid first."""
    rows = conn.execute(
        """SELECT b.* FROM bids b
           JOIN (SELECT carrier_name, MIN(total) AS best FROM bids
                 WHERE rfq_id = ? GROUP BY carrier_name) m
             ON b.carrier_name = m.carrier_name AND b.total = m.best
           WHERE b.rfq_id = ?
           ORDER BY b.total, b.created_at""",
        (rfq_id, rfq_id),
    ).fetchall()
    seen, result = set(), []
    for r in rows:
        if r["carrier_name"] not in seen:
            seen.add(r["carrier_name"])
            result.append(dict(r))
    return result


def log(conn, rfq_id, event, msg, t=None):
    conn.execute(
        "INSERT INTO activity_log (rfq_id, event, message, created_at) VALUES (?, ?, ?, ?)",
        (rfq_id, event, msg, iso(t or now())),
    )


def get_rfq_or_404(conn, rfq_id):
    rfq = conn.execute("SELECT * FROM rfqs WHERE id = ?", (rfq_id,)).fetchone()
    if not rfq:
        raise HTTPException(404, "RFQ not found")
    return rfq


@app.post("/api/rfqs", status_code=201)
def create_rfq(body: RFQIn):
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO rfqs (ref_id, name, bid_start, original_close, bid_close, forced_close,
               pickup_date, trigger_window, extension_minutes, trigger_type, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (body.ref_id, body.name, iso(body.bid_start), iso(body.bid_close), iso(body.bid_close),
             iso(body.forced_close), iso(body.pickup_date), body.trigger_window,
             body.extension_minutes, body.trigger_type, iso(now())),
        )
    except Exception:
        raise HTTPException(400, "RFQ reference id already exists")
    log(conn, cur.lastrowid, "RFQ_CREATED", f"RFQ {body.ref_id} created")
    return {"id": cur.lastrowid}


@app.get("/api/rfqs")
def list_rfqs():
    conn = get_conn()
    out = []
    for r in conn.execute("SELECT * FROM rfqs ORDER BY id DESC").fetchall():
        low = conn.execute("SELECT MIN(total) FROM bids WHERE rfq_id = ?", (r["id"],)).fetchone()[0]
        out.append({**dict(r), "lowest_bid": low, "status": status_of(r)})
    return out


@app.get("/api/rfqs/{rfq_id}")
def rfq_details(rfq_id: int):
    conn = get_conn()
    rfq = get_rfq_or_404(conn, rfq_id)
    ranks = ranking(conn, rfq_id)
    for i, b in enumerate(ranks):
        b["rank"] = f"L{i + 1}"
    bids = conn.execute(
        "SELECT * FROM bids WHERE rfq_id = ? ORDER BY total, created_at", (rfq_id,)
    ).fetchall()
    logs = conn.execute(
        "SELECT * FROM activity_log WHERE rfq_id = ? ORDER BY id DESC", (rfq_id,)
    ).fetchall()
    return {
        "rfq": {**dict(rfq), "status": status_of(rfq)},
        "ranking": ranks,
        "bids": [dict(b) for b in bids],
        "activity": [dict(l) for l in logs],
    }


@app.post("/api/rfqs/{rfq_id}/bids", status_code=201)
def place_bid(rfq_id: int, body: BidIn):
    conn = get_conn()
    # BEGIN IMMEDIATE takes the write lock, so two bids near the end can't both read
    # the old close time / ranking and race each other
    conn.execute("BEGIN IMMEDIATE")
    try:
        rfq = get_rfq_or_404(conn, rfq_id)
        t = now()
        st = status_of(rfq, t)
        if st != "Active":
            raise HTTPException(400, f"Auction is {st.lower()}, bids not accepted")

        total = round(body.freight_charges + body.origin_charges + body.destination_charges, 2)
        prev = conn.execute(
            "SELECT MIN(total) FROM bids WHERE rfq_id = ? AND carrier_name = ?",
            (rfq_id, body.carrier_name),
        ).fetchone()[0]
        if prev is not None and total >= prev:
            raise HTTPException(400, f"New bid must be lower than your previous best ({prev})")

        before = [b["carrier_name"] for b in ranking(conn, rfq_id)]
        conn.execute(
            """INSERT INTO bids (rfq_id, carrier_name, freight_charges, origin_charges,
               destination_charges, total, transit_days, quote_validity, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rfq_id, body.carrier_name, body.freight_charges, body.origin_charges,
             body.destination_charges, total, body.transit_days, body.quote_validity, iso(t)),
        )
        after = [b["carrier_name"] for b in ranking(conn, rfq_id)]
        log(conn, rfq_id, "BID", f"{body.carrier_name} bid {total} (rank L{after.index(body.carrier_name) + 1})", t)

        extended = maybe_extend(conn, rfq, before, after, t)
        conn.execute("COMMIT")
        return {"total": total, "extended": extended}
    except Exception:
        conn.execute("ROLLBACK")
        raise


def maybe_extend(conn, rfq, before, after, t):
    close = parse(rfq["bid_close"])
    forced = parse(rfq["forced_close"])
    if t < close - timedelta(minutes=rfq["trigger_window"]):
        return False  # not inside the trigger window

    kind = rfq["trigger_type"]
    reason = None
    if kind == "BID":
        reason = f"Bid received in last {rfq['trigger_window']} min"
    elif kind == "ANY_RANK" and before != after:
        reason = "Supplier ranking changed in trigger window"
    elif kind == "L1_RANK" and (not before or before[0] != after[0]):
        reason = f"New L1: {after[0]}"
    if not reason:
        return False

    if close >= forced:
        log(conn, rfq["id"], "EXTENSION", f"{reason}, but already at forced close - no extension", t)
        return False

    new_close = min(close + timedelta(minutes=rfq["extension_minutes"]), forced)
    conn.execute("UPDATE rfqs SET bid_close = ? WHERE id = ?", (iso(new_close), rfq["id"]))
    capped = " (capped at forced close)" if new_close == forced else ""
    log(conn, rfq["id"], "EXTENSION",
        f"{reason}. Close time {iso(close)} -> {iso(new_close)}{capped}", t)
    return True
