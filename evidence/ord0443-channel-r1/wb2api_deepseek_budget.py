"""ORD-0443: does `cn:deepseek-v4-flash` answer when it is given a real token budget?

The first attempt at this measurement crashed before the request went out, so the claim "with a
larger budget it answers" had no artifact behind it. This is that artifact: max_tokens 1 vs 16, same
prompt, same slot, statuses/bytes/seconds and the reasoning-token split recorded. No credential is
written anywhere.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

CFG = Path(r"C:\Users\仓鼠王\WorkBuddy\2026-09-15-15-47-27\wb2api\config.json")
OUT = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0443\WB2API_DEEPSEEK_16TOK.json")
PROMPT = [{"role": "user", "content": "Reply with exactly one word: ok"}]


def call(token: str, max_tokens: int) -> dict:
    body = {"model": "cn:deepseek-v4-flash", "messages": PROMPT, "max_tokens": max_tokens,
            "temperature": 0, "stream": False}
    req = urllib.request.Request("http://127.0.0.1:7863/v1/chat/completions",
                                 data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + token)
    started = time.perf_counter()
    out: dict = {"max_tokens": max_tokens}
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=120) as r:
            raw, status = r.read(), r.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    except Exception as exc:
        out.update(status="NO_RESPONSE", error=f"{type(exc).__name__}: {exc}"[:160])
        return out
    usage = (json.loads(raw.decode("utf-8", errors="replace")) or {}).get("usage") or {}
    out.update(status=status, bytes=len(raw), elapsed_s=round(time.perf_counter() - started, 2),
               content_head=str(((json.loads(raw.decode("utf-8", errors="replace"))
                                  .get("choices") or [{}])[0].get("message") or {}).get("content") or "")[:80],
               completion_tokens=usage.get("completion_tokens"),
               reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"))
    return out


def main() -> int:
    token = str(json.loads(CFG.read_text(encoding="utf-8")).get("api_key") or "")
    rows = [call(token, n) for n in (1, 16)]
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    report = {"model": "cn:deepseek-v4-flash", "rows": rows,
              "verdict_empty_content_is_a_budget_artifact": bool(
                  rows[0].get("content_head") == "" and rows[0].get("reasoning_tokens")
                  and rows[1].get("status") == 200 and bool(rows[1].get("content_head")))}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print("verdict", report["verdict_empty_content_is_a_budget_artifact"], "| WROTE", OUT)
    return 0 if report["verdict_empty_content_is_a_budget_artifact"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
