"""ORD-0685 验收：那扇「当前签名查看者是谁」的门，真发 HTTP 问一遍。

我自己起一台一次性后端（:8012，一次性库 `_cmdr0685*.db`），只测这扇门，不碰 :8000/:8011/:4781/:4782/:8693。
两档环境：
  A 档 不配 secret —— 期望它拒，而且拒得有名有姓（绝不"什么都收"）；
  B 档 配 secret（随机生成，只在进程环境里，不落盘、不打印）—— 期望：
        无凭证 → 401 TRAVELER_CREDENTIALS_MISSING
        合法 token → 200 回出签发时那个 traveler_id，且带 private/no-store
        篡改 token → 401 TRAVELER_CREDENTIALS_INVALID
        过期 token → 401 TRAVELER_CREDENTIALS_EXPIRED
        未知 traveler → 401 TRAVELER_PRINCIPAL_NOT_FOUND

密钥值不进任何输出：只打印路径与字段名（常设红线）。
"""
import base64
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(HERE, "tip", "backend")
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
PORT = 8012
BASE = "http://127.0.0.1:%d" % PORT
OUT = os.path.join(HERE, "ord0685_acceptance.json")


def start(env_extra, db):
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_DATABASE_URL": "sqlite:///./%s" % db,
        "CITYNEXUS_AI_ENABLED": "false",
        "PYTHONIOENCODING": "utf-8",
    })
    env.pop("CITYNEXUS_TRAVELER_AUTH_SECRET", None)
    env.update(env_extra)
    log = open(os.path.join(HERE, "ord0685_server_%s.log" % ("A" if not env_extra else "B")), "ab")
    proc = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=BACKEND, env=env, stdout=log, stderr=log,
    )
    for _ in range(90):
        try:
            with urllib.request.urlopen(BASE + "/api/v1/health", timeout=3) as r:
                if r.status == 200:
                    return proc, env
        except Exception:
            time.sleep(1)
    raise SystemExit("ABORT: the throwaway backend never answered health on :%d" % PORT)


def hdr(hdrs, name):
    """HTTP/1.1 hands these back lower-cased; a case-sensitive lookup reads a
    present header as missing (that false red cost one full run of this matrix)."""
    for k, v in (hdrs or {}).items():
        if k.lower() == name.lower():
            return v
    return ""


def call(method, path, headers=None, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data, timeout=30) as r:
            return r.status, json.loads(r.read().decode()), dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw), dict(e.headers)
        except Exception:
            return e.code, {"raw": raw[:200]}, dict(e.headers)
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, {"err": str(e)[:200]}, {}


def mint(env, traveler_id, ttl=600, now=None):
    """Ask the server's own code to sign a principal, in the same environment."""
    code = ("import os,sys;sys.path.insert(0,os.getcwd());"
            "from app.traveler_principal import issue_traveler_token;"
            "print(issue_traveler_token(sys.argv[1], ttl_seconds=int(sys.argv[2]),"
            " now=(None if sys.argv[3]=='-' else int(sys.argv[3]))))")
    r = subprocess.run([PY, "-c", code, traveler_id, str(ttl), str(now if now is not None else "-")],
                       cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise SystemExit("ABORT: cannot mint a token: " + (r.stderr or "")[:300])
    return r.stdout.strip().splitlines()[-1]


def reason_of(payload):
    if not isinstance(payload, dict):
        return str(payload)[:60]
    for box in (payload, payload.get("detail"), payload.get("error")):
        if isinstance(box, dict):
            for key in ("reason_code", "reason", "code"):
                if box.get(key):
                    return box[key]
    return "no-reason-code:" + json.dumps(payload, ensure_ascii=False)[:80]


def main():
    report = {"at_local": time.strftime("%Y-%m-%d %H:%M:%S"), "port": PORT, "cases": []}

    def add(name, got, want, extra=""):
        ok = got == want
        report["cases"].append({"case": name, "expected": want, "observed": got, "ok": ok, "note": extra})
        print("%-46s want=%-45s got=%-45s %s" % (name, want, got, "OK" if ok else "MISMATCH"))
        return ok

    # ---- A 档：没有 secret
    proc, envA = start({}, "_cmdr0685_a.db")
    try:
        st, body, _ = call("GET", "/api/v1/travelers/session",
                           headers={"Authorization": "Bearer cmdr-fake-token"})
        add("A credential-present-but-no-secret: status", st, 503)
        add("A credential-present-but-no-secret: reason_code", reason_of(body), "TRAVELER_AUTH_NOT_CONFIGURED")
    finally:
        proc.terminate()
        proc.wait(timeout=60)

    # ---- B 档：配 secret（值不出进程）
    secret = secrets.token_urlsafe(48)
    proc, envB = start({"CITYNEXUS_TRAVELER_AUTH_SECRET": secret}, "_cmdr0685_b.db")
    try:
        st, body, _ = call("GET", "/api/v1/travelers/session")
        add("B no credentials: status", st, 401)
        add("B no credentials: reason_code", reason_of(body), "TRAVELER_CREDENTIALS_MISSING")

        st, made, _ = call("POST", "/api/v1/travelers", body={"display_name": "cmdr probe", "locale": "zh-CN", "timezone": "Asia/Shanghai"})
        tid = made.get("id") if isinstance(made, dict) else None
        add("B create traveler: status", st, 201 if tid else "no-id:" + str(made)[:40])
        add("B create traveler: carries access_token", "access_token" in (made or {}), True,
            "the V8 client has no way to obtain a credential unless the create door hands one over")

        token = mint(envB, tid)
        st, who, hdrs = call("GET", "/api/v1/travelers/session", headers={"Authorization": "Bearer " + token})
        add("B bearer token: status", st, 200)
        add("B bearer token: traveler_id matches", (who or {}).get("traveler_id"), tid)
        add("B bearer token: Cache-Control", str(hdr(hdrs, "Cache-Control")).lower(), "private, no-store",
            "header keys on the wire: " + ", ".join(sorted(hdrs)))
        add("B bearer token: Vary names the header", "x-citynexus-traveler-token" in str(hdr(hdrs, "Vary")).lower(), True)

        st, who2, _ = call("GET", "/api/v1/travelers/session",
                           headers={"X-CityNexus-Traveler-Token": token})
        add("B header alias: status", st, 200)

        tampered = token[:-3] + ("AAA" if not token.endswith("AAA") else "BBB")
        st, bad, _ = call("GET", "/api/v1/travelers/session", headers={"Authorization": "Bearer " + tampered})
        add("B tampered token: status", st, 401)
        add("B tampered token: reason_code", reason_of(bad), "TRAVELER_CREDENTIALS_INVALID")

        expired = mint(envB, tid, ttl=60, now=int(time.time()) - 600)
        st, bad2, _ = call("GET", "/api/v1/travelers/session", headers={"Authorization": "Bearer " + expired})
        add("B expired token: status", st, 401)
        add("B expired token: reason_code", reason_of(bad2), "TRAVELER_CREDENTIALS_EXPIRED")

        ghost = mint(envB, "11111111-2222-3333-4444-555555555555")
        st, bad3, _ = call("GET", "/api/v1/travelers/session", headers={"Authorization": "Bearer " + ghost})
        add("B unknown principal: status", st, 401)
        add("B unknown principal: reason_code", reason_of(bad3), "TRAVELER_PRINCIPAL_NOT_FOUND")
    finally:
        proc.terminate()
        proc.wait(timeout=60)

    report["all_ok"] = all(c["ok"] for c in report["cases"])
    report["n_cases"] = len(report["cases"])
    report["n_red"] = sum(1 for c in report["cases"] if not c["ok"])
    report["server_log_sha256"] = {
        name: hashlib.sha256(open(os.path.join(HERE, name), "rb").read()).hexdigest()[:16]
        for name in ("ord0685_server_A.log", "ord0685_server_B.log")
        if os.path.exists(os.path.join(HERE, name))
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("\nverdict: %d cases, %d not matching -> %s" % (
        report["n_cases"], report["n_red"], "ACCEPTED" if report["all_ok"] else "PARTIAL"))
    print("receipt -> %s" % OUT)
    return 0 if report["all_ok"] else 4


if __name__ == "__main__":
    sys.exit(main())
