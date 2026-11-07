# mock/state.py
"""内存态数据仓（本单允许内存/SQLite；这里用进程内内存，重启即重置）。"""
import datetime as dt
import json
import threading
import uuid
from typing import Any

from .security import HMAC_SECRET, hmac_signature

LOCK = threading.RLock()

CONSENT_VERSION = "v1.0"
RETENTION_DAYS = 180
AI_BANNER = "本服务由 AI 提供 · 可随时转人工"

SLOT_FIELDS = [
    ("name", "称呼"),
    ("birth_ym", "出生年月"),
    ("area_text", "意向区域"),
    ("job_type", "岗位意向"),
    ("has_ebike", "车辆"),
    ("start_text", "到岗时间"),
    ("experience_text", "配送经验"),
]
SLOT_TOTAL = len(SLOT_FIELDS)

JOB_TYPES = {"全职": "fulltime", "兼职": "parttime", "待定": "undecided"}
HEALTH_CERTS = {"none", "holding", "processing", "unknown"}
CANDIDATE_STATUS = {
    "new", "collecting", "complete", "booked",
    "interviewed", "hired", "rejected", "handoff",
}

STATE: dict[str, Any] = {
    "candidates": {},
    "sessions": {},
    "stations": [],
    "bookings": {},
    "outbox": [],
    "vault": {},
    "audit": [],
}


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(dt_obj: dt.datetime) -> str:
    return dt_obj.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _slots_for_day(day: dt.date) -> list[str]:
    return [f"{day.isoformat()} 10:00", f"{day.isoformat()} 14:00", f"{day.isoformat()} 16:00"]


def seed_stations() -> list[dict]:
    today = utc_now().date()
    return [
        {
            "id": "ST-001",
            "name": "张江配送站",
            "lat": 31.2034,
            "lng": 121.5890,
            "open_quota": 8,
            "distance_km": 1.2,
            "slots": _slots_for_day(today + dt.timedelta(days=1))
            + _slots_for_day(today + dt.timedelta(days=2)),
        },
        {
            "id": "ST-002",
            "name": "金桥配送站",
            "lat": 31.2570,
            "lng": 121.5910,
            "open_quota": 5,
            "distance_km": 3.4,
            "slots": _slots_for_day(today + dt.timedelta(days=2))
            + _slots_for_day(today + dt.timedelta(days=3)),
        },
        {
            "id": "ST-003",
            "name": "川沙配送站",
            "lat": 31.1850,
            "lng": 121.7010,
            "open_quota": 12,
            "distance_km": 6.8,
            "slots": _slots_for_day(today + dt.timedelta(days=3))
            + _slots_for_day(today + dt.timedelta(days=4)),
        },
    ]


def reset_state() -> None:
    with LOCK:
        STATE["candidates"].clear()
        STATE["sessions"].clear()
        STATE["bookings"].clear()
        STATE["outbox"].clear()
        STATE["vault"].clear()
        STATE["audit"].clear()
        STATE["stations"] = seed_stations()


def emit_event(event_type: str, payload: dict) -> dict:
    """outbox + Webhook 事件：HMAC-SHA256 签名（secret 固定，测试可复算）。"""
    with LOCK:
        timestamp_ms = int(utc_now().timestamp() * 1000)
        event = {
            "id": new_id("evt"),
            "type": event_type,
            "occurred_at": iso(utc_now()),
            "payload": payload,
        }
        body = json.dumps(event, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        event["signature"] = {
            "algorithm": "HMAC-SHA256",
            "timestamp_ms": timestamp_ms,
            "secret_hint": "mock-secret",
            "hmac_sha256": hmac_signature(body, timestamp_ms, HMAC_SECRET),
            "signed_body": body,
        }
        STATE["outbox"].append(event)
        return event


def find_active_booking(candidate_id: str) -> dict | None:
    for booking in STATE["bookings"].values():
        if booking["candidate_id"] == candidate_id and booking["status"] == "booked":
            return booking
    return None


def station_public(station: dict) -> dict:
    return {
        "id": station["id"],
        "name": station["name"],
        "lat": station["lat"],
        "lng": station["lng"],
        "open_quota": station["open_quota"],
        "distance_km": station["distance_km"],
        "slots": list(station["slots"]),
    }


reset_state()
