"""Make evidence_provenance_sweep.py resumable + incrementally flushed.

Why a generator file instead of an inline shell edit: twice tonight a `\\n` inside an inline heredoc lost a
level of escaping on the way in and produced a real newline inside a string literal in the generated
Python.  Raw strings here, `ast.parse` before writing, and the original file is left untouched unless the
new one parses.
"""
import ast
import io

P = "evidence_provenance_sweep.py"
s = io.open(P, encoding="utf-8", newline="\n").read()

old = r'''    tip, blobs, truncated = tree_of(REF)
    ev = sorted(e["path"] for e in blobs if e["path"].startswith("evidence/") and e["path"].endswith(".json"))
    touched, scanned, failures = [], [], []
    for p in ev[:max_files]:'''

new = r'''    tip, blobs, truncated = tree_of(REF)
    ev = sorted(e["path"] for e in blobs if e["path"].startswith("evidence/") and e["path"].endswith(".json"))
    # r2: the first version only wrote at the very end, so a wall-clock kill during a 681-file sweep left
    # NOTHING behind.  The receipt is now flushed every `flush_every` files, and a re-run resumes from the
    # paths already scanned against the same ref tip - a killed sweep still yields a real denominator.
    touched, failures = [], []
    scanned = []
    if os.path.exists(OUT):
        try:
            prev = json.load(io.open(OUT, encoding="utf-8"))
            if prev.get("ref_tip_read") == tip:
                scanned = list(prev.get("scanned_paths") or [])
                touched = list(prev.get("list") or [])
        except Exception:
            pass
    done = set(scanned)
    todo = [x for x in ev if x not in done]
    flush_every = 25

    def flush():
        doc = {
            "schema": "CNX_EVIDENCE_PROVENANCE_SWEEP_V2",
            "ref": REF, "ref_tip_read": tip, "tree_truncated": truncated,
            "evidence_json_total": len(ev), "scanned": len(scanned), "cap": max_files,
            "coverage": "EXHAUSTIVE" if len(scanned) == len(ev) and not truncated else "NOT EXHAUSTIVE",
            "read_failures": len(failures), "failures_sample": failures[:5],
            "cite_main_py": len(touched), "scanned_paths": sorted(scanned), "list": touched,
            "meaning": "each listed receipt names backend/app/main.py, whose blob differs between "
                       "c79e2b4f and dcae1bc96 - those are the receipts a cross-generation quote must re-derive",
        }
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
        print("progress %d/%d cite_main_py=%d coverage=%s"
              % (len(scanned), len(ev), len(touched), doc["coverage"]), flush=True)

    for p in todo:'''

assert s.count(old) == 1, "main anchor"
s = s.replace(old, new, 1)

old2 = r'''        if hit_main:
            touched.append({"path": p, "cited_40hex": shas[:8], "n_shas": len(shas)})'''
new2 = r'''        if hit_main:
            touched.append({"path": p, "cited_40hex": shas[:8], "n_shas": len(shas)})
        if len(scanned) % flush_every == 0:
            flush()'''
assert s.count(old2) == 1, "loop anchor"
s = s.replace(old2, new2, 1)

# replace the single end-of-run receipt build with a call to flush()
start = s.index('    doc = {\n        "schema": "CNX_EVIDENCE_PROVENANCE_SWEEP_V1"')
end = s.index('    print("ref tip %s')
s = s[:start] + "    flush()\n\n" + s[end:]

tail_marker = '    print("wrote", OUT)'
assert s.count(tail_marker) == 1, "tail anchor"

ast.parse(s)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched", P, len(s.encode("utf-8")), "B; syntax OK")
