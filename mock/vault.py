# mock/vault.py
"""保险箱 mock（任务 5 的接口）：tokenize / detokenize（需权限、写审计）。"""
import secrets

from .security import mask_name, mask_phone
from .state import LOCK, STATE, iso, utc_now


def _mask_for(vtype: str, value: str) -> str:
    if vtype == "phone":
        return mask_phone(value)
    if vtype == "name":
        return mask_name(value)
    return "*" * min(len(value), 8)


def tokenize(vtype: str, value: str) -> dict:
    with LOCK:
        token = "vt_" + secrets.token_hex(12)
        STATE["vault"][token] = {
            "token": token,
            "type": vtype,
            "value": value,
            "masked": _mask_for(vtype, value),
        }
        return {"token": token, "type": vtype, "masked": STATE["vault"][token]["masked"]}


def detokenize(token: str, reason: str) -> dict | None:
    with LOCK:
        item = STATE["vault"].get(token)
        if item is None:
            return None
        STATE["audit"].append(
            {
                "token": token,
                "type": item["type"],
                "reason": reason,
                "at": iso(utc_now()),
            }
        )
        return {"token": token, "type": item["type"], "value": item["value"]}


def masked_of(token: str) -> str | None:
    item = STATE["vault"].get(token)
    return item["masked"] if item else None
