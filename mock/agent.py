# mock/agent.py
"""Agent 会话 mock：7 项槽位收集、未成年终止、政策问答、站点推荐。"""
import datetime as dt
import re

from .state import (
    LOCK,
    SLOT_FIELDS,
    SLOT_TOTAL,
    STATE,
    emit_event,
    iso,
    station_public,
    utc_now,
)
from .vault import tokenize

FIELD_LABELS = dict(SLOT_FIELDS)

PROMPTS = {
    "name": {
        "reply": "先认识一下，怎么称呼您？",
        "quick_replies": [],
    },
    "birth_ym": {
        "reply": "您的出生年月是？请按 YYYY-MM 填写，例如 1998-05。",
        "quick_replies": [],
    },
    "area_text": {
        "reply": "您意向在哪个区域跑单？填到街道即可，例如「浦东新区张江镇」。",
        "quick_replies": [],
    },
    "job_type": {
        "reply": "您的岗位意向是？",
        "quick_replies": ["全职", "兼职", "还没定"],
    },
    "has_ebike": {
        "reply": "您有电动车吗？",
        "quick_replies": ["有电动车", "没有", "还没准备"],
    },
    "start_text": {
        "reply": "最快什么时候可以到岗？",
        "quick_replies": ["本周内", "两周内", "一个月内"],
    },
    "experience_text": {
        "reply": "您有多少配送经验？",
        "quick_replies": ["没做过", "1 年以内", "1-3 年"],
    },
}

POLICY_ENTRIES = [
    {
        "id": "POL-1807-01",
        "keywords": ["住宿", "宿舍", "住"],
        "answer": "部分站点提供合作宿舍，床位费按站点公示价收取，不强制入住；具体以站点现场公示为准。",
        "sources": [
            {
                "title": "站点用工政策摘要",
                "reference": "POL-1807 §3.2",
                "updated_at": "2026-06-30",
            }
        ],
    },
    {
        "id": "POL-1807-02",
        "keywords": ["工资", "结算", "发薪", "报酬"],
        "answer": "配送报酬按单结算，站点每周公示账单；本页面不承诺具体金额，签约前请与站长确认计价规则。",
        "sources": [
            {
                "title": "骑手报酬结算说明",
                "reference": "POL-1807 §4.1",
                "updated_at": "2026-07-15",
            }
        ],
    },
    {
        "id": "POL-1807-03",
        "keywords": ["体检", "健康证", "证件"],
        "answer": "配送岗位需办理健康证；可先报名预约，到站后按站点指引办理，办理周期以当地规定为准。",
        "sources": [
            {
                "title": "入职材料清单",
                "reference": "POL-1807 §2.4",
                "updated_at": "2026-05-20",
            }
        ],
    },
    {
        "id": "POL-1807-04",
        "keywords": ["合同", "签约", "保险", "协议"],
        "answer": "用工协议与保险方案在站点签约时当面确认；本服务只做信息收集与预约，不代签任何协议。",
        "sources": [
            {
                "title": "签约与保险口径",
                "reference": "POL-1807 §5.3",
                "updated_at": "2026-06-01",
            }
        ],
    },
]

POLICY_DISCLAIMER = "以上为政策摘要，不构成签约承诺；具体以站点签约口径为准。"
POLICY_QUICK = ["站点有住宿吗？", "工资怎么结算？", "转人工"]


def _progress(session: dict) -> dict:
    fields = [FIELD_LABELS[name] for name, _ in SLOT_FIELDS if name in session["slots"]]
    return {"done": len(fields), "total": SLOT_TOTAL, "fields": fields}


def _stations_card() -> dict:
    return {
        "type": "stations",
        "title": "按距离为您推荐就近站点",
        "stations": [station_public(item) for item in STATE["stations"]],
    }


def _bump_candidate(candidate: dict) -> None:
    candidate["updated_at"] = iso(utc_now())


def _event_payload(candidate: dict) -> dict:
    return {
        "candidate_id": candidate["id"],
        "status": candidate["status"],
        "source_channel": candidate["source_channel"],
        "fields_collected": [
            name for name, _ in SLOT_FIELDS if candidate.get(name) not in (None, "")
        ],
    }


def _complete_message(session: dict) -> dict:
    session["state"] = "complete"
    return {
        "reply": "7 项信息已收集完成。下面是按距离排序的站点，选一个可约时段即可预约到站。",
        "quick_replies": list(POLICY_QUICK),
        "actions": ["show_stations"],
        "card": _stations_card(),
    }


def _ask_next(session: dict) -> dict:
    if len(session["slots"]) >= SLOT_TOTAL:
        return _complete_message(session)
    field = SLOT_FIELDS[len(session["slots"])][0]
    prompt = PROMPTS[field]
    return {
        "reply": prompt["reply"],
        "quick_replies": list(prompt["quick_replies"]),
        "actions": [],
        "card": None,
    }


def _retry(session: dict, hint: str) -> dict:
    field = SLOT_FIELDS[len(session["slots"])][0]
    prompt = PROMPTS[field]
    return {
        "reply": f"{hint} {prompt['reply']}",
        "quick_replies": list(prompt["quick_replies"]),
        "actions": [],
        "card": None,
    }


def _age_at(birth_ym: str, now: dt.date) -> int:
    year, month = (int(part) for part in birth_ym.split("-"))
    age = now.year - year
    if (now.month, now.day) < (month, 1):
        age -= 1
    return age


def _store_slot(session: dict, candidate: dict, field: str, text: str) -> dict | None:
    """返回 None 表示已推进；返回 dict 表示需要重问（不推进）。"""
    text = text.strip()
    if field == "name":
        if len(text) > 20:
            return _retry(session, "称呼请控制在 20 字以内。")
        token = tokenize("name", text)
        candidate["name_token"] = token["token"]
        session["slots"]["name"] = token["masked"]
        return None

    if field == "birth_ym":
        if not re.fullmatch(r"\d{4}-\d{2}", text):
            return _retry(session, "出生年月格式不对，请按 YYYY-MM 填写。")
        age = _age_at(text, utc_now().date())
        if age < 18:
            candidate["birth_ym"] = text
            candidate["status"] = "rejected"
            _bump_candidate(candidate)
            emit_event("candidate.updated", _event_payload(candidate))
            session["state"] = "ended"
            session["end_reason"] = "end_minor"
            return {
                "reply": "抱歉，未满 18 周岁暂不能报名配送岗位，本次收集到此结束。如有疑问可拨打 400-000-1807 咨询。",
                "quick_replies": [],
                "actions": ["end_minor"],
                "card": None,
            }
        candidate["birth_ym"] = text
        session["slots"]["birth_ym"] = text
        return None

    if field == "area_text":
        if len(text) < 2:
            return _retry(session, "请填写到街道级区域，例如「浦东新区张江镇」。")
        candidate["area_text"] = text
        session["slots"]["area_text"] = text
        return None

    if field == "job_type":
        if "全职" in text or "全" in text:
            value = "fulltime"
        elif "兼职" in text or "兼" in text:
            value = "parttime"
        else:
            value = "undecided"
        candidate["job_type"] = value
        session["slots"]["job_type"] = {"fulltime": "全职", "parttime": "兼职", "undecided": "待定"}[value]
        return None

    if field == "has_ebike":
        if "没有" in text or text in {"无", "否"}:
            value = False
        elif "还没" in text or "待定" in text or "不确定" in text:
            value = None
        elif "有" in text:
            value = True
        else:
            value = None
        candidate["has_ebike"] = value
        session["slots"]["has_ebike"] = "有电动车" if value else ("没有" if value is False else "还没准备")
        return None

    if field == "start_text":
        if not text:
            return _retry(session, "请填写可到岗时间。")
        candidate["start_text"] = text
        session["slots"]["start_text"] = text
        return None

    if field == "experience_text":
        if not text:
            return _retry(session, "请填写配送经验，例如「没做过」「1-3 年」。")
        candidate["experience_text"] = text
        session["slots"]["experience_text"] = text
        return None

    return _retry(session, "这一项没有识别到，请再填一次。")


def _policy_reply(text: str) -> dict:
    if "转人工" in text or "人工" in text:
        return {
            "reply": "可以，点击下方「转人工」按钮，我会把您已填写的信息一并交接给人工客服。",
            "quick_replies": [],
            "actions": ["handoff"],
            "card": None,
        }
    for entry in POLICY_ENTRIES:
        if any(keyword in text for keyword in entry["keywords"]):
            return {
                "reply": "已为您找到相关政策摘要。",
                "quick_replies": list(POLICY_QUICK),
                "actions": [],
                "card": {
                    "type": "policy",
                    "policy_id": entry["id"],
                    "answer": entry["answer"],
                    "sources": entry["sources"],
                    "disclaimer": POLICY_DISCLAIMER,
                },
            }
    return {
        "reply": "这个问题我无法确定回答，已为您准备转人工，请点击下方「转人工」按钮。",
        "quick_replies": ["转人工"],
        "actions": ["handoff"],
        "card": None,
    }


def process_message(session: dict, text: str) -> dict:
    """处理一条用户消息；返回 reply/quick_replies/actions/card（会话状态已更新）。"""
    with LOCK:
        candidate = STATE["candidates"].get(session["candidate_id"])
        if candidate is None:
            session["state"] = "ended"
            return {
                "reply": "本次会话已结束。",
                "quick_replies": [],
                "actions": [],
                "card": None,
            }

        if session["state"] == "ended":
            return {
                "reply": "本次收集已结束，如有疑问可拨打 400-000-1807。",
                "quick_replies": [],
                "actions": [],
                "card": None,
            }
        if session["state"] == "handoff":
            return {
                "reply": "已为您转接人工，请保持电话畅通；您也可以直接拨打 400-000-1807。",
                "quick_replies": [],
                "actions": ["handoff"],
                "card": None,
            }

        if session["state"] == "complete" or len(session["slots"]) >= SLOT_TOTAL:
            return _policy_reply(text)

        field = SLOT_FIELDS[len(session["slots"])][0]
        result = _store_slot(session, candidate, field, text)
        if result is not None:
            return result

        if session["state"] == "ended":
            return {
                "reply": "抱歉，未满 18 周岁暂不能报名配送岗位，本次收集到此结束。",
                "quick_replies": [],
                "actions": ["end_minor"],
                "card": None,
            }

        _bump_candidate(candidate)
        if len(session["slots"]) >= SLOT_TOTAL:
            candidate["status"] = "complete"
            emit_event("candidate.completed", _event_payload(candidate))
            return _complete_message(session)

        candidate["status"] = "collecting"
        emit_event("candidate.updated", _event_payload(candidate))
        return _ask_next(session)


def initial_message(session: dict) -> dict:
    with LOCK:
        if len(session["slots"]) >= SLOT_TOTAL:
            return _complete_message(session)
        return _ask_next(session)
