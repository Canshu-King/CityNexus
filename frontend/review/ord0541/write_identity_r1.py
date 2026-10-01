"""ORD-0541 lane -- write the evidence folder's own identity file, computed from the artifacts that are
already in it.

Nothing is typed in here: the three commit coordinates come from the build receipts this lane copied in,
the served-entry hashes come from the ownership probe, and the run counts come from the per-generation
generation tables. A reader who wants to check that the bundle named in the delivery block is the bundle
that was served reads one file and one command, not a paragraph.
"""
import glob
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RECEIPTS = os.path.join(HERE, "receipts")
RUN = os.path.join(HERE, "run")


def read(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main():
    tags = {"candidate": "_build_ord0541c_info.json", "base": "_build_ord0541b_info.json",
            "mutant": "_build_ord0541m_info.json"}
    builds = {}
    for label, name in tags.items():
        receipt = read(os.path.join(RECEIPTS, name))
        builds[label] = {
            "commit": receipt["sha"],
            "built_at": receipt["at_local"],
            "build_rc": 0 if receipt["build"].get("dist_exists") else 1,
            "blob_equality_all_identical": all(
                row.get("identical") is True for row in receipt["export_blob_equality"].values()
            ),
            "blob_equality_files_checked": len(receipt["export_blob_equality"]),
        }

    ownership = read(os.path.join(RECEIPTS, "stack_ord0541.json"))
    ports = {"4980": "candidate", "4981": "base", "4982": "mutant",
             "4983": "candidate", "4984": "base"}
    served = {}
    for port, front in ownership["fronts"].items():
        served[port] = {
            "generation": front["label"],
            "entry_asset_named_by_served_index": front["entry_from_served_index"],
            "served_asset_sha1": front.get("served_asset_sha1"),
            "disk_asset_sha1": front.get("disk_asset_sha1"),
            "served_bytes_equal_disk": front.get("bytes_equal"),
            "outDir_third_proof": front.get("outDir_third_proof"),
        }

    tables = {}
    for path in sorted(glob.glob(os.path.join(RECEIPTS, "ord0541_generation_table_r*.json"))):
        tag = os.path.basename(path).replace("ord0541_generation_table_", "").replace(".json", "")
        data = read(path)
        tables[tag] = {}
        for generation, entry in data.items():
            tables[tag][generation] = {
                "arms": entry.get("arms"),
                "passed": entry.get("passed"),
                "failed": entry.get("failed"),
                "red_arm_titles": [row["arm"] for row in entry.get("rows", []) if row["state"] != "passed"],
                "red_first_lines": [row["first_error_line"] for row in entry.get("rows", [])
                                    if row["state"] != "passed"],
            }

    per_arm_files = {}
    for path in sorted(glob.glob(os.path.join(RUN, "*", "*.json"))):
        key = "%s/%s" % (os.path.basename(os.path.dirname(path)), os.path.basename(path))
        per_arm_files[key] = os.path.getsize(path)

    out = {
        "order": "ORD-0541",
        "lane": "e766b154",
        "generations": builds,
        "listeners_served": served,
        "run_counts_by_trip": tables,
        "per_arm_evidence_files": per_arm_files,
        "superseded_pass": {
            "run/candidate, run/base, run/mutant": "the ruler's first cut, which pressed twice inside one "
            "sheet and waited for the sentence to change -- see the two ruler-fix commits",
            "run/*_r1": "the corrected ruler with one wrong precondition (A1 compared the roster's total "
            "length to zero; the list door keeps withdrawn rows on purpose)",
        },
    }
    with io.open(os.path.join(HERE, "identity.json"), "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=1, ensure_ascii=False)
    print("IDENTITY_WROTE generations=%d listeners=%d trips=%d per_arm_files=%d"
          % (len(builds), len(served), len(tables), len(per_arm_files)))
    for tag in sorted(tables):
        for generation in ("candidate", "base", "mutant"):
            entry = tables[tag][generation]
            print("  %s %s arms=%s passed=%s failed=%s"
                  % (tag, generation, entry["arms"], entry["passed"], entry["failed"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
