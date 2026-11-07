"""契约 v1 测试：OpenAPI 路径/字段、错误体、docs 快照同步。"""
import json
from pathlib import Path

from mock.app import app
from mock.state import STATE

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PATHS = {
    "/api/v1/health",
    "/api/v1/consents",
    "/api/v1/agent/sessions",
    "/api/v1/agent/sessions/{session_id}/messages",
    "/api/v1/handoff",
    "/api/v1/stations",
    "/api/v1/bookings",
    "/api/v1/bookings/{booking_id}/cancel",
    "/api/v1/candidates/{candidate_id}",
    "/api/v1/candidates/{candidate_id}/export",
    "/api/v1/vault/tokenize",
    "/api/v1/vault/detokenize",
}

CONTRACT_CANDIDATE_FIELDS = {
    "id", "name_token", "phone_token", "birth_ym", "area_text", "job_type", "has_ebike",
    "start_text", "experience_text", "health_cert", "source_channel", "station_id",
    "status", "consent_version", "consent_at", "retention_until", "created_at", "updated_at",
}

CONTRACT_STATION_FIELDS = {"id", "name", "lat", "lng", "open_quota"}
CONTRACT_BOOKING_FIELDS = {"id", "candidate_id", "station_id", "slot_start", "status"}


def test_openapi_json_is_served(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["info"]["version"] == "1.0.0"
    assert len(spec["paths"]) >= len(REQUIRED_PATHS)


def test_openapi_contract_paths_present(client):
    spec = client.get("/openapi.json").json()
    missing = REQUIRED_PATHS - set(spec["paths"].keys())
    assert not missing, f"缺少契约路径: {sorted(missing)}"


def test_all_paths_use_v1_prefix(client):
    spec = client.get("/openapi.json").json()
    for path in spec["paths"]:
        assert path.startswith("/api/v1/"), path


def test_candidate_contract_fields_runtime(client):
    consent = client.post(
        "/api/v1/consents",
        json={"consent_version": "v1.0", "consent_at": "2026-11-07T09:30:00+08:00", "source_channel": "poster_qr"},
    ).json()
    session = client.post(
        "/api/v1/agent/sessions", json={"candidate_id": consent["candidate_id"]}
    ).json()
    headers = {"Authorization": f"Bearer {session['token']}"}
    candidate = client.get(f"/api/v1/candidates/{consent['candidate_id']}", headers=headers).json()
    assert CONTRACT_CANDIDATE_FIELDS <= set(candidate)
    assert candidate["source_channel"] == "poster_qr"
    assert candidate["consent_version"] == consent["consent_version"]
    assert candidate["consent_at"] == consent["consent_at"]
    assert set(candidate["status"] for _ in [0]) <= {
        "new", "collecting", "complete", "booked", "interviewed", "hired", "rejected", "handoff",
    }


def test_station_and_booking_contract_fields(client):
    stations = client.get("/api/v1/stations").json()["stations"]
    for station in stations:
        assert CONTRACT_STATION_FIELDS <= set(station)
    candidate_id = client.post(
        "/api/v1/consents",
        json={"consent_version": "v1.0", "consent_at": "2026-11-07T01:00:00Z", "source_channel": "poster_qr"},
    ).json()["candidate_id"]
    session = client.post("/api/v1/agent/sessions", json={"candidate_id": candidate_id}).json()
    headers = {"Authorization": f"Bearer {session['token']}"}
    for text in ["王小明", "1998-05", "浦东新区张江镇", "全职", "有电动车", "本周内", "1-3 年"]:
        client.post(
            f"/api/v1/agent/sessions/{session['session_id']}/messages",
            json={"text": text},
            headers=headers,
        )
    station = stations[0]
    view = client.post(
        "/api/v1/bookings",
        json={"station_id": station["id"], "slot_start": station["slots"][0]},
        headers=headers,
    ).json()
    assert CONTRACT_BOOKING_FIELDS <= set(view["booking"])


def test_agent_message_contract_shape(client):
    candidate_id = client.post(
        "/api/v1/consents",
        json={"consent_version": "v1.0", "consent_at": "2026-11-07T01:00:00Z", "source_channel": "poster_qr"},
    ).json()["candidate_id"]
    session = client.post("/api/v1/agent/sessions", json={"candidate_id": candidate_id}).json()
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = client.post(
        f"/api/v1/agent/sessions/{session['session_id']}/messages",
        json={"text": "王小明"},
        headers=headers,
    ).json()
    assert {"reply", "quick_replies", "progress", "actions"} <= set(response)
    assert set(response["progress"].keys()) == {"done", "total", "fields"}
    assert set(response["actions"]) <= {"show_stations", "booking_confirmed", "handoff", "end_minor"}


def test_error_envelope_shape_everywhere(client):
    missing_auth = client.get("/api/v1/agent/sessions/sess-missing")
    assert missing_auth.status_code == 401
    assert set(missing_auth.json()) == {"code", "message"}

    invalid = client.post("/api/v1/consents", json={})
    assert invalid.status_code == 400
    assert set(invalid.json()) == {"code", "message"}

    unknown = client.get("/api/v1/stations/ST-404")
    assert unknown.status_code == 404
    assert set(unknown.json()) == {"code", "message"}


def test_contract_events_enum():
    from mock.state import emit_event

    payload = {"candidate_id": "cand-demo"}
    for event_type in [
        "candidate.created", "candidate.updated", "candidate.completed",
        "booking.created", "booking.cancelled", "handoff.requested",
    ]:
        event = emit_event(event_type, payload)
        assert event["type"] == event_type
        assert event["signature"]["algorithm"] == "HMAC-SHA256"


def test_docs_openapi_snapshot_in_sync(client):
    snapshot = ROOT / "docs" / "openapi.json"
    assert snapshot.exists(), "缺少 docs/openapi.json（先跑 python scripts/export_openapi.py）"
    assert json.loads(snapshot.read_text(encoding="utf-8")) == app.openapi()
