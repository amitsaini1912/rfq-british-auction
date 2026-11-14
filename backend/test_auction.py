import os
from datetime import datetime, timedelta, timezone

os.environ["DB_PATH"] = "test.db"
if os.path.exists("test.db"):
    os.remove("test.db")

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)
n = 0


def make_rfq(close_in=5, forced_in=8, x=10, y=5, trigger="BID"):
    global n
    n += 1
    t = datetime.now(timezone.utc)
    r = client.post("/api/rfqs", json={
        "ref_id": f"RFQ-{n}", "name": "Test lane",
        "bid_start": (t - timedelta(minutes=1)).isoformat(),
        "bid_close": (t + timedelta(minutes=close_in)).isoformat(),
        "forced_close": (t + timedelta(minutes=forced_in)).isoformat(),
        "pickup_date": (t + timedelta(days=3)).isoformat(),
        "trigger_window": x, "extension_minutes": y, "trigger_type": trigger,
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def bid(rfq_id, carrier, freight):
    return client.post(f"/api/rfqs/{rfq_id}/bids", json={
        "carrier_name": carrier, "freight_charges": freight, "origin_charges": 0,
        "destination_charges": 0, "transit_days": 4, "quote_validity": "2026-12-31",
    })


def test_forced_close_must_be_after_close():
    t = datetime.now(timezone.utc)
    r = client.post("/api/rfqs", json={
        "ref_id": "BAD", "name": "x", "bid_start": t.isoformat(),
        "bid_close": (t + timedelta(hours=2)).isoformat(),
        "forced_close": (t + timedelta(hours=1)).isoformat(),
        "pickup_date": t.isoformat(), "trigger_window": 5, "extension_minutes": 5,
        "trigger_type": "BID",
    })
    assert r.status_code == 422


def test_bid_in_window_extends_but_caps_at_forced():
    rid = make_rfq(close_in=5, forced_in=8)
    assert bid(rid, "A", 100).json()["extended"]
    rfq = client.get(f"/api/rfqs/{rid}").json()["rfq"]
    assert rfq["bid_close"] == rfq["forced_close"]  # +5 would pass forced, so capped
    assert not bid(rid, "B", 90).json()["extended"]


def test_no_extension_outside_window():
    rid = make_rfq(close_in=30, forced_in=60, x=10)
    assert not bid(rid, "A", 100).json()["extended"]


def test_l1_trigger_only_on_new_lowest():
    rid = make_rfq(close_in=5, forced_in=120, x=60, trigger="L1_RANK")
    assert bid(rid, "A", 100).json()["extended"]  # first bid is a new L1
    assert not bid(rid, "B", 120).json()["extended"]  # B is L2, L1 unchanged
    assert bid(rid, "B", 95).json()["extended"]  # B takes L1


def test_rank_trigger():
    rid = make_rfq(close_in=5, forced_in=120, x=60, trigger="ANY_RANK")
    bid(rid, "A", 100)
    bid(rid, "B", 120)
    bid(rid, "C", 130)
    assert not bid(rid, "C", 125).json()["extended"]  # still L3
    assert bid(rid, "C", 110).json()["extended"]  # C passes B


def test_bid_must_beat_own_previous():
    rid = make_rfq(close_in=30, forced_in=60)
    bid(rid, "A", 100)
    assert bid(rid, "A", 100).status_code == 400


def test_ranking():
    rid = make_rfq(close_in=30, forced_in=60)
    bid(rid, "A", 100)
    bid(rid, "B", 80)
    bid(rid, "A", 70)
    ranks = client.get(f"/api/rfqs/{rid}").json()["ranking"]
    assert [(r["carrier_name"], r["rank"]) for r in ranks] == [("A", "L1"), ("B", "L2")]
