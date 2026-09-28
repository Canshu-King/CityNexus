"""ORD-0443 read-out: what the gateway on :7863 really answers, per route.

The key is read from the gateway's own config at runtime and only ever used inside the
Authorization header - nothing here prints it, writes it, or copies it into a receipt. Values that
look like credentials anywhere in a response are replaced with their length before the receipt is
written, and the receipt path is outside the product tree.

Identity: the vendor documents `/healthz` as auth-free with a `service` field and an `X-Service`
header, so "something answered on 7863" is only "this gateway answered" when both match.
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
OUT = Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence\0443\WB2API_READOUT.json")
SECRET_KEY = re.compile(r"key|token|secret|cookie|password|authorization|credential|device", re.I)
SECRET_VAL = re.compile(r"sk-[A-Za-z0-9]|eyJ[A-Za-z0-9_.-]{8,}|Bearer\s+\S{8,}")


def redact(node):
    if isinstance(node, dict):
        return {k: ("MASKED(len=%d)" % len(str(v))) if SECRET_KEY.search(str(k)) else redact(v)
                for k, v in node.items()}
    if isinstance(node, list):
        return [redact(v) for v in node[:40]]
    if isinstance(node, str) and SECRET_VAL.search(node):
        return "MASKED(len=%d)" % len(node)
    return node


def call(method: str, path: str, token: str, body=None, timeout=20, extra=None) -> dict:
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    for k, v in (extra or {}).items():
        req.add_header(k, v)
    started = time.time()
    out = {"method": method, "path": path, "timeout_s": timeout}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as r:
            raw = r.read()
            out.update(status=r.status, bytes=len(raw),
                       elapsed_s=round(time.time() - started, 2),
                       x_service=r.headers.get("X-Service"),
                       content_type=r.headers.get("Content-Type"))
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        out.update(status=exc.code, bytes=len(raw), elapsed_s=round(time.time() - started, 2),
                   x_service=exc.headers.get("X-Service"), content_type=exc.headers.get("Content-Type"))
    except Exception as exc:
        out.update(status="NO_RESPONSE", error=f"{type(exc).__name__}: {exc}"[:140],
                   elapsed_s=round(time.time() - started, 2))
        return out
    text = raw.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text)
        out["json"] = redact(parsed)
        if isinstance(parsed, dict) and isinstance(parsed.get("data"), list):
            out["model_ids"] = sorted(str(item.get("id")) for item in parsed["data"]
                                      if isinstance(item, dict))
    except json.JSONDecodeError:
        out["body_head"] = text[:200]
    return out


def main() -> int:
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    token = str(cfg.get("api_key") or "")
    report: dict = {"config_path": str(CFG), "listen_from_config": cfg.get("listen"),
                    "api_key_present_as_field": bool(token), "api_key_length": len(token),
                    "global_chat_base_empty": cfg.get("global", {}).get("chat_base") == "",
                    "probes": {}}
    seq = [
        ("healthz_noauth", "GET", "/healthz", "", None, 15),
        ("root", "GET", "/", "", None, 15),
        ("panel", "GET", "/panel/", "", None, 15),
        ("panel_api_state", "GET", "/panel/api/state", token, None, 30),
        ("status", "GET", "/status", token, None, 30),
        ("models_fast", "GET", "/v1/models", token, None, 20),
        ("models_slow", "GET", "/v1/models", token, None, 75),
        ("models_noauth", "GET", "/v1/models", "", None, 20),
    ]
    for name, method, path, use_token, body, timeout in seq:
        report["probes"][name] = call(method, path, use_token, body, timeout)
        print(name, report["probes"][name].get("status"), report["probes"][name].get("bytes"),
              report["probes"][name].get("elapsed_s"), "s",
              "| x_service=", report["probes"][name].get("x_service"),
              "| models=", len(report["probes"][name].get("model_ids") or []))
        if report["probes"][name].get("model_ids"):
            break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print("WROTE", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
