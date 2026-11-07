"""mock 服务单测：会话/槽位/政策/站点/预约/自助/撤回/vault/outbox/错误体。"""
import hmac
import json

from mock.security import HMAC_SECRET, hmac_signature
from mock.state import STATE

CONSENT = {
    "consent_version": "v1.0",
    "consent_at": "2026-11-07T08:00:00Z",
    "source_channel": "poster_qr",
}
ANSWERS = ["王小明", "1998-05", "浦东新区张江镇", "全职", "有电动车", "本周内", "1-3 年"]


def start(client):
    consent = client.post("/api/v1/consents", json=CONSENT)
    assert consent.status_code == 201, consent.text
    candidate_id = consent.json()["candidate_id"]
    session = client.post(
        "/api/v1/agent/sessions",
        json={"candidate_id": candidate_id, "source_channel": "poster_qr"},
    )
    assert session.status_code == 201, session.text
    body = session.json()
    headers = {"Authorization": f"Bearer {body['token']}"}
    return candidate_id, body, headers


def send(client, session_id, headers, text):
    response = client.post(
        f"/api/v1/agent/sessions/{session_id}/messages",
        json={"text": text},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def complete(client, session_id, headers, count=7):
    data = None
    for text in ANSWERS[:count]:
        data = send(client, session_id, headers, text)
    return data


def test_health(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert body["ai_banner"] == "本服务由 AI 提供 · 可随时转人工"
    assert body["stations"] == 3


def test_consent_requires_version_and_time(client):
    response = client.post("/api/v1/consents", json={"consent_version": "v1.0"})
    assert response.status_code == 400
    assert response.json() == {"code": "invalid_request", "message": "请求参数不合法"}


def test_consent_records_version_time_retention(client):
    response = client.post("/api/v1/consents", json=CONSENT)
    assert response.status_code == 201
    data = response.json()
    assert data["consent_version"] == "v1.0"
    assert data["consent_at"] == "2026-11-07T08:00:00Z"
    assert data["retention_until"].startswith("2027-05-06")
    assert data["status"] == "new"


def test_session_unknown_candidate_404(client):
    response = client.post("/api/v1/agent/sessions", json={"candidate_id": "cand-missing"})
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_session_initial_prompt_and_progress(client):
    _cid, session, headers = start(client)
    view = client.get(f"/api/v1/agent/sessions/{session['session_id']}", headers=headers).json()
    assert view["progress"] == {"done": 0, "total": 7, "fields": []}
    assert "怎么称呼" in view["reply"]
    assert view["ai_banner"] == "本服务由 AI 提供 · 可随时转人工"


def test_multi_turn_collects_seven_slots(client):
    cid, session, headers = start(client)
    data = None
    for index, text in enumerate(ANSWERS, start=1):
        data = send(client, session["session_id"], headers, text)
        assert data["progress"]["done"] == index
        assert data["progress"]["total"] == 7
    assert data["progress"]["done"] == 7
    assert "show_stations" in data["actions"]
    assert data["card"]["type"] == "stations"
    assert len(data["card"]["stations"]) == 3
    candidate = client.get(f"/api/v1/candidates/{cid}", headers=headers).json()
    assert candidate["status"] == "complete"
    assert candidate["area_text"] == "浦东新区张江镇"
    assert candidate["job_type"] == "fulltime"
    assert candidate["has_ebike"] is True
    assert candidate["experience_text"] == "1-3 年"


def test_underage_returns_end_minor(client):
    cid, session, headers = start(client)
    send(client, session["session_id"], headers, "王小明")
    data = send(client, session["session_id"], headers, "2010-01")
    assert "end_minor" in data["actions"]
    assert "18 周岁" in data["reply"]
    candidate = client.get(f"/api/v1/candidates/{cid}", headers=headers).json()
    assert candidate["status"] == "rejected"


def test_invalid_birth_format_does_not_advance(client):
    _cid, session, headers = start(client)
    send(client, session["session_id"], headers, "王小明")
    data = send(client, session["session_id"], headers, "1998年5月")
    assert data["progress"]["done"] == 1
    assert "YYYY-MM" in data["reply"]


def test_policy_hit_has_sources_and_disclaimer(client):
    _cid, session, headers = start(client)
    complete(client, session["session_id"], headers)
    data = send(client, session["session_id"], headers, "站点有住宿吗？")
    assert data["card"]["type"] == "policy"
    assert data["card"]["sources"]
    assert data["card"]["sources"][0]["reference"] == "POL-1807 §3.2"
    assert "免责声明" not in data["card"]["disclaimer"]
    assert data["card"]["disclaimer"]


def test_policy_miss_returns_handoff_action(client):
    _cid, session, headers = start(client)
    complete(client, session["session_id"], headers)
    data = send(client, session["session_id"], headers, "你们老板是谁？")
    assert "handoff" in data["actions"]
    assert data["card"] is None


def test_handoff_endpoint_updates_status_and_event(client):
    _cid, session, headers = start(client)
    response = client.post(
        "/api/v1/handoff",
        json={"session_id": session["session_id"], "reason": "user_requested"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["candidate_status"] == "handoff"
    assert any(event["type"] == "handoff.requested" for event in STATE["outbox"])


def test_stations_shape(client):
    response = client.get("/api/v1/stations")
    assert response.status_code == 200
    stations = response.json()["stations"]
    assert len(stations) == 3
    for station in stations:
        assert {"id", "name", "lat", "lng", "open_quota"} <= set(station)
        assert station["slots"]


def test_booking_requires_complete_profile(client):
    _cid, session, headers = start(client)
    send(client, session["session_id"], headers, "王小明")
    station = client.get("/api/v1/stations").json()["stations"][0]
    response = client.post(
        "/api/v1/bookings",
        json={"station_id": station["id"], "slot_start": station["slots"][0]},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "incomplete_profile"


def test_booking_success_and_view(client):
    _cid, session, headers = start(client)
    complete(client, session["session_id"], headers)
    station = client.get("/api/v1/stations").json()["stations"][0]
    before = station["open_quota"]
    response = client.post(
        "/api/v1/bookings",
        json={"station_id": station["id"], "slot_start": station["slots"][0]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    view = response.json()
    assert view["booking"]["status"] == "booked"
    assert view["candidate_status"] == "booked"
    assert view["navigation"]["amap_uri"].startswith("https://uri.amap.com/")
    assert len(view["arrival_notes"]) == 3
    assert view["virtual_phone"]["tel"].startswith("tel:400")
    assert len(view["reschedule_slots"]) >= 3
    after = next(item for item in client.get("/api/v1/stations").json()["stations"] if item["id"] == station["id"])
    assert after["open_quota"] == before - 1


def test_booking_slot_unavailable(client):
    _cid, session, headers = start(client)
    complete(client, session["session_id"], headers)
    response = client.post(
        "/api/v1/bookings",
        json={"station_id": "ST-001", "slot_start": "1999-01-01 10:00"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "slot_unavailable"


def test_booking_duplicate_conflict(client):
    _cid, session, headers = start(client)
    complete(client, session["session_id"], headers)
    station = client.get("/api/v1/stations").json()["stations"][0]
    payload = {"station_id": station["id"], "slot_start": station["slots"][0]}
    assert client.post("/api/v1/bookings", json=payload, headers=headers).status_code == 201
    second = client.post("/api/v1/bookings", json=payload, headers=headers)
    assert second.status_code == 409
    assert second.json()["code"] == "already_booked"


def test_cancel_restores_quota_and_conflict(client):
    _cid, session, headers = start(client)
    complete(client, session["session_id"], headers)
    station = client.get("/api/v1/stations").json()["stations"][0]
    before = station["open_quota"]
    booking = client.post(
        "/api/v1/bookings",
        json={"station_id": station["id"], "slot_start": station["slots"][0]},
        headers=headers,
    ).json()["booking"]
    cancelled = client.post(f"/api/v1/bookings/{booking['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["booking"]["status"] == "cancelled"
    after = next(item for item in client.get("/api/v1/stations").json()["stations"] if item["id"] == station["id"])
    assert after["open_quota"] == before
    again = client.post(f"/api/v1/bookings/{booking['id']}/cancel", headers=headers)
    assert again.status_code == 409
    assert again.json()["code"] == "invalid_state"


def test_reschedule_updates_slot(client):
    _cid, session, headers = start(client)
    complete(client, session["session_id"], headers)
    station = client.get("/api/v1/stations").json()["stations"][0]
    booking = client.post(
        "/api/v1/bookings",
        json={"station_id": station["id"], "slot_start": station["slots"][0]},
        headers=headers,
    ).json()["booking"]
    new_slot = station["slots"][1]
    response = client.post(
        f"/api/v1/bookings/{booking['id']}/reschedule",
        json={"slot_start": new_slot},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["booking"]["slot_start"] == new_slot
    assert response.json()["booking"]["status"] == "booked"


def test_candidate_view_masks_and_contract_fields(client):
    cid, session, headers = start(client)
    complete(client, session["session_id"], headers)
    candidate = client.get(f"/api/v1/candidates/{cid}", headers=headers).json()
    assert candidate["name"] == "王**"
    assert candidate["phone"] == "139****0000"
    required = {
        "id", "name_token", "phone_token", "birth_ym", "area_text", "job_type", "has_ebike",
        "start_text", "experience_text", "health_cert", "source_channel", "station_id",
        "status", "consent_version", "consent_at", "retention_until", "created_at", "updated_at",
    }
    assert required <= set(candidate)


def test_patch_correction_and_event(client):
    cid, session, headers = start(client)
    complete(client, session["session_id"], headers)
    response = client.patch(
        f"/api/v1/candidates/{cid}",
        json={"area_text": "闵行区七宝镇", "job_type": "parttime"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["area_text"] == "闵行区七宝镇"
    assert any("area_text" in event["payload"].get("changed_fields", []) for event in STATE["outbox"])


def test_patch_rejects_bad_enum(client):
    cid, _session, headers = start(client)
    response = client.patch(f"/api/v1/candidates/{cid}", json={"job_type": "freelance"}, headers=headers)
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_export_copy_contains_consent(client):
    cid, session, headers = start(client)
    complete(client, session["session_id"], headers)
    response = client.get(f"/api/v1/candidates/{cid}/export", headers=headers)
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    body = json.loads(response.text)
    assert body["consent"]["version"] == "v1.0"
    assert body["candidate"]["name"] == "王**"
    assert body["generated_at"].endswith("Z")


def test_revoke_deletes_data_and_invalidates_session(client):
    cid, session, headers = start(client)
    response = client.delete(f"/api/v1/candidates/{cid}", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"deleted": True, "session_invalidated": True, "candidate_id": cid}
    expired = client.get(f"/api/v1/agent/sessions/{session['session_id']}", headers=headers)
    assert expired.status_code == 410
    assert expired.json()["code"] == "session_expired"
    gone = client.get(f"/api/v1/candidates/{cid}", headers=headers)
    assert gone.status_code == 410
    assert cid not in STATE["candidates"]


def test_vault_masks_and_requires_permission(client):
    name = client.post("/api/v1/vault/tokenize", json={"type": "name", "value": "王小明"}).json()
    phone = client.post("/api/v1/vault/tokenize", json={"type": "phone", "value": "13800138000"}).json()
    assert name["masked"] == "王**"
    assert phone["masked"] == "138****8000"

    denied = client.post("/api/v1/vault/detokenize", json={"token": name["token"], "reason": "客服核验"})
    assert denied.status_code == 403
    allowed = client.post(
        "/api/v1/vault/detokenize",
        json={"token": name["token"], "reason": "客服核验"},
        headers={"X-Vault-Permission": "vault:read", "X-Employee-Id": "EMP-001"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["value"] == "王小明"
    assert any(item["reason"].startswith("客服核验") for item in STATE["audit"])


def test_outbox_events_have_valid_hmac(client):
    _cid, session, headers = start(client)
    complete(client, session["session_id"], headers)
    station = client.get("/api/v1/stations").json()["stations"][0]
    client.post(
        "/api/v1/bookings",
        json={"station_id": station["id"], "slot_start": station["slots"][0]},
        headers=headers,
    )
    types = {event["type"] for event in STATE["outbox"]}
    assert {"candidate.created", "candidate.updated", "candidate.completed", "booking.created"} <= types
    for event in STATE["outbox"]:
        signature = event["signature"]
        expected = hmac_signature(signature["signed_body"], signature["timestamp_ms"], HMAC_SECRET)
        assert hmac.compare_digest(signature["hmac_sha256"], expected)


def test_employee_jwt_required_for_admin_outbox(client):
    assert client.get("/api/v1/admin/outbox").status_code == 401
    token = client.post("/api/v1/admin/token", json={"employee_id": "EMP-001"}).json()["access_token"]
    response = client.get("/api/v1/admin/outbox", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "events" in response.json()


def test_error_body_shape_for_unknown_route(client):
    response = client.get("/api/v1/not-exists")
    assert response.status_code == 404
    assert set(response.json().keys()) == {"code", "message"}
