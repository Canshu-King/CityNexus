"""Counter-arm for the two sentences the order named -- break the product side, show the judge bites.

CMDR 02:45 item 6 (ledger line 16866): of the six rows no instrument ever painted, take
`targetRequired` and `targetAmbiguous` and build 反件 -- mutate the product so the sentence disappears,
and prove my screen-read reddens rather than shrugging.

Two independent ways for a sentence to disappear, each expected to be caught by a DIFFERENT assertion:

  M1  mapping removed -- drop the two `CHECKIN_REFUSAL_COPY` rows, so those reason codes fall through to
      the generic `unexpected` sentence. The door's own words are gone but *something* is painted: only a
      judge that compares against the named row can see it.
  M2  row emptied    -- blank both locales of the two rows. The component guards on a truthy notice, so
      an empty sentence renders no element at all: caught by "exactly one notice on the screen".

This file only edits and restores its own worktree copy, keeps the original bytes in a sidecar, and
refuses to report success unless the restore is byte-identical (sha256 both ways).
"""
import hashlib
import io
import re
import json
import os
import sys
import time

WT = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt"
TARGET = "%s/frontend/src/features/checkin/checkinCopy.ts" % WT
EVID = "%s/frontend/review/checkin-words-mutants-day25" % WT
RECEIPT = "%s/receipts/target_sentences_mutant_r1.json" % EVID
SIDECAR = "%s/receipts/checkinCopy.ts.orig_bytes" % EVID
MAP_ROWS = ['  CHECKIN_TARGET_REQUIRED: "targetRequired",',
            '  CHECKIN_TARGET_AMBIGUOUS: "targetAmbiguous",']
ROW_START = {
    "targetRequired": '  targetRequired: {\n    zh: "',
    "targetAmbiguous": '  targetAmbiguous: {\n    zh: "',
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_bytes():
    with open(TARGET, "rb") as handle:
        return handle.read()


def write_bytes(data):
    with open(TARGET, "wb") as handle:
        handle.write(data)


def record(event):
    os.makedirs(os.path.dirname(RECEIPT), exist_ok=True)
    history = {"events": []}
    if os.path.exists(RECEIPT):
        history = json.load(io.open(RECEIPT, encoding="utf-8"))
    event["at_local"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    history["events"].append(event)
    history["target_file"] = "frontend/src/features/checkin/checkinCopy.ts"
    with io.open(RECEIPT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(history, handle, indent=1, ensure_ascii=False)
    printable = json.dumps(event, ensure_ascii=False).encode("ascii", "replace").decode("ascii")
    print(printable[:900])


def apply_m1(before):
    text = before.decode("utf-8")
    removed = []
    for row in MAP_ROWS:
        if text.count("\n%s\n" % row) != 1:
            raise AssertionError("M1_ABORT row not found exactly once: %r" % row)
        text = text.replace("\n%s\n" % row, "\n")
        removed.append(row)
    after = text.encode("utf-8")
    kept = [line.strip() for line in text.split("\n")
            if re.match(r'^  CHECKIN_[A-Z_]+: "', line)]
    return after, {"rows_removed": removed, "mapping_rows_left": len(kept),
                   "mapping_rows_kept": kept}


def apply_m2(before):
    text = before.decode("utf-8")
    for key in ROW_START:
        if text.count(ROW_START[key]) != 1:
            raise AssertionError("M2_ABORT row head not found exactly once: %s" % key)
    import re
    for key in ROW_START:
        block = re.compile(r"(%s: \{\n    zh: )\"[^\n]*\",\n    en: \"[^\n]*\",\n  \}" % key)
        text, hits = block.subn(r'\1"",\n    en: "",\n  }', text)
        if hits != 1:
            raise AssertionError("M2_ABORT blanking hit %s times for %s" % (hits, key))
    return text.encode("utf-8"), {"rows_emptied": sorted(ROW_START)}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "apply":
        which = sys.argv[2]
        before = read_bytes()
        if not os.path.exists(SIDECAR):
            os.makedirs(os.path.dirname(SIDECAR), exist_ok=True)
            with open(SIDECAR, "wb") as handle:
                handle.write(before)
        after, detail = (apply_m1(before) if which == "M1" else apply_m2(before))
        write_bytes(after)
        record({"event": "apply", "mutant": which, "sha256_before": sha256(before),
                "sha256_after": sha256(after), "bytes_before": len(before),
                "bytes_after": len(after), **detail})
        print("APPLIED %s" % which)
        return 0
    if mode == "restore":
        before = read_bytes()
        with open(SIDECAR, "rb") as handle:
            original = handle.read()
        write_bytes(original)
        after = read_bytes()
        identical = sha256(after) == sha256(original)
        record({"event": "restore", "sha256_before_restore": sha256(before),
                "sha256_after_restore": sha256(after), "sidecar_sha256": sha256(original),
                "restored_byte_identical": identical})
        print("RESTORED identical=%s" % identical)
        return 0 if identical else 3
    if mode == "status":
        data = read_bytes()
        print("sha256 %s bytes %d" % (sha256(data), len(data)))
        print("sidecar %s" % (sha256(open(SIDECAR, "rb").read()) if os.path.exists(SIDECAR)
                              else "NO_SIDECAR"))
        return 0
    raise SystemExit("usage: %s apply M1|M2 | restore | status" % sys.argv[0])


if __name__ == "__main__":
    sys.exit(main())
