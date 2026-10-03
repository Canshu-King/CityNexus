"""收形: pair the screen reading with file bytes, at the generation the reading was taken.

The commander's 22:35 line asks for "打卡词走真门而不走假门：屏读 + 文件字节对照". The 屏读 half was
delivered at 20:17 (that block is in the ledger). This is the byte half -- one row per sentence, five ways:

  1. the row's words as they stand in the source file at the generation I measured
     (`git show <measured>:frontend/src/features/checkin/checkinCopy.ts`, blob named by 40 hex);
  2. how many times that exact literal occurs in the bytes the port served for the entry asset --
     fetched over HTTP from my own front, not read off disk;
  3. whether the reason_code that keys the row is present in the bundle at all (the mapping shipped);
  4. whether the backend at that generation emits the same code, with what English prose of its own --
     the words that must NOT be on the glass;
  5. what the arm recorded the door actually answered.

It then re-reads the same four rows at the CURRENT tip, because both files moved since my generation:
if the words are unchanged the delivered reading still describes the line, and if they changed, it does
not, and that has to be said rather than glossed.
"""
import hashlib
import io
import os
import json
import re
import subprocess
import time
import urllib.request

WT = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt"
EVID = "%s/frontend/review/checkin-words-real-door" % WT
OUT = "%s/receipts/real_door_byte_pairing_r1.json" % EVID
MEASURED = "bf4f776b0ba943b88817dfcc0cb3442d75fd9e21"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
FRONT = 4996
COPY_PATH = "frontend/src/features/checkin/checkinCopy.ts"
MAIN_PATH = "backend/app/main.py"
CODES = {
    "journeyUnknown": "CHECKIN_JOURNEY_UNKNOWN",
    "activityUnknown": "CHECKIN_ACTIVITY_UNKNOWN",
    "activityNotInJourney": "CHECKIN_ACTIVITY_NOT_IN_JOURNEY",
    "placeUnknown": "CHECKIN_PLACE_UNKNOWN",
}


def git(*args):
    r = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout.strip()


def rows_from_source(text):
    out = {}
    for name in CODES:
        block = re.search(r'\n  %s: \{\n    zh: "(.*?)",\n    en: "(.*?)",' % name, text)
        out[name] = {"zh": block.group(1), "en": block.group(2)} if block else None
    return out


def server_prose(text, code):
    hits = text.count('"%s"' % code)
    idx = text.find('"%s"' % code)
    if idx < 0:
        return None, 0
    window = text[max(0, idx - 420):idx]
    messages = re.findall(r'"([A-Z][^"\\]{20,})"', window)
    return (messages[-1] if messages else None), hits


def bundle_hits(bundle_text, literal):
    raw = bundle_text.count(literal)
    escaped = json.dumps(literal, ensure_ascii=False)[1:-1]
    return {"literal_hits_in_served_bytes": raw,
            "escaped_form_hits": 0 if raw else bundle_text.count(escaped),
            "form_that_matched": "raw" if raw else ("escaped" if bundle_text.count(escaped)
                                                    else "NONE")}


def diff_shape(old, new, path):
    """What kind of change moved the file: comment lines or code lines. Counted, not eyeballed."""
    out = git("diff", "-U0", old, new, "--", path)
    changed = [l for l in out.splitlines()
               if (l.startswith("+") or l.startswith("-")) and not l.startswith("+++")
               and not l.startswith("---")]
    comment = [l for l in changed if l[1:].strip().startswith(("*", "//", "/*"))]
    return {"changed_lines": len(changed), "comment_lines": len(comment),
            "non_comment_lines": len(changed) - len(comment),
            "non_comment_samples": [l[:100] for l in changed if l not in comment][:4]}


def main():
    own = json.load(io.open("%s/receipts/real_door_stack_ownership_r1.json" % EVID, encoding="utf-8"))
    asset = own["entry_asset"]
    served = urllib.request.urlopen("http://127.0.0.1:%d%s" % (FRONT, asset), timeout=90).read()
    served_text = served.decode("utf-8", "replace")
    tip_now = git("ls-remote", "--refs", "origin", TIP_REF).split("\t")[0]

    copy_measured = git("show", "%s:%s" % (MEASURED, COPY_PATH))
    main_measured = git("show", "%s:%s" % (MEASURED, MAIN_PATH))
    copy_now = git("show", "%s:%s" % (tip_now, COPY_PATH))
    rows_measured = rows_from_source(copy_measured)
    rows_now = rows_from_source(copy_now)

    arms = {}
    for name in CODES:
        for locale in ("zh-CN", "en"):
            path = "%s/readings/r-%s-%s.json" % (EVID, locale, name)
            body = json.load(io.open(path, encoding="utf-8"))
            arms["%s/%s" % (locale, name)] = {"door_reason_code": body["door_reason_code"],
                                               "door_status": body["door_status"],
                                               "painted_equals_expected": body["checks"][
                                                   "painted_equals_the_tables_own_row"],
                                               "server_prose_off_screen": body["checks"][
                                                   "servers_own_prose_stays_off_the_screen"]}

    table = []
    for name, code in CODES.items():
        row = rows_measured[name]
        prose, hits = server_prose(main_measured, code)
        entry = {
            "copy_key": name, "reason_code": code,
            "source_blob_at_measured": git("rev-parse", "%s:%s" % (MEASURED, COPY_PATH)),
            "zh_row_in_source": row["zh"], "en_row_in_source": row["en"],
            "zh_in_served_bundle": bundle_hits(served_text, row["zh"]),
            "en_in_served_bundle": bundle_hits(served_text, row["en"]),
            "code_present_in_served_bundle": served_text.count(code),
            "backend_emits_code_times": hits,
            "backend_own_prose": prose,
            "backend_prose_present_in_bundle": served_text.count(prose) if prose else None,
            "arms": {k: v for k, v in arms.items() if k.endswith("/" + name)},
            "words_identical_at_current_tip": (rows_now[name] == row),
        }
        table.append(entry)

    body = {
        "taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "measured_generation": MEASURED, "tip_at_write": tip_now,
        "entry_asset": asset, "served_bytes": len(served),
        "served_sha1": hashlib.sha1(served).hexdigest(),
        "served_sha1_kind": "本机字节 sha1，不是 git 对象",
        "disk_bytes_equal": served == open("%s%s" % (own["dist"], asset), "rb").read(),
        "copy_blob_measured": git("rev-parse", "%s:%s" % (MEASURED, COPY_PATH)),
        "copy_blob_current": git("rev-parse", "%s:%s" % (tip_now, COPY_PATH)),
        "main_blob_measured": git("rev-parse", "%s:%s" % (MEASURED, MAIN_PATH)),
        "main_blob_current": git("rev-parse", "%s:%s" % (tip_now, MAIN_PATH)),
        "rows": table,
        "all_four_rows_in_bundle": all(r["zh_in_served_bundle"]["literal_hits_in_served_bytes"]
                                       and r["en_in_served_bundle"]["literal_hits_in_served_bytes"]
                                       for r in table),
        "all_four_codes_shipped": all(r["code_present_in_served_bundle"] > 0 for r in table),
        "no_backend_prose_in_bundle": all(not r["backend_prose_present_in_bundle"] for r in table),
        "words_changed_at_current_tip": sorted(r["copy_key"] for r in table
                                               if not r["words_identical_at_current_tip"]),
    }
    body["copy_file_diff_measured_to_current"] = diff_shape(MEASURED, tip_now, COPY_PATH)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(body, handle, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in body.items() if k != "rows"},
                     ensure_ascii=False, indent=1).encode("ascii", "replace").decode("ascii")[:900])
    for r in table:
        print("%s zh_hits=%s en_hits=%s code_in_bundle=%s backend_times=%s prose_in_bundle=%s "
              "same_at_tip=%s" % (r["copy_key"],
                                  r["zh_in_served_bundle"]["literal_hits_in_served_bytes"],
                                  r["en_in_served_bundle"]["literal_hits_in_served_bytes"],
                                  r["code_present_in_served_bundle"], r["backend_emits_code_times"],
                                  r["backend_prose_present_in_bundle"],
                                  r["words_identical_at_current_tip"]))
    print("WROTE %s bytes=%d" % (OUT, len(json.dumps(body, ensure_ascii=False).encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
