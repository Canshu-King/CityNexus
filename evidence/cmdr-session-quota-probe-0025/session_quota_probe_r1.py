"""Per-session Qoder quota probe: which of my lanes are actually blocked right now.

Why: a watchdog session reported at 23:54 that three lanes were dead from the daily quota. Two of them had
already recovered by 00:17 and I nearly accepted that reading. The cheap, honest way to know is to read each
session's own JSONL and count only RECORD-LEVEL API-error records (type assistant + displayErrorCode /
isApiErrorMessage), then compare the last error timestamp with the last record that carries content - a lane
whose newest content is newer than its newest error is alive, no matter how many 110s it has accumulated.

Text search is deliberately NOT the signal: my own session contains the string `110` and
"Billing daily count exceeded" because I print lane posts and probe code into tool inputs, and a substring
count there would read as three fresh quota errors.

Read-only; no session is messaged, nothing is written outside my own output file.
"""
import glob
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PROJECT_DIR = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LANES = {
    "B c01d72a3": "c01d72a3",
    "F 8ccd71d8": "8ccd71d8",
    "D e345b9d6": "e345b9d6",
    "E d2305848": "d2305848",
    "HJ-P3 aad2d1f2": "aad2d1f2",
    "cmdr 494abfd7": "494abfd7",
    "watchdog 42d1a6fa": "42d1a6fa",
}


def probe(prefix):
    files = glob.glob(os.path.join(PROJECT_DIR, prefix + "*.jsonl"))
    if not files:
        return {"error": "no jsonl for this prefix"}
    f = max(files, key=os.path.getmtime)
    errors, last_content = [], None
    for line in io.open(f, encoding="utf-8", errors="replace"):
        if '"type": "assistant"' not in line and '"type":"assistant"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        msg = d.get("message") or {}
        err = d.get("isApiErrorMessage") or msg.get("isApiErrorMessage")
        code = d.get("displayErrorCode")
        if code is None and isinstance(d.get("error"), dict):
            code = d["error"].get("code") or d["error"].get("displayErrorCode")
        if err or code is not None:
            errors.append({"at": d.get("timestamp"), "code": code,
                           "quota_110": str(code) == "110"})
        if (msg.get("content") or d.get("content")) and not err and code is None:
            last_content = d.get("timestamp")
    return {"jsonl": os.path.basename(f), "path": f, "api_error_records": len(errors),
            "last_error_at": errors[-1]["at"] if errors else None,
            "last_error_code": errors[-1]["code"] if errors else None,
            "last_content_at": last_content,
            "alive_now": bool(last_content) and (not errors or str(last_content) > str(errors[-1]["at"]))}


def main():
    rows = {}
    for label, pre in LANES.items():
        r = probe(pre)
        r["last_write_local"] = (time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(r["path"])))
                                 if r.get("path") else None)
        rows[label] = r
    blocked = [k for k, v in rows.items() if v.get("last_error_code") == "110" and not v.get("alive_now")]
    alive = [k for k, v in rows.items() if v.get("alive_now")]
    out = {
        "schema": "CNX_CMDR_SESSION_QUOTA_PROBE_V1",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what": "record-level (not substring) read of each session's JSONL to say who is quota-blocked right now",
        "method": "type==assistant + displayErrorCode/isApiErrorMessage at record level; then compare newest "
                  "error timestamp against newest content-bearing record",
        "sessions": rows,
        "still_blocked": blocked,
        "alive": alive,
        "why_not_substring": "my own session shows the strings `110` and 'Billing daily count exceeded' because "
                             "I print lane posts and this probe's code into tool inputs; a substring count there "
                             "would report phantom quota errors (that is how a watchdog reading can overcount).",
        "discipline": {"sessions_messaged": 0, "files_written": 1, "product_bytes_changed": 0,
                       "credential_values_printed": 0},
        "claim_kind": "log_determined",
        "claimed_result": None, "derived_result": None,
    }
    out["claimed_result"] = ("at %s: still quota-blocked = %s ; alive (newest content newer than newest error) = %s"
                             % (out["at_local"], blocked or "none", alive))
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    io.open("_cmdr_session_quota_probe.json", "w", encoding="utf-8", newline="\n").write(txt)
    print(out["claimed_result"])
    for label, r in rows.items():
        print("   %-16s errors=%-3s last_err=%s %s last_content=%s alive=%s" % (
            label, r.get("api_error_records"), str(r.get("last_error_at"))[:19], r.get("last_error_code"),
            str(r.get("last_content_at"))[:19], r.get("alive_now")))
    print("file=_cmdr_session_quota_probe.json bytes=%d" % len(txt.encode("utf-8")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
