# mock/app.py
"""FastAPI mock：契约 v1 的求职者端接口 + 任务 1/5 的 mock（agent / vault）。"""
import datetime as dt
import json
import uuid

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from .agent import (
    FIELD_LABELS,
    POLICY_DISCLAIMER,
    POLICY_ENTRIES,
    POLICY_QUICK,
    initial_message,
    process_message,
)
from .security import (
    VAULT_PERMISSION,
    issue_employee_jwt,
    mask_name,
    mask_phone,
    new_token,
    verify_employee_jwt,
)
from .state import (
    AI_BANNER,
    CONSENT_VERSION,
    LOCK,
    RETENTION_DAYS,
    SLOT_FIELDS,
    SLOT_TOTAL,
    STATE,
    find_active_booking,
    iso,
    new_id,
    reset_state,
    station_public,
    utc_now,
)
from .vault import detokenize, masked_of, tokenize

app = FastAPI(
    title="ClawHunt #1807 求职者端 Mock API",
    version="1.0.0",
    description="契约 v1 求职者端接口（合成数据）。Agent / 保险箱 / 大模型均为 mock。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


@app.exception_handler(ApiError)
async def api_error_handler(_request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, _exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"code": "invalid_request", "message": "请求参数不合法"},
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_request: Request, exc: StarletteHTTPException):
    code = "not_found" if exc.status_code == 404 else "http_error"
    detail = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return JSONResponse(status_code=exc.status_code, content={"code": code, "message": detail})


class ConsentIn(BaseModel):
    consent_version: str
    consent_at: str
    source_channel: str | None = None


class SessionIn(BaseModel):
    candidate_id: str
    source_channel: str | None = None


class MessageIn(BaseModel):
    text: str = Field(min_length=0, max_length=500)


class HandoffIn(BaseModel):
    session_id: str
    reason: str | None = None


class BookingIn(BaseModel):
    station_id: str
    slot_start: str


class RescheduleIn(BaseModel):
    slot_start: str


class CandidatePatch(BaseModel):
    area_text: str | None = None
    job_type: str | None = None
    start_text: str | None = None
    experience_text: str | None = None
    has_ebike: bool | None = None
    health_cert: str | None = None


class TokenizeIn(BaseModel):
    type: str
    value: str


class DetokenizeIn(BaseModel):
    token: str
    reason: str


class AdminLoginIn(BaseModel):
    employee_id: str


def _parse_iso(text: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApiError(400, "invalid_request", "consent_at 必须是 ISO-8601 时间") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError(401, "unauthorized", "缺少求职者会话令牌")
    token = authorization[len("Bearer "):].strip()
    if not token:
        raise ApiError(401, "unauthorized", "缺少求职者会话令牌")
    return token


def _require_session(session_id: str, authorization: str | None) -> dict:
    token = _bearer(authorization)
    with LOCK:
        session = STATE["sessions"].get(session_id)
        if session is None:
            raise ApiError(410, "session_expired", "会话已失效，请重新开始")
        if session["token"] != token:
            raise ApiError(401, "unauthorized", "会话令牌不匹配")
        return session


def _require_candidate(candidate_id: str, authorization: str | None) -> tuple[dict, dict]:
    token = _bearer(authorization)
    with LOCK:
        sessions = [item for item in STATE["sessions"].values() if item["candidate_id"] == candidate_id]
        if not sessions:
            raise ApiError(410, "session_expired", "会话已失效，请重新开始")
        session = sessions[0]
        if session["token"] != token:
            raise ApiError(401, "unauthorized", "会话令牌不匹配")
        candidate = STATE["candidates"].get(candidate_id)
        if candidate is None:
            raise ApiError(404, "not_found", "候选人不存在")
        return candidate, session


def _progress(session: dict) -> dict:
    fields = [FIELD_LABELS[name] for name, _ in SLOT_FIELDS if name in session["slots"]]
    return {"done": len(fields), "total": SLOT_TOTAL, "fields": fields}


def _candidate_public(candidate: dict) -> dict:
    return {
        "id": candidate["id"],
        "name_token": candidate["name_token"],
        "phone_token": candidate["phone_token"],
        "name": masked_of(candidate["name_token"]) or "**",
        "phone": masked_of(candidate["phone_token"]) or "****",
        "birth_ym": candidate["birth_ym"],
        "area_text": candidate["area_text"],
        "job_type": candidate["job_type"],
        "has_ebike": candidate["has_ebike"],
        "start_text": candidate["start_text"],
        "experience_text": candidate["experience_text"],
        "health_cert": candidate["health_cert"],
        "source_channel": candidate["source_channel"],
        "station_id": candidate["station_id"],
        "status": candidate["status"],
        "consent_version": candidate["consent_version"],
        "consent_at": candidate["consent_at"],
        "retention_until": candidate["retention_until"],
        "created_at": candidate["created_at"],
        "updated_at": candidate["updated_at"],
    }


def _message_view(session: dict, result: dict) -> dict:
    view = {
        "session_id": session["id"],
        "reply": result["reply"],
        "quick_replies": result.get("quick_replies", []),
        "progress": _progress(session),
        "actions": result.get("actions", []),
        "card": result.get("card"),
    }
    return view


def _record_ui(session: dict, result: dict, reply: str, card: dict | None) -> dict:
    session["last_ui"] = {
        "reply": reply,
        "quick_replies": result.get("quick_replies", []),
        "actions": result.get("actions", []),
        "card": card,
        "progress": _progress(session),
    }
    session["history"].append(
        {
            "role": "assistant",
            "text": reply,
            "quick_replies": result.get("quick_replies", []),
            "card": card,
            "actions": result.get("actions", []),
        }
    )
    return session["last_ui"]


def _session_view(session: dict) -> dict:
    ui = session.get("last_ui") or {
        "reply": "",
        "quick_replies": [],
        "actions": [],
        "card": None,
        "progress": _progress(session),
    }
    if session["state"] == "complete" and not ui.get("card"):
        ui = dict(ui)
        ui["card"] = {
            "type": "stations",
            "title": "按距离为您推荐就近站点",
            "stations": [station_public(item) for item in STATE["stations"]],
        }
        ui["actions"] = ["show_stations"]
    return {
        "session_id": session["id"],
        "candidate_id": session["candidate_id"],
        "state": session["state"],
        "status": STATE["candidates"].get(session["candidate_id"], {}).get("status"),
        "messages": list(session["history"]),
        "reply": ui.get("reply", ""),
        "quick_replies": ui.get("quick_replies", []),
        "progress": _progress(session),
        "actions": ui.get("actions", []),
        "card": ui.get("card"),
        "ai_banner": AI_BANNER,
        "consent_version": CONSENT_VERSION,
    }


def _station_or_404(station_id: str) -> dict:
    for station in STATE["stations"]:
        if station["id"] == station_id:
            return station
    raise ApiError(404, "not_found", "站点不存在")


def _booking_public(booking: dict) -> dict:
    return {
        "id": booking["id"],
        "candidate_id": booking["candidate_id"],
        "station_id": booking["station_id"],
        "slot_start": booking["slot_start"],
        "status": booking["status"],
    }


def _booking_view(booking: dict, candidate: dict) -> dict:
    station = _station_or_404(booking["station_id"])
    number = "40000010" + station["id"][-2:]
    return {
        "booking": _booking_public(booking),
        "station": station_public(station),
        "candidate_status": candidate["status"],
        "navigation": {
            "label": "高德地图导航",
            "amap_uri": (
                "https://uri.amap.com/marker?position="
                f"{station['lng']},{station['lat']}&name={station['name']}"
            ),
        },
        "arrival_notes": [
            "请按预约时段提前 10 分钟到站，携带本人手机。",
            "到站后在前台报预约号，由站长核验身份与健康证办理情况。",
            "如需改约或取消，请在结果页操作，或拨打站长虚拟号。",
        ],
        "virtual_phone": {"display": f"{number[:3]}-{number[3:7]}-{number[7:]}", "tel": f"tel:{number}"},
        "reschedule_slots": list(station["slots"]),
    }


@app.get("/api/v1/health")
def health():
    return {
        "status": "ok",
        "service": "clawhunt-1807-mock",
        "ai_banner": AI_BANNER,
        "consent_version": CONSENT_VERSION,
        "stations": len(STATE["stations"]),
    }


@app.post("/api/v1/_mock/reset")
def mock_reset():
    reset_state()
    return {"reset": True}


@app.get("/api/v1/_mock/outbox")
def mock_outbox():
    return {"events": list(STATE["outbox"]), "count": len(STATE["outbox"])}


@app.post("/api/v1/consents", status_code=201)
def create_consent(body: ConsentIn):
    version = body.consent_version.strip()
    if not version:
        raise ApiError(400, "invalid_request", "consent_version 不能为空")
    consent_dt = _parse_iso(body.consent_at)
    now = utc_now()
    candidate_id = new_id("cand")
    phone = tokenize("phone", "13900000000")
    with LOCK:
        candidate = {
            "id": candidate_id,
            "name_token": "",
            "phone_token": phone["token"],
            "birth_ym": None,
            "area_text": None,
            "job_type": None,
            "has_ebike": None,
            "start_text": None,
            "experience_text": None,
            "health_cert": "unknown",
            "source_channel": body.source_channel or "unknown",
            "station_id": None,
            "status": "new",
            "consent_version": version,
            "consent_at": iso(consent_dt),
            "retention_until": iso(consent_dt + dt.timedelta(days=RETENTION_DAYS)),
            "created_at": iso(now),
            "updated_at": iso(now),
        }
        STATE["candidates"][candidate_id] = candidate
    from .state import emit_event

    emit_event(
        "candidate.created",
        {
            "candidate_id": candidate_id,
            "source_channel": candidate["source_channel"],
            "consent_version": version,
            "consent_at": candidate["consent_at"],
            "retention_until": candidate["retention_until"],
            "consent_status": "granted",
        },
    )
    return {
        "candidate_id": candidate_id,
        "consent_version": version,
        "consent_at": candidate["consent_at"],
        "retention_until": candidate["retention_until"],
        "status": candidate["status"],
    }


@app.post("/api/v1/agent/sessions", status_code=201)
def create_session(body: SessionIn):
    with LOCK:
        candidate = STATE["candidates"].get(body.candidate_id)
        if candidate is None:
            raise ApiError(404, "not_found", "候选人不存在，请先完成告知同意")
        session_id = new_id("sess")
        session = {
            "id": session_id,
            "token": new_token("st_"),
            "candidate_id": body.candidate_id,
            "state": "collecting",
            "slots": {},
            "history": [],
            "last_ui": None,
            "created_at": iso(utc_now()),
        }
        STATE["sessions"][session_id] = session
        candidate["status"] = "collecting"
        candidate["updated_at"] = iso(utc_now())
        first = initial_message(session)
        session["history"].append({"role": "assistant", "text": "您好，我是骑手报名助手。"})
        _record_ui(session, first, first["reply"], first.get("card"))
        return {
            "session_id": session_id,
            "token": session["token"],
            "candidate_id": body.candidate_id,
            "reply": first["reply"],
            "ai_banner": AI_BANNER,
        }


@app.get("/api/v1/agent/sessions/{session_id}")
def get_session(session_id: str, authorization: str | None = Header(default=None)):
    session = _require_session(session_id, authorization)
    return _session_view(session)


@app.post("/api/v1/agent/sessions/{session_id}/messages")
def post_message(session_id: str, body: MessageIn, authorization: str | None = Header(default=None)):
    session = _require_session(session_id, authorization)
    text = body.text.strip()
    with LOCK:
        if text:
            session["history"].append({"role": "user", "text": text})
        result = process_message(session, text)
        _record_ui(session, result, result["reply"], result.get("card"))
        return _message_view(session, result)


@app.post("/api/v1/handoff", status_code=201)
def request_handoff(body: HandoffIn, authorization: str | None = Header(default=None)):
    session = _require_session(body.session_id, authorization)
    from .state import emit_event

    with LOCK:
        candidate = STATE["candidates"][session["candidate_id"]]
        candidate["status"] = "handoff"
        candidate["updated_at"] = iso(utc_now())
        session["state"] = "handoff"
        ticket = new_id("ticket")
        reply = "已转接人工客服，请保持电话畅通；也可直接拨打 400-000-1807。"
        result = {"reply": reply, "quick_replies": [], "actions": ["handoff"], "card": None}
        session["history"].append({"role": "assistant", "text": reply})
        _record_ui(session, result, reply, None)
        emit_event(
            "handoff.requested",
            {
                "candidate_id": candidate["id"],
                "ticket_id": ticket,
                "reason": body.reason or "user_requested",
                "status": candidate["status"],
            },
        )
    return {
        "ticket_id": ticket,
        "queue_position": 3,
        "phone": "400-000-1807",
        "candidate_status": "handoff",
    }


@app.get("/api/v1/stations")
def list_stations():
    return {"stations": [station_public(item) for item in STATE["stations"]], "count": len(STATE["stations"])}


@app.get("/api/v1/policy/entries")
def policy_entries():
    return {
        "entries": [
            {"id": item["id"], "keywords": item["keywords"], "sources": item["sources"]}
            for item in POLICY_ENTRIES
        ],
        "disclaimer": POLICY_DISCLAIMER,
        "quick_replies": POLICY_QUICK,
    }


@app.post("/api/v1/bookings", status_code=201)
def create_booking(body: BookingIn, authorization: str | None = Header(default=None)):
    token = _bearer(authorization)
    with LOCK:
        sessions = [s for s in STATE["sessions"].values() if s["token"] == token]
        if not sessions:
            raise ApiError(410, "session_expired", "会话已失效，请重新开始")
        session = sessions[0]
        candidate = STATE["candidates"].get(session["candidate_id"])
        if candidate is None:
            raise ApiError(410, "session_expired", "会话已失效，请重新开始")
        if len(session["slots"]) < SLOT_TOTAL:
            raise ApiError(400, "incomplete_profile", "7 项报名信息未收集完成，不能预约")
        station = _station_or_404(body.station_id)
        if body.slot_start not in station["slots"]:
            raise ApiError(400, "slot_unavailable", "该时段不可预约，请重新选择")
        if station["open_quota"] <= 0:
            raise ApiError(409, "quota_exhausted", "该站点名额已满")
        if find_active_booking(candidate["id"]) is not None:
            raise ApiError(409, "already_booked", "已有有效预约，请先改约或取消")

        from .state import emit_event

        booking = {
            "id": new_id("book"),
            "candidate_id": candidate["id"],
            "station_id": station["id"],
            "slot_start": body.slot_start,
            "status": "booked",
            "created_at": iso(utc_now()),
        }
        STATE["bookings"][booking["id"]] = booking
        station["open_quota"] -= 1
        candidate["station_id"] = station["id"]
        candidate["status"] = "booked"
        candidate["updated_at"] = iso(utc_now())
        emit_event(
            "booking.created",
            {
                "booking_id": booking["id"],
                "candidate_id": candidate["id"],
                "station_id": station["id"],
                "slot_start": booking["slot_start"],
                "status": "booked",
            },
        )
        emit_event("candidate.updated", {"candidate_id": candidate["id"], "status": "booked"})
        return _booking_view(booking, candidate)


@app.post("/api/v1/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: str, authorization: str | None = Header(default=None)):
    token = _bearer(authorization)
    with LOCK:
        sessions = [s for s in STATE["sessions"].values() if s["token"] == token]
        if not sessions:
            raise ApiError(410, "session_expired", "会话已失效，请重新开始")
        session = sessions[0]
        booking = STATE["bookings"].get(booking_id)
        if booking is None or booking["candidate_id"] != session["candidate_id"]:
            raise ApiError(404, "not_found", "预约不存在")
        if booking["status"] != "booked":
            raise ApiError(409, "invalid_state", "该预约已不可取消")
        from .state import emit_event

        booking["status"] = "cancelled"
        station = _station_or_404(booking["station_id"])
        station["open_quota"] += 1
        candidate = STATE["candidates"].get(booking["candidate_id"])
        if candidate is not None:
            candidate["status"] = "complete"
            candidate["station_id"] = None
            candidate["updated_at"] = iso(utc_now())
        emit_event(
            "booking.cancelled",
            {"booking_id": booking["id"], "candidate_id": booking["candidate_id"], "status": "cancelled"},
        )
        return _booking_view(booking, candidate)


@app.post("/api/v1/bookings/{booking_id}/reschedule")
def reschedule_booking(
    booking_id: str,
    body: RescheduleIn,
    authorization: str | None = Header(default=None),
):
    token = _bearer(authorization)
    with LOCK:
        sessions = [s for s in STATE["sessions"].values() if s["token"] == token]
        if not sessions:
            raise ApiError(410, "session_expired", "会话已失效，请重新开始")
        session = sessions[0]
        booking = STATE["bookings"].get(booking_id)
        if booking is None or booking["candidate_id"] != session["candidate_id"]:
            raise ApiError(404, "not_found", "预约不存在")
        if booking["status"] != "booked":
            raise ApiError(409, "invalid_state", "该预约已不可改约")
        station = _station_or_404(booking["station_id"])
        if body.slot_start not in station["slots"]:
            raise ApiError(400, "slot_unavailable", "该时段不可预约，请重新选择")
        from .state import emit_event

        booking["slot_start"] = body.slot_start
        candidate = STATE["candidates"][booking["candidate_id"]]
        emit_event(
            "booking.created",
            {
                "booking_id": booking["id"],
                "candidate_id": candidate["id"],
                "station_id": station["id"],
                "slot_start": booking["slot_start"],
                "status": "booked",
                "rescheduled": True,
            },
        )
        return _booking_view(booking, candidate)


@app.get("/api/v1/candidates/{candidate_id}")
def get_candidate(candidate_id: str, authorization: str | None = Header(default=None)):
    candidate, _session = _require_candidate(candidate_id, authorization)
    return _candidate_public(candidate)


@app.patch("/api/v1/candidates/{candidate_id}")
def patch_candidate(
    candidate_id: str,
    body: CandidatePatch,
    authorization: str | None = Header(default=None),
):
    candidate, session = _require_candidate(candidate_id, authorization)
    from .state import emit_event

    allowed = {"area_text", "job_type", "start_text", "experience_text", "has_ebike", "health_cert"}
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise ApiError(400, "invalid_request", "没有需要更正的字段")
    with LOCK:
        if "job_type" in updates and updates["job_type"] not in {"fulltime", "parttime", "undecided"}:
            raise ApiError(400, "invalid_request", "job_type 取值不合法")
        if "health_cert" in updates and updates["health_cert"] not in {
            "none", "holding", "processing", "unknown",
        }:
            raise ApiError(400, "invalid_request", "health_cert 取值不合法")
        for key, value in updates.items():
            if key in allowed:
                candidate[key] = value
                if key in session["slots"]:
                    if key == "has_ebike":
                        session["slots"][key] = "有电动车" if value else "没有"
                    elif key == "job_type":
                        session["slots"][key] = {"fulltime": "全职", "parttime": "兼职", "undecided": "待定"}[value]
                    else:
                        session["slots"][key] = value
        candidate["updated_at"] = iso(utc_now())
        emit_event(
            "candidate.updated",
            {"candidate_id": candidate["id"], "status": candidate["status"], "changed_fields": sorted(updates)},
        )
    return _candidate_public(candidate)


@app.get("/api/v1/candidates/{candidate_id}/export")
def export_candidate(candidate_id: str, authorization: str | None = Header(default=None)):
    candidate, _session = _require_candidate(candidate_id, authorization)
    with LOCK:
        bookings = [
            _booking_public(item)
            for item in STATE["bookings"].values()
            if item["candidate_id"] == candidate_id
        ]
    payload = {
        "generated_at": iso(utc_now()),
        "candidate": _candidate_public(candidate),
        "bookings": bookings,
        "consent": {
            "version": candidate["consent_version"],
            "at": candidate["consent_at"],
            "retention_until": candidate["retention_until"],
        },
        "notice": "本副本为合成演示数据；如需删除请在「我的信息」页撤回授权。",
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="candidate-{candidate_id}.json"'},
    )


@app.delete("/api/v1/candidates/{candidate_id}")
def revoke_candidate(candidate_id: str, authorization: str | None = Header(default=None)):
    token = _bearer(authorization)
    with LOCK:
        sessions = [s for s in STATE["sessions"].values() if s["token"] == token]
        if not sessions:
            raise ApiError(410, "session_expired", "会话已失效，请重新开始")
        session = sessions[0]
        if session["candidate_id"] != candidate_id:
            raise ApiError(401, "unauthorized", "会话令牌不匹配")
        candidate = STATE["candidates"].get(candidate_id)
        if candidate is None:
            raise ApiError(404, "not_found", "候选人不存在")
        STATE["candidates"].pop(candidate_id, None)
        for booking_id in [
            key for key, item in STATE["bookings"].items() if item["candidate_id"] == candidate_id
        ]:
            STATE["bookings"].pop(booking_id, None)
        for session_id in [
            key for key, item in STATE["sessions"].items() if item["candidate_id"] == candidate_id
        ]:
            STATE["sessions"].pop(session_id, None)
    return {"deleted": True, "session_invalidated": True, "candidate_id": candidate_id}


@app.post("/api/v1/vault/tokenize", status_code=201)
def vault_tokenize(body: TokenizeIn):
    if body.type not in {"name", "phone"}:
        raise ApiError(400, "invalid_request", "type 仅支持 name / phone")
    value = body.value.strip()
    if not value:
        raise ApiError(400, "invalid_request", "value 不能为空")
    item = tokenize(body.type, value)
    return item


@app.post("/api/v1/vault/detokenize")
def vault_detokenize(
    body: DetokenizeIn,
    x_vault_permission: str | None = Header(default=None),
    x_employee_id: str | None = Header(default=None),
):
    if x_vault_permission != VAULT_PERMISSION:
        raise ApiError(403, "forbidden", "缺少保险箱解盲权限")
    reason = body.reason.strip()
    if not reason:
        raise ApiError(400, "invalid_request", "解盲必须填写理由")
    item = detokenize(body.token, f"{reason} | by:{x_employee_id or 'unknown'}")
    if item is None:
        raise ApiError(404, "not_found", "token 不存在")
    return item


@app.post("/api/v1/admin/token")
def admin_token(body: AdminLoginIn):
    return {
        "access_token": issue_employee_jwt(body.employee_id),
        "token_type": "bearer",
        "expires_in": 3600,
    }


@app.get("/api/v1/admin/outbox")
def admin_outbox(authorization: str | None = Header(default=None)):
    token = _bearer(authorization)
    payload = verify_employee_jwt(token)
    if payload is None:
        raise ApiError(401, "unauthorized", "员工端需要有效 Bearer JWT")
    return {"events": list(STATE["outbox"]), "count": len(STATE["outbox"])}
