"""Build the landing-receipt file the r2 ruler needs, out of an instrument's own published output -- not out of
my memory of what landed.

A receipt here means: a scan already published on a side ref recorded that a hand's paths were byte-equal on a
named tip.  That is weaker than the commander's own landing note and it is labelled as such (`claim_source`),
and it is deliberately not extended to hands whose only "it landed" record is prose in a ledger block: those
refs stay unreceipted and r2 classifies them `NOT_ON_LINE` instead of inventing a loss.
"""
import json
import os
import re
import subprocess

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
SRC_REF = "refs/heads/review/0afdb49b-landed-blob-rescan-r1"
SRC_PATH = "review/landed-blob-rescan/evidence/landed_blob_rescan_r1.json"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*a):
    p = subprocess.run(["git", "-C", WT] + list(a), capture_output=True, timeout=300, env=ENV)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def main():
    rc, out, err = git("ls-remote", "--refs", "origin", SRC_REF)
    if rc or not out.strip():
        raise SystemExit("ABORT_SRC_REF_UNREADABLE " + (out + err)[:120])
    head = out.split()[0]
    rc, blob, err = git("rev-parse", "%s:%s" % (head, SRC_PATH))
    if rc:
        raise SystemExit("ABORT_SRC_BLOB_UNREADABLE " + err[:120])
    src_blob = re.match(r"([0-9a-f]{40})", blob.strip()).group(1)
    rc, text, err = git("cat-file", "blob", src_blob)
    if rc:
        raise SystemExit("ABORT_SRC_BYTES_UNREADABLE " + err[:120])
    prior = json.loads(text)
    landed = []
    for r in prior.get("refs", []):
        if r.get("verdict") != "HELD":
            continue
        landed.append({"ref": r["ref"], "head": r["head"], "paths": r["paths"],
                       "landed_tip": prior["live_tip"],
                       "claim_source": "%s@%s:%s" % (SRC_REF, head, SRC_PATH),
                       "claim_source_blob": src_blob,
                       "instrument_verdict_at_claim": "HELD"})
    if not landed:
        raise SystemExit("ABORT_NO_RECEIPTS_DERIVED prior scan verdicts: %s"
                         % sorted({r.get("verdict") for r in prior.get("refs", [])}))
    dest = os.path.join(LANE, "run", "rescan2_receipts.json")
    json.dump({"schema": "CNX_LANDED_RECEIPTS_V1", "derived_from": prior.get("tool"),
               "derived_locally": True, "landed": landed},
              open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"receipts": len(landed), "prior_tip": prior["live_tip"],
                      "prior_scan_tool": prior.get("tool"), "src_blob": src_blob,
                      "refs": [e["ref"].split("/")[-1] for e in landed]}, indent=1))
    print("WROTE " + dest)


if __name__ == "__main__":
    main()
