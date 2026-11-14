import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "auction.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS rfqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    bid_start TEXT NOT NULL,
    original_close TEXT NOT NULL,
    bid_close TEXT NOT NULL,          -- current close, moves on extension
    forced_close TEXT NOT NULL,
    pickup_date TEXT NOT NULL,
    trigger_window INTEGER NOT NULL,  -- X minutes
    extension_minutes INTEGER NOT NULL, -- Y minutes
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('BID', 'ANY_RANK', 'L1_RANK')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rfq_id INTEGER NOT NULL REFERENCES rfqs(id),
    carrier_name TEXT NOT NULL,
    freight_charges REAL NOT NULL,
    origin_charges REAL NOT NULL,
    destination_charges REAL NOT NULL,
    total REAL NOT NULL,
    transit_days INTEGER NOT NULL,
    quote_validity TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bids_rfq ON bids(rfq_id, carrier_name);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rfq_id INTEGER NOT NULL REFERENCES rfqs(id),
    event TEXT NOT NULL,              -- RFQ_CREATED / BID / EXTENSION
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.close()
