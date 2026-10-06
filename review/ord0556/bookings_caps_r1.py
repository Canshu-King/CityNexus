"""ORD-0556 -- measure the bookings caps words before and after this lane's retitles, then break them.

Sequence, all on this lane's own stack (backend of mine over a COPY of the commander's canary, vite of
mine, both hashed and torn down):

  before   the tip's own LocaleContext, read in both arms            -> the baseline this order cites
  after    this lane's retitled LocaleContext, read in both arms      -> the fix
  N1       one value put back to ALL CAPS (single variable)            -> that word must come back
  N2       one dictionary key renamed so t() falls back to the key     -> a key name must appear
  restored byte-identical, and the Chinese arm must be unchanged by an English-only fix.

The counting rules are the commander's (quoted into the reader), so the numbers are comparable.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
FRONTEND = ROOT / "frontend"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
READOUTS = ROOT / "review/ord0556/readouts"
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
DICT = ROOT / DICT_REL
READER = ROOT / "review/ord0556/bookings_caps_reader_r1.js"
SOURCE_CANARY = pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/canary_56d20ec.db")
BASE_TIP = os.environ.get("CITYNEXUS_ORD0556_BASE_TIP", "")
BACKEND_PORT = int(os.environ.get("CITYNEXUS_ORD0556_BACKEND_PORT", "4943"))
FRONTEND_PORT = int(os.environ.get("CITYNEXUS_ORD0556_FRONTEND_PORT", "4948"))
RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
SFX = RUN_STAMP[-7:-1]
STORE = DATA / f"_ord0556_{SFX}.db"
BACKEND_LOG = DATA / f"uvicorn_{BACKEND_PORT}_{SFX}.log"
VITE_LOG = DATA / f"vite_{FRONTEND_PORT}_{SFX}.log"
RECEIPT = READOUTS / f"ord0556_caps_{RUN_STAMP}.json"
LOCK = DATA / f"ord0556_caps_{SFX}.lock"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
ROUTES = ["/v8/bookings"]
WATCH = ("STAY", "MULTIMODAL", "AUTHORITATIVE")
LABELS = ("Stay evidence", "Multimodal inbox", "Authoritative memory")
SUBS = {
    "stay": ('  "bookings.stayEvidence": "Stay evidence",', '  "bookings.stayEvidence": "STAY EVIDENCE",'),
    "key": ('  "inbox.multimodal": ', '  "inbox.multimoda": '),
}


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def listeners(port: int) -> list[str]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace").stdout
    return sorted({ln.split()[-1] for ln in out.splitlines()
                   if len(ln.split()) >= 5 and ln.split()[0].upper() == "TCP"
                   and ln.split()[3].upper() == "LISTENING" and ln.split()[1].endswith(f":{port}")})


def http(method: str, url: str, body: dict | None = None, timeout: int = 20):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"content-type": "application/json",
                                          "user-agent": "CityNexus-ORD-0556-lane"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        return r.status, json.loads(raw)
    except ValueError:
        return r.status, raw


def read(locale: str, tag: str) -> dict:
    READOUTS.mkdir(parents=True, exist_ok=True)
    out_file = READOUTS / f"ord0556_read_{locale}_{tag}_{SFX}.json"
    started = time.time()
    r = subprocess.run(["node", str(READER), f"http://127.0.0.1:{FRONTEND_PORT}/", str(out_file),
                        locale, *ROUTES], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=420)
    d = json.loads(out_file.read_text(encoding="utf-8")) if out_file.is_file() else {}
    per = d.get("perRoute", {}).get("/v8/bookings", {})
    items = per.get("items", [])
    return {
        "tag": tag, "locale": locale, "rc": r.returncode, "wall_seconds": round(time.time() - started, 1),
        "file": out_file.name, "pageErrors": d.get("pageErrors", []),
        "items": [{"kind": i["kind"], "token": i["token"], "cls": i["cls"]} for i in items],
        "tokens": sorted({i["token"] for i in items}),
        "kinds": per.get("kinds", {}),
        "url_now": per.get("url_now"), "walk_stats": per.get("walk_stats"),
        "inner_text_head": per.get("inner_text_head"),
        "leftovers": per.get("leftovers", []),
        "key_fallback_anywhere": per.get("key_fallback_anywhere"),
        "body_text_chars": per.get("documentChars"),
        "watch_tokens_present": sorted(t for t in {i["token"] for i in items} if t in WATCH),
        "labels": {l["needle"]: {"present": l.get("present"), "dom_upper": l.get("dom_is_upper_case"),
                                 "rendered_upper": l.get("rendered_is_upper_case"),
                                 "dom_text": l.get("dom_text"), "rendered_text": l.get("rendered_text"),
                                 "transform": l.get("computed_text_transform")}
                   for l in per.get("labels", [])},
        "stderr_head": (r.stderr or "")[:200],
    }


def main() -> int:
    if LOCK.exists():
        holder = "".join(ch for ch in LOCK.read_text(encoding="utf-8") if ch.isdigit())
        alive = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                f"Get-Process -Id {holder} -ErrorAction SilentlyContinue | ForEach-Object {{ $_.Id }}"],
                               capture_output=True, text=True).stdout.strip() if holder.isdigit() else ""
        if alive:
            raise SystemExit("ABORT another ORD-0556 run holds the lock (live pid " + alive + ")")
        print("lock left by a dead pid; taking it over", flush=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8", newline="\n")
    if not re.fullmatch(r"[0-9a-f]{40}", BASE_TIP or ""):
        raise SystemExit("ABORT CITYNEXUS_ORD0556_BASE_TIP must be the 40-hex tip measured on")
    if listeners(BACKEND_PORT) or listeners(FRONTEND_PORT):
        raise SystemExit("ABORT my ports are held: " + str(listeners(BACKEND_PORT) + listeners(FRONTEND_PORT)))
    if not SOURCE_CANARY.is_file() or not READER.is_file():
        raise SystemExit("ABORT the canary or the reader is missing")

    fixed = DICT.read_bytes()
    tip_src = subprocess.run(["git", "-C", str(ROOT), "show", BASE_TIP + ":" + DICT_REL],
                             capture_output=True).stdout
    if not tip_src:
        raise SystemExit("ABORT could not read the tip's dictionary; the before-phase would be a guess")
    tip_sha = hashlib.sha256(tip_src).hexdigest()
    fixed_sha = sha(DICT)
    source_before = sha(SOURCE_CANARY)
    STORE.write_bytes(SOURCE_CANARY.read_bytes())

    doc: dict = {"generation": {"base_tip": BASE_TIP, "recorded_at": RUN_STAMP,
                                "dictionary_sha_at_tip": tip_sha, "dictionary_sha_fixed": fixed_sha,
                                "dictionary_differs_from_tip": tip_sha != fixed_sha,
                                "this_lane_ports": [BACKEND_PORT, FRONTEND_PORT],
                                "routes": ROUTES, "store_copy": STORE.name,
                                "canary_source_sha256_before": source_before},
                 "phases": []}

    def emit():
        READOUTS.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_E2E_RUN_ID", None)
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{STORE.as_posix()}"
    env["CITYNEXUS_DEMO_MODE"] = "true"
    b_log = BACKEND_LOG.open("w", encoding="utf-8", errors="replace")
    backend = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                "--port", str(BACKEND_PORT), "--log-level", "warning"],
                               cwd=ROOT / "backend", env=env, stdout=b_log, stderr=subprocess.STDOUT)
    vite_env = dict(env)
    vite_env["CITYNEXUS_BACKEND_PORT"] = str(BACKEND_PORT)
    v_log = VITE_LOG.open("w", encoding="utf-8", errors="replace")
    vite = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1",
                             "--port", str(FRONTEND_PORT), "--strictPort"],
                            cwd=FRONTEND, env=vite_env, stdout=v_log, stderr=subprocess.STDOUT)
    aborted = ""
    try:
        for _ in range(90):
            try:
                if http("GET", f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health")[0] == 200:
                    break
            except (urllib.error.URLError, ConnectionError, OSError):
                pass
            time.sleep(1)
        else:
            raise SystemExit("ABORT backend never answered; see " + str(BACKEND_LOG))
        for _ in range(90):
            if listeners(FRONTEND_PORT):
                break
            time.sleep(1)
        else:
            raise SystemExit("ABORT vite never listened; see " + str(VITE_LOG))

        def phase(name: str, dictionary_bytes: bytes | None = None):
            if dictionary_bytes is not None:
                DICT.write_bytes(dictionary_bytes)
                time.sleep(2.0)  # let vite's file watcher pick the change up before the read
            row = {"phase": name, "reads": {}}
            for locale in ("en", "zh"):
                row["reads"][locale] = read(locale, name)
                rr = row["reads"][locale]
                print(name, locale, "rc", rr["rc"], "watch", rr["watch_tokens_present"],
                      "items", len(rr["items"]), "url", rr["url_now"],
                      "walk", json.dumps(rr["walk_stats"]), flush=True)
            doc["phases"].append(row)
            emit()
            return row

        before = phase("before_tip_source", tip_src)
        after = phase("after_retitles", fixed)
        doc["phases"].append({"phase": "restored_check",
                              "dictionary_sha_after_restoring_fix": sha(DICT),
                              "equal_to_fixed": sha(DICT) == fixed_sha})
        emit()

        # N1: one value back to ALL CAPS -- the word must return to the English arm
        n1_text = fixed.decode("utf-8").replace(SUBS["stay"][0], SUBS["stay"][1], 1)
        if n1_text.count(SUBS["stay"][1]) != 1:
            aborted = "N1 anchor moved"
            doc["phases"].append({"phase": "N1", "skipped": aborted})
        else:
            row = {"phase": "N1_one_value_back_to_all_caps"}
            DICT.write_text(n1_text, encoding="utf-8", newline="\n")
            time.sleep(2.0)
            row["en"] = read("en", "N1")
            DICT.write_bytes(fixed)
            row["restored"] = sha(DICT) == fixed_sha
            row["bites"] = "STAY" in row["en"]["watch_tokens_present"] and row["restored"]
            doc["phases"].append(row)
            print("N1", json.dumps({"bites": row["bites"], "watch": row["en"]["watch_tokens_present"]}), flush=True)
            emit()

        # N2: one key renamed in both tables so the component's lookup falls back to printing the key
        n2_text = fixed.decode("utf-8").replace(SUBS["key"][0], SUBS["key"][1], 2)
        # English and Chinese tables each carry the key, so a rename must land on exactly two lines
        if n2_text.count(SUBS["key"][1]) != 2 or aborted:
            doc["phases"].append({"phase": "N2", "skipped": aborted or "N2 anchor moved"})
        else:
            row = {"phase": "N2_one_key_renamed"}
            DICT.write_text(n2_text, encoding="utf-8", newline="\n")
            time.sleep(2.0)
            row["en"] = read("en", "N2")
            DICT.write_bytes(fixed)
            row["restored"] = sha(DICT) == fixed_sha
            # Measured: with the key renamed, the label simply LEAVES the screen and the key name is
            # never painted (`key_fallback_anywhere` False) -- this component's `t` has no key echo.
            # So the honest non-vacuity signal is the departure itself: the slot is dictionary-driven,
            # not a string hardcoded in JSX.
            row["key_name_on_screen"] = bool(row["en"].get("key_fallback_anywhere"))
            row["human_words_gone"] = row["en"]["labels"].get("Multimodal inbox", {}).get("present") is False
            row["other_json_items_untouched"] = sorted(i["token"] for i in row["en"]["items"]) == ["JSON", "JSON"]
            row["bites"] = bool(row["human_words_gone"] and row["other_json_items_untouched"] and row["restored"])
            doc["phases"].append(row)
            print("N2", json.dumps({"bites": row["bites"], "key_echo_on_screen": row["key_name_on_screen"],
                                    "human_words_gone": row["human_words_gone"]}), flush=True)
            emit()

        # N3: the claim "the kicker's uppercase look comes from CSS, not from my string" is falsified by
        # one line of styles.css -- drop the transform and the rendered text must stop being uppercase.
        if not aborted:
            css_path = FRONTEND / "src/styles.css"
            css_bytes = css_path.read_bytes()
            css_sha = hashlib.sha256(css_bytes).hexdigest()
            css_text = css_bytes.decode("utf-8")
            anchor = ".v8-kicker { margin: 0 0 var(--cn-s-10); color: var(--v8-indigo); font-size: 10px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }"
            if css_text.count(anchor) != 1:
                doc["phases"].append({"phase": "N3_css_transform", "skipped": "anchor count " + str(css_text.count(anchor))})
                aborted = "N3 anchor moved"
            else:
                row = {"phase": "N3_kicker_transform_removed"}
                mutated = css_text.replace(anchor,
                                           anchor.replace("text-transform: uppercase", "text-transform: none"),
                                           1)
                css_path.write_bytes(mutated.encode("utf-8"))
                time.sleep(2.0)
                row["en"] = read("en", "N3")
                css_path.write_bytes(css_bytes)
                row["restored"] = hashlib.sha256(css_path.read_bytes()).hexdigest() == css_sha
                lab = row["en"]["labels"].get("Multimodal inbox", {})
                row["rendered_stopped_being_uppercase"] = lab.get("present") is True and lab.get("rendered_upper") is False
                row["dom_text_stayed_title_case"] = lab.get("dom_text") == "Multimodal inbox"
                row["bites"] = bool(row["rendered_stopped_being_uppercase"] and row["dom_text_stayed_title_case"]
                                    and row["restored"])
                doc["phases"].append(row)
                print("N3", json.dumps({"bites": row["bites"], "rendered_upper": lab.get("rendered_upper"),
                                        "dom_text": lab.get("dom_text"), "restored": row["restored"]}), flush=True)
                emit()
    finally:
        DICT.write_bytes(fixed)
        for p in (vite, backend):
            p.terminate()
        for _ in range(30):
            if vite.poll() is not None and backend.poll() is not None:
                break
            time.sleep(1)
        for p in (vite, backend):
            if p.poll() is None:
                p.kill()
        v_log.close()
        b_log.close()
        doc["teardown"] = {"dictionary_byte_identical_at_exit": sha(DICT) == fixed_sha,
                           "my_ports_listening_after": {str(BACKEND_PORT): listeners(BACKEND_PORT),
                                                         str(FRONTEND_PORT): listeners(FRONTEND_PORT)},
                           "canary_source_sha256_after": sha(SOURCE_CANARY),
                           "canary_source_untouched": sha(SOURCE_CANARY) == source_before}
        emit()
        LOCK.unlink(missing_ok=True)
        STORE.unlink(missing_ok=True)
        BACKEND_LOG.unlink(missing_ok=True)
        VITE_LOG.unlink(missing_ok=True)


    b = {p["phase"]: p for p in doc["phases"]}
    en_before = b.get("before_tip_source", {}).get("reads", {}).get("en", {})
    en_after = b.get("after_retitles", {}).get("reads", {}).get("en", {})
    zh_before = b.get("before_tip_source", {}).get("reads", {}).get("zh", {})
    zh_after = b.get("after_retitles", {}).get("reads", {}).get("zh", {})
    checks = {
        "watch_tokens_were_live_before": len(en_before.get("watch_tokens_present", [])) == 3,
        "watch_tokens_gone_after": en_after.get("watch_tokens_present", []) == [],
        "labels_still_painted_after": all(
            en_after.get("labels", {}).get(l, {}).get("present") is True for l in LABELS),
        "chinese_arm_items_unchanged": [i["token"] for i in zh_before.get("items", [])]
        == [i["token"] for i in zh_after.get("items", [])],
        "chinese_arm_no_page_errors": zh_after.get("pageErrors", []) == [],
        "english_arm_no_page_errors": en_after.get("pageErrors", []) == [],
        "kicker_still_uppercase_by_css": all(
            en_after.get("labels", {}).get(l, {}).get("transform") == "uppercase"
            for l in ("Multimodal inbox", "Authoritative memory")),
        "N1_bites": next((p["bites"] for p in doc["phases"] if p["phase"].startswith("N1")), False),
        "N2_bites": next((p["bites"] for p in doc["phases"] if p["phase"].startswith("N2")), False),
        "N3_css_bites": next((p["bites"] for p in doc["phases"] if p["phase"].startswith("N3")), False),
        "dictionary_restored": doc["teardown"]["dictionary_byte_identical_at_exit"],
        "canary_untouched": doc["teardown"]["canary_source_untouched"],
        "ports_free": all(v == [] for v in doc["teardown"]["my_ports_listening_after"].values()),
    }
    doc["checks"] = checks
    doc["verdict"] = ("CAPS_DONE " + str(sum(checks.values())) + " of " + str(len(checks)) +
                      " checks green" if all(checks.values()) else "NOT_DONE " +
                      ",".join(k for k, v in checks.items() if not v))
    emit()
    print(json.dumps({"receipt": str(RECEIPT), "checks": checks, "verdict": doc["verdict"]},
                     ensure_ascii=False), flush=True)
    return 0 if doc["verdict"].startswith("CAPS_DONE") else 1


if __name__ == "__main__":
    sys.exit(main())
