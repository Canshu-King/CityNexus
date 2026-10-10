import io, re, subprocess, sys

WT = r"D:/moodle/_qoder_pinggong_0555"
OUT = WT + "/review/pinggong-0555/sceneclock_face_r1.txt"
tip = subprocess.run(["git", "-C", WT, "ls-remote", "origin",
                      "refs/heads/mirror/integration-frontend-apple-pass1"],
                     capture_output=True, text=True).stdout.split()[0]

rel = "frontend/src/lib/sceneClock.ts"
src = subprocess.run(["git", "-C", WT, "show", "%s:%s" % (tip, rel)],
                     capture_output=True).stdout.decode("utf-8").split("\n")

CJK = re.compile(r"[㐀-鿿]")
TER = re.compile(r'\?\s*"([^"]*)"\s*:\s*"([^"]*)"')

L = ["# sceneClock face, re-measured per the broadcast ruler's predicate (two literals, exactly one side CJK)"]
L.append("tip=%s file_lines=%d" % (tip, len(src)))
hits = []
for i, s in enumerate(src, 1):
    for m in TER.finditer(s):
        a, b = m.group(1), m.group(2)
        ca, cb = bool(CJK.search(a)), bool(CJK.search(b))
        if ca != cb:
            hits.append((i, a, b, "zh" if ca else "en"))
            break
L.append("hits=%d" % len(hits))
for i, a, b, side in hits:
    L.append("frontend/src/lib/sceneClock.ts:%d | branch_a=%r | branch_b=%r | cjk_side=%s" % (i, a, b, side))
io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("HITS=%d tip=%s" % (len(hits), tip))
for i, a, b, side in hits:
    print(i, repr(a)[:40], repr(b)[:40], side)
