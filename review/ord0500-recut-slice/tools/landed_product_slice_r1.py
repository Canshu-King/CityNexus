"""The product slice of the r2 inventory: of the paths my hands actually changed outside `review/`, what does
the live line hold right now?

Why this is the cell worth taking next: the r2 scan sorts whole refs, and a ref can be `SUPERSEDED_ON_LINE`
because of a receipts JSON nobody reads.  What a traveller feels is the product path -- the sheet, the copy
file, the i18n context.  This tool asks, per product path, the same question the standing rule says to ask:
compare blobs, do not consult ancestry.

Rows come from a ref's own diff (`git diff --name-only <ref>^..<ref>`), never from a remembered file list;
the tip side is read at call time.  A path the hand deleted is reported as a deletion claim, and an unreadable
tip read is its own verdict -- never folded into "the file is gone".
"""
import json
import os
import re
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
sys.path.insert(0, os.path.join(LANE, "tools"))
import landed_blob_rescan_r2 as R

KEYS = "0afdb49b,newlane-ord0500-phone,newlane-ord0485-phone"


def main():
    # set on the imported module, not in the environment: KEYS is read once at import there, so an env var
    # written after the import would look like it took effect and change nothing
    R.KEYS = tuple(KEYS.split(","))
    tip = R.live_tip()
    rows = R.all_review_refs()
    heads = dict(rows)
    refs, missed = R.my_refs(rows)
    out = {"schema": "CNX_LANDED_PRODUCT_SLICE_V1", "tool": "landed_product_slice_r1", "live_tip": tip,
           "took_local": datetime.now().astimezone().isoformat(), "refs_scanned": len(refs),
           "refs_review_total": len(rows), "paths": [], "refs_without_product_paths": 0}
    readable = R.tree_ok(tip)
    tally = {}
    for ref in refs:
        cs, why = R.coordinates(ref, heads[ref])
        if cs is None:
            out["paths"].append({"ref": ref, "verdict": "NOT_REACHED", "why": why})
            continue
        prod = [c for c in cs["coords"] if not c["path"].startswith("review/")]
        if not prod:
            out["refs_without_product_paths"] += 1
            continue
        for c in prod:
            if not readable:
                on_line = "UNREADABLE_ON_LINE"
            else:
                rc, o, err = R.git("rev-parse", "%s:%s" % (tip, c["path"]))
                m = re.match(r"([0-9a-f]{40})", o.strip()) if rc == 0 else None
                on_line = m.group(1) if m else ("ABSENT" if rc else "UNREADABLE_ON_LINE")
            if c["expect"] == "DELETED_BY_HAND":
                verdict = "DELETION_HELD" if on_line == "ABSENT" else "DELETION_UNDONE"
            elif on_line == "ABSENT":
                verdict = "NOT_ON_LINE"
            elif on_line == "UNREADABLE_ON_LINE":
                verdict = "UNREADABLE_ON_LINE"
            elif on_line == c["expect"]:
                verdict = "HELD_AS_SHIPPED"
            else:
                verdict = "SUPERSEDED_ON_LINE"
            tally[verdict] = tally.get(verdict, 0) + 1
            out["paths"].append({"ref": ref.split("/")[-1], "ref_head": cs["head"], "path": c["path"],
                                 "shipped_blob": c["expect"], "on_line": on_line, "verdict": verdict})
    out["tally"] = tally
    dest = os.path.join(LANE, "evidence", "landed_product_slice_r1.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"live_tip": tip, "refs_scanned": len(refs),
                      "refs_without_product": out["refs_without_product_paths"],
                      "product_rows": len(out["paths"]), "tally": tally}, ensure_ascii=False))
    for p in out["paths"]:
        print("%-44s %-52s %s" % (p["ref"], p["path"][:52], p["verdict"]))
    print("WROTE " + dest)


if __name__ == "__main__":
    main()
