"""ORD-0443 re-check: which slot is answering now, and what does the pool say?

Written because my own earlier claim needed testing rather than repeating: the `cn:deepseek-v4-flash`
slot answered in 2.02 s at 06:1x and timed out at 120 s at 06:4x. `/healthz` + `/status` are read in
the same run so a cooldown or breaker state is visible next to the timeouts, and both realms are
probed with a bounded budget each.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

CFG = Path(r"C:\Users\仓鼠王\WorkBuddy\2026-09-15-15-47-27\wb2api\config.json")
OUT = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0443\WB2API_RECHECK.json")
GATE = "http://127.0.0.1:7863"
PROMPT = [{"role": "user", "content": "Reply with exactly one word: ok"}]
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(path: str, token: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(GATE + path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    started = time.perf_counter()
    try:
        with OPENER.open(req, timeout=timeout) as r:
            raw = r.read()
            return {"status": r.status, "bytes": len(raw),
                    "elapsed_s": round(time.perf_counter() - started, 2),
                    "x_service": r.headers.get("X-Service"), "body": raw}
    except Exception as exc:
        return {"status": "NO_RESPONSE", "error": f"{type(exc).__name__}: {exc}"[:120],
                "elapsed_s": round(time.perf_counter() - started, 2), "body": b""}


def chat(token: str, model: str, budget: int) -> dict:
    body = {"model": model, "messages": PROMPT, "max_tokens": 16, "temperature": 0, "stream": False}
    req = urllib.request.Request(GATE + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + token)
    started = time.perf_counter()
    try:
        with OPENER.open(req, timeout=budget) as r:
            raw, status = r.read(), r.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    except Exception as exc:
        return {"model": model, "status": "NO_RESPONSE", "budget_s": budget,
                "error": f"{type(exc).__name__}: {exc}"[:120],
                "elapsed_s": round(time.perf_counter() - started, 2)}
    parsed = json.loads(raw.decode("utf-8", errors="replace"))
    choice = (parsed.get("choices") or [{}])[0]
    usage = parsed.get("usage") or {}
    return {"model": model, "status": status, "bytes": len(raw), "budget_s": budget,
            "elapsed_s": round(time.perf_counter() - started, 2),
            "content_head": str((choice.get("message") or {}).get("content") or "")[:60],
            "finish_reason": choice.get("finish_reason"),
            "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")}


def main() -> int:
    token = str(json.loads(CFG.read_text(encoding="utf-8")).get("api_key") or "")
    health = get("/healthz", "", 20)
    status = get("/status", token, 30)
    pool = json.loads(status["body"].decode("utf-8", errors="replace")) if status.get("body") else {}
    accounts = [{"realm": a.get("realm"), "name_len": len(str(a.get("uid") or a.get("name") or "")),
                 "credits": a.get("credits"), "status": a.get("status"),
                 "in_flight": a.get("in_flight"), "breaker": a.get("breaker")}
                for a in (pool.get("accounts") or [])]
    rows = [chat(token, "global:glm-5.2", 45), chat(token, "cn:deepseek-v4-flash", 90),
            chat(token, "cn:glm-5.2", 45)]
    report = {"healthz": {k: v for k, v in health.items() if k != "body"},
              "status_http": {k: v for k, v in status.items() if k != "body"},
              "pool": {k: pool.get(k) for k in ("healthy", "total", "cooling", "disabled",
                                                "in_flight_full", "realm_totals")},
              "accounts": accounts, "chats": rows,
              "verdict_all_three_slots_answer": all(r.get("status") == 200 for r in rows)}
    for k in ("healthz", "status_http"):
        pass
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))
    print("pool", json.dumps(report["pool"], ensure_ascii=False)[:300])
    print("healthz", report["healthz"])
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print("WROTE", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
