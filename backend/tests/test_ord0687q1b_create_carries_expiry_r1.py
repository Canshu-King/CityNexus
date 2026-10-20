"""Issue #33 Q1 的尾巴 -- 建人那一扇门要把它刚签发的窗口一起交出去。

上一棒给了凭据，却没给"这枚凭据到什么时候作废"。壳里 `renewSignedSessionIfShort` 的规矩是
**没被告知到期就不动**（不许拿一个自己猜的钟点去刷服务器），所以一个刚在这块屏上建好的人，
要等下一次重载或下一次建行程才会知道自己还剩多少时间 —— 在那之前服务器已经把他忘了，
屏上出现的是「登录已结束」。这一支把那个数从门里递出去，并钉住三件事：

- 交出去的窗口与令牌自己带的那一格**逐字相等**，不是"大约十五分钟"；
- 不能签的那一档，两个字段一起是 null —— 一个有、一个没有，屏上就会一半真一半猜；
- 读人的那扇门（`GET /travelers/{traveler_id}`）**不**长出这两个字段：凭据是会话的事，
  不是这个人的属性，否则任何缓存这份答复的地方都拿到了一枚能用的凭证。
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import replace
from uuid import uuid4

from fastapi.testclient import TestClient

from app import traveler_principal
from app.core.config import settings
from app.db.session import ensure_schema
from app.main import app

client = TestClient(app)
ensure_schema()

CREATE_PATH = "/api/v1/travelers"
LONG_SECRET = uuid4().hex + uuid4().hex


def _claims(token: str) -> dict:
    body = token.split(".")[0]
    raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
    return json.loads(raw)


def _create() -> tuple[int, dict, dict]:
    answer = client.post(
        CREATE_PATH,
        json={"display_name": "窗口呢", "locale": "zh-CN", "timezone": "Asia/Shanghai"},
    )
    return answer.status_code, answer.json(), dict(answer.headers)


def test_a_signed_create_hands_over_the_same_window_the_token_carries(monkeypatch) -> None:
    monkeypatch.setattr(traveler_principal, "settings", replace(settings, traveler_auth_secret=LONG_SECRET))
    status, body, headers = _create()
    assert status == 201, body
    token = body["access_token"]
    assert isinstance(token, str) and token, body
    window = body["expires_at"]
    assert isinstance(window, int) and not isinstance(window, bool), body
    # 同一个数，两处写：令牌 payload 里的 `exp` 就是答复里的 `expires_at`。
    assert _claims(token)["exp"] == window, body
    assert window > int(time.time()), "窗口必须在将来，否则壳一上手就已经过期"
    assert headers.get("cache-control") == "private, no-store", headers


def test_a_build_that_cannot_sign_says_so_in_both_fields_together(monkeypatch) -> None:
    monkeypatch.setattr(traveler_principal, "settings", replace(settings, traveler_auth_secret=None))
    status, body, _headers = _create()
    assert status == 201, body
    assert body["session_state"] != "SIGNED", body
    assert body["access_token"] is None, body
    assert "expires_at" in body, "字段得在，值是 null —— 缺席与为 null 在屏上是两件事"
    assert body["expires_at"] is None, body


def test_the_plain_read_door_grows_no_credential_and_no_window(monkeypatch) -> None:
    monkeypatch.setattr(traveler_principal, "settings", replace(settings, traveler_auth_secret=LONG_SECRET))
    _status, created, _headers = _create()
    answer = client.get("%s/%s" % (CREATE_PATH, created["id"]))
    assert answer.status_code == 200, answer.text
    shelf = answer.json()
    assert "access_token" not in shelf, shelf
    assert "expires_at" not in shelf, "这扇门答的是一个人，不是一段会话；把窗口放进来等于把凭据的一半抄进可缓存的答复"


def test_the_contract_describes_the_window_it_answers_with() -> None:
    import pathlib

    import yaml

    path = pathlib.Path(__file__).resolve().parents[2] / "contracts" / "openapi.yaml"
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    ref = spec["paths"]["/travelers"]["post"]["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
    assert ref.endswith("TravelerSessionAnswer"), ref
    answer = spec["components"]["schemas"]["TravelerSessionAnswer"]
    required = set()
    for arm in answer["allOf"]:
        required.update(arm.get("required", []))
    assert {"access_token", "session_state", "expires_at"} <= required, sorted(required)
    plain = spec["components"]["schemas"]["Traveler"]
    assert "expires_at" not in json.dumps(plain), "窗口不能长在'人'这个形状上，否则每扇读人的门都算发了会话"
