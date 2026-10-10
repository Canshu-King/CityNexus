import io, re, subprocess

T = "65897e97a139c59279041fabe1d7413a5a9d537f"
WT = r"D:/moodle/_qoder_pinggong_0557"
OUT = WT + "/review/pinggong-0557/main_bilingual_face_r1.txt"

src = subprocess.run(["git", "-C", WT, "show", "%s:frontend/src/main.tsx" % T],
                     capture_output=True).stdout.decode("utf-8").split("\n")

HAN = re.compile(r"[㐀-鿿]")
TERNARY = re.compile(r'\?\s*"([^"]*)"\s*:\s*"([^"]*)"')

L = ["# real-character test of the 3 rows the byte-range ruler counted in frontend/src/main.tsx at %s" % T]
r = subprocess.run(["git", "-C", WT, "grep", "-n", "-E",
                    r'\?\s*"[^"]*[一-龥][^"]*"\s*:\s*"', T, "--", "frontend/src/main.tsx"],
                   capture_output=True)
byte_hits = sorted({int(x.split(":", 3)[2]) for x in r.stdout.decode("utf-8", "replace").splitlines() if x})
L.append("byte-range hits counted by the dispatch ruler: %s" % (byte_hits or "none"))
real = 0
for n in byte_hits or []:
    line = src[n - 1]
    m = TERNARY.search(line)
    zh_side = m.group(1) if m else ""
    has_han = bool(HAN.search(line))
    if has_han:
        real += 1
    L.append("row frontend/src/main.tsx:%d | branch_before_colon=%r | contains_real_hanzi=%s" % (n, zh_side[:24], has_han))
L.append("rows_with_real_hanzi_branch=%d out of %d counted" % (real, len(byte_hits)))
L.append("draft judgement for this file (zero takeable rows) is at _cn10_bldraft_1155.txt:212")
io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("\n".join(L))
