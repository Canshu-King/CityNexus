"""Re-read every quoted (file, line, text) triple in a delivered artifact straight from the tip and assert
they match. Quotes come from a `git archive` export, so this checks the artifact against the tree it cites,
not against my transcription. Any mismatch exits 7 and nothing gets published.
"""
import io
import json
import os
import subprocess
import sys

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
SCRATCH = os.path.join(ROOT, "_sweep_scratch")
REPO = "D:/moodle/CityNexus"
TREES = {
    "frontend/src": os.path.join(SCRATCH, "treeN", "frontend", "src"),
}
BE_CACHE = {}


def line_of(relpath, n):
    """Read line n of a path in the tip export; backend paths are read at the tip via git show."""
    if relpath.startswith("backend/"):
        if relpath not in BE_CACHE:
            p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (TIP, relpath)], capture_output=True)
            if p.returncode:
                raise SystemExit("CANNOT_READ %s:%s" % (TIP, relpath))
            BE_CACHE[relpath] = p.stdout.decode("utf-8", "replace").splitlines()
        lines = BE_CACHE[relpath]
    else:
        if not relpath.startswith("frontend/src/"):
            raise SystemExit("UNEXPECTED_CITED_ROOT %s" % relpath)
        local = os.path.join(TREES["frontend/src"], relpath[len("frontend/src/"):])
        lines = io.open(local, encoding="utf-8", errors="replace").read().splitlines()
    if not 1 <= n <= len(lines):
        raise SystemExit("LINE_OUT_OF_RANGE %s:%d (file has %d lines)" % (relpath, n, len(lines)))
    return lines[n - 1].strip()


def collect(doc):
    """Every (file, line, text) triple the artifact asserts, wherever it hides in the schema."""
    out = []

    def walk(node, ctx):
        if isinstance(node, dict):
            if "line" in node and "text" in node and ("file" in node or "path" in node):
                out.append((node.get("file") or node.get("path"), node["line"], node["text"], ctx))
            for k, v in node.items():
                walk(v, ctx + "/" + k)
        elif isinstance(node, list):
            for v in node:
                walk(v, ctx + "[]")

    walk(doc, "")
    return out


def main():
    global TIP
    TIP = sys.argv[1]
    bad, checked = [], 0
    for name in sys.argv[2:]:
        doc = json.load(io.open(os.path.join(ROOT, name), encoding="utf-8"))
        for rel, n, txt, ctx in collect(doc):
            checked += 1
            actual = line_of(rel, n)
            if actual != txt:
                bad.append({"artifact": name, "where": ctx[:60], "cite": "%s:%d" % (rel, n),
                            "artifact_text": txt[:70], "tree_text": actual[:70]})
        # structural asserts that must hold regardless of quotes
        if doc.get("generation") != TIP:
            bad.append({"artifact": name, "where": "generation", "cite": doc.get("generation"),
                        "artifact_text": "must equal the tip I was told to pin", "tree_text": TIP})
    print("artifacts=%d quotes_checked=%d mismatches=%d" % (len(sys.argv[2:]), checked, len(bad)))
    for b in bad[:20]:
        print("  MISMATCH", json.dumps(b, ensure_ascii=False))
    if bad:
        return 7
    print("QUOTES_VERIFIED_against_tip %s" % TIP)
    return 0


if __name__ == "__main__":
    sys.exit(main())
