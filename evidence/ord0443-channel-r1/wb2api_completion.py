"""ORD-0443 minimal completion: one real round trip per realm, costed in bytes and seconds.

The model ids come from the gateway's own /v1/models read-out (`wb2api_readout.py`), not from the
order's wording - which mattered: what this gateway actually exposes is `cn:deepseek-*` and GLM in
both realms, not "international deepseek / domestic GLM".

The key is read from config.json at runtime, used only in the Authorization header, and never
written to the receipt. 429 handling: after a rate-limited answer the same prompt is retried once
against the gateway's other realm slot so the two status codes sit side by side in one receipt.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

CFG = Path(r"C:\Users\仓鼠王\WorkBuddy\2026-09-15-15-47-27\wb2api\config.json")
BASE = "http://127.0.0.1:7863"
OUT = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0443\WB2API_COMPLETION.json")
SECRET_VAL = re.compile(r"sk-[A-Za-z0-9]|eyJ[A-Za-z0-9_.-]{8,}")
PROMPT = [{"role": "user", "content": "Reply with exactly one word: ok"}]


def complete(token: str, model: str, timeout: int = 90) -> dict:
    body = {"model": model, "messages": PROMPT, "max_tokens": 1, "temperature": 0, "stream": False}
    req = urllib.request.Request(BASE + "/v1/chat/completions",
                                 data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + token)
    started = time.time()
    out = {"model": model, "timeout_s": timeout}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as r:
            raw = r.read()
            out.update(status=r.status, bytes=len(raw), elapsed_s=round(time.time() - started, 2))
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        out.update(status=exc.code, bytes=len(raw), elapsed_s=round(time.time() - started, 2))
    except Exception as exc:
        out.update(status="NO_RESPONSE", error=f"{type(exc).__name__}: {exc}"[:160],
                   elapsed_s=round(time.time() - started, 2))
        return out
    text = raw.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text)
        choice = (parsed.get("choices") or [{}])[0]
        out["finish_reason"] = choice.get("finish_reason")
        content = str((choice.get("message") or {}).get("content") or "")[:80]
        out["content_head"] = SECRET_VAL.sub("MASKED", content)
        out["usage"] = parsed.get("usage")
    except json.JSONDecodeError:
        out["body_head"] = SECRET_VAL.sub("MASKED", text[:160])
    return out


def main() -> int:
    token = str(json.loads(CFG.read_text(encoding="utf-8")).get("api_key") or "")
    report: dict = {"attempts": []}
    for model in ("cn:deepseek-v4-flash", "global:glm-5.2", "cn:glm-5.2"):
        first = complete(token, model)
        report["attempts"].append(first)
        print(model, "->", first.get("status"), first.get("bytes"), "B", first.get("elapsed_s"), "s",
              "|", first.get("content_head") or first.get("error") or first.get("body_head"))
        if first.get("status") == 429:
            other = complete(token, "global:glm-5.2" if model != "global:glm-5.2" else "cn:glm-5.2")
            other["note"] = "paired second status code after a 429"
            report["attempts"].append(other)
            print("   retry ->", other.get("status"), other.get("bytes"), "B", other.get("elapsed_s"), "s")
    statuses = [a.get("status") for a in report["attempts"]]
    report["summary"] = {"statuses": statuses, "any_ok": 200 in statuses, "any_429": 429 in statuses}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print("WROTE", OUT)
    return 0 if 200 in statuses else 1


if __name__ == "__main__":
    raise SystemExit(main())
