import re, io, sys, collections, os

BASE = r"D:\moodle\_cn7_plural_surface_0057.txt"
WT = r"D:\moodle\_qoder_huomingxi_0558\wt"
TIP = "7ce836f9afafe9e763527cba828719b414b18db8"
BASE_TIP = "2f02024c2a1165f68a1a8c275dd7c336c72ec7b2"

rows = []
with io.open(BASE, encoding="utf-8", errors="replace") as f:
    for l in f:
        l = l.rstrip("\n")
        m = re.match(r"^(frontend/[^|]+?:\d+) \| (.*?) \| ([ABC]) \| (.*)$", l)
        if m:
            rows.append(m.groups())

def kind(j):
    if "单位缩写" in j:
        return "UNIT"
    if "中文量词" in j:
        return "ZH"
    if "一般名词" in j or "硬衬词" in j:
        return "NOUN"
    return "OTHER"

# files that the addendum lists as code-side
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
code_files = []
with io.open(LEDGER, encoding="utf-8", errors="replace") as f:
    tx = f.read().split("\n")
s = next(i for i, l in enumerate(tx) if l.startswith("### 号令者追加（接 ORD-0558）"))
e = next(j for j in range(s + 5, s + 200) if tx[j].startswith("字典侧"))
for l in tx[s:e]:
    m = re.match(r"^- `(frontend/[^`]+)`\uFF5c(\d+)\uFF0f(\d+)", l)
    if m:
        code_files.append(m.group(1))

cache = {}
def tip_lines(path):
    if path not in cache:
        p = os.path.join(WT, path.replace("/", os.sep))
        with io.open(p, encoding="utf-8", errors="replace") as f:
            cache[path] = [x.rstrip("\n") for x in f]
    return cache[path]

out = []
out.append(f"base_tip={BASE_TIP}")
out.append(f"current_tip={TIP}")
out.append(f"base_rows_parsed={len(rows)} addendum_code_files={len(code_files)}")
out.append("")
per = collections.defaultdict(lambda: collections.Counter())
reanchor = collections.defaultdict(list)
miss = []
for coord, text, cls, j in rows:
    path, line = coord.rsplit(":", 1)
    if path not in code_files:
        continue
    k = kind(j)
    per[path][k] += 1
    if k not in ("NOUN", "OTHER"):
        continue
    want = text.strip()
    lines = tip_lines(path)
    hits = [i + 1 for i, l in enumerate(lines) if l.strip() == want]
    if not hits:
        # fall back: substring of a tip line (base may have trimmed trailing chars)
        hits = [i + 1 for i, l in enumerate(lines) if want[:60] in l.strip()]
    if hits:
        reanchor[path].append((k, int(line), hits, text, j))
    else:
        miss.append((coord, k, text[:70]))
    per[path]["hit" if hits else "miss"] += 1

out.append("=== per-file, addendum code-side rows classified by CN's own judgement, re-anchored on the current tip ===")
out.append("file | NOUN | UNIT | ZH | OTHER | noun_rows_now_at")
for path in sorted(code_files, key=lambda p: (-per[p]["NOUN"], p)):
    nows = []
    for k, ol, hs, t, j in sorted(reanchor[path], key=lambda x: x[1]):
        if k == "NOUN":
            nows.append(f":{ol}->{','.join(str(h) for h in hs)}")
    out.append(f"{path} | {per[path]['NOUN']} | {per[path]['UNIT']} | {per[path]['ZH']} | {per[path]['OTHER']} | {' '.join(nows) if nows else '-'}")

out.append("")
tn = sum(per[p]["NOUN"] for p in code_files)
tu = sum(per[p]["UNIT"] for p in code_files)
tz = sum(per[p]["ZH"] for p in code_files)
to = sum(per[p]["OTHER"] for p in code_files)
out.append(f"TOTALS over addendum code-side files: NOUN={tn} UNIT={tu} ZH={tz} OTHER={to} (addendum claimed 61 code-side)")
out.append(f"re-anchor hits={sum(per[p]['hit'] for p in code_files)} misses={sum(per[p]['miss'] for p in code_files)}")
out.append("")
out.append("=== NOUN rows with current-tip coordinates (each line: file:base_line -> current line | stem | text) ===")
for path in sorted(code_files, key=lambda p: (-per[p]["NOUN"], p)):
    for k, ol, hs, t, j in sorted(reanchor[path], key=lambda x: x[1]):
        if k != "NOUN":
            continue
        stem = re.search(r"[：:]\s*([A-Za-z][A-Za-z_ ]*\|[A-Za-z][A-Za-z_ ]*)", j)
        out.append(f"{path}:{ol} -> {path}:{','.join(str(h) for h in hs)} | stem={stem.group(1) if stem else j[:24]} | {t}")
out.append("")
out.append("=== misses (row text not found verbatim on the current tip) ===")
for c, k, t in miss:
    out.append(f"{c} | {k} | {t}")
if not miss:
    out.append("(none)")

txt = "\n".join(out)
sys.stdout.buffer.write(txt.encode("utf-8"))
with io.open(r"D:\moodle\_qoder_huomingxi_0558\wt\review\huomingxi\reslice_0558_r1.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write(txt + "\n")
