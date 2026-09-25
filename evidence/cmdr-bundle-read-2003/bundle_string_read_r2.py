"""Commander's byte-read of the generation the phone is served: is the ORD-0302 guard in the shipped bundle?

Deliberately narrower than ORD-0312 and in a different register: this answers "which strings and which
optional-chaining shapes exist in the file the phone downloads", nothing about what a screen paints.
The runtime sentence still belongs to the measurement lane and the level to the verifier; this only stops
anyone from having to wonder whether the deployed generation carries the fix at all.

Needles are counted over the served bytes fetched from the same origin the tunnel answers on.
"""
import base64
import datetime
import hashlib
import io
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://127.0.0.1:4781"
PROBE = "evidence/cmdr-phone-chain-1919/phone_side_probe__7856e03f.json"
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "cmdr-bundle-read-r2"}
NEEDLES = {
    "label_technical_details": "技术详情",
    "promise_sentence_fragment": "原因原文在",
    "no_plans_status_token": "NO_PLANS_PRODUCED",
    "guard_optional_chain": r"\?\.\s*detail",
    "unguarded_member_read": r"\bbody\b\s*\.\s*detail",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "cmdr-bundle-read-r2"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, r.headers.get("content-type", ""), r.read()


def get(path):
    return json.loads(urllib.request.urlopen(urllib.request.Request(
        "https://api.github.com" + path, headers=H), timeout=240).read())


# the generation this read is about, taken from the published probe rather than from memory
meta = get("/repos/Canshu-King/CityNexus/contents/" + urllib.parse.quote(PROBE, safe="") + "?ref=commander%2Fcontrol")
raw_probe = base64.b64decode(get("/repos/Canshu-King/CityNexus/git/blobs/" + meta["sha"])["content"])
probe = json.loads(raw_probe.decode("utf-8"))
probe_sha = hashlib.sha1(b"blob %d\x00" % len(raw_probe) + raw_probe).hexdigest()
named = [r["path"] for r in probe["rows"] if r["path"].endswith(".js")]

st, ctype, index = fetch(BASE + "/index.html")
refs = sorted(set(re.findall(r'(?:src|href)="(/[^"]+\.(?:js|css))"', index.decode("utf-8", "replace"))))
rows = []
for ref in refs:
    s, ct, body = fetch(BASE + ref)
    text = body.decode("utf-8", "replace")
    counts = {}
    for k, pat in NEEDLES.items():
        counts[k] = len(re.findall(pat, text)) if k.startswith(("guard_", "unguarded_")) else text.count(pat)
    rows.append({"asset": ref, "http_status": s, "content_type": ct, "bytes": len(body),
                 "sha256": hashlib.sha256(body).hexdigest(), "served_equals_named_asset": ref in named,
                 "counts": counts})

out = {
    "schema": "CNX_CMDR_BUNDLE_STRING_READ_V2",
    "at_local": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).isoformat(timespec="seconds") + "+08",
    "generation_under_test": probe["generation_under_test"],
    "identity_source": {"probe_path": PROBE, "probe_blob": probe_sha, "probe_blob_named": "1020e014b78aec08ba6c2bf48ae809f01cf00ef5",
                        "probe_matches_citation": probe_sha == "1020e014b78aec08ba6c2bf48ae809f01cf00ef5",
                        "index_named_refs": refs},
    "rows": rows,
    "decisions": {
        "js_asset_named_by_the_probe_is_the_one_served": all(r["served_equals_named_asset"] for r in rows if r["asset"].endswith(".js")),
        "guard_present_in_shipped_bytes": any(r["counts"]["guard_optional_chain"] >= 1 for r in rows),
        "no_unguarded_body_detail_read": all(r["counts"]["unguarded_member_read"] == 0 for r in rows),
        "promise_label_still_ships": any(r["counts"]["label_technical_details"] >= 1 for r in rows)},
    "tool_sha1": hashlib.sha1(io.open(__file__, "rb").read()).hexdigest(),
    "scope": "Bytes only: which sentences and which read-shapes are inside the file the phone downloads. "
             "It is NOT the runtime sentence, NOT a screen reading, and NOT a verdict - the deployed-"
             "generation reading of both shapes belongs to ORD-0312 (measurement lane), the levels to the verifier."}
import urllib.parse  # noqa: E402
io.open("_bundle_string_read_r2.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print("generation", out["generation_under_test"], "| probe blob ok", out["identity_source"]["probe_matches_citation"])
for r in rows:
    print(" ", r["asset"], r["bytes"], "B", json.dumps(r["counts"], ensure_ascii=False))
print("decisions", json.dumps(out["decisions"], ensure_ascii=False))
