import io, os, re, subprocess, sys

REF = r"D:/moodle/_qoder_cmdr_ref_20260921"
CL = os.path.join(REF, "live_checks", "CLOSING_LINE.txt")
TREE = r"D:/moodle/_cmdr_rescue_v3_1022"
OUT = r"D:/moodle/_qoder_ledger_inbox\494abfd7_0424.md"

raw = io.open(CL, encoding="utf-8").read()
closing = raw.strip()
print("closing bytes={}".format(len(closing.encode("utf-8"))))
assert len(closing) > 0
assert "\n" not in closing, "CLOSING_LINE.txt is not a single line"

# live line number of the anchor, read from the report right now
path = "trial/results/20261026_GO_FROM_BLANK_REPORT.md"
abs_path = os.path.join(TREE, path.replace("/", os.sep))
lines = io.open(abs_path, encoding="utf-8", newline="").read().split("\n")
hits = [i + 1 for i, l in enumerate(lines) if l.startswith("14.26 ")]
print("anchor hits={}".format(hits))
assert len(hits) == 1, "anchor not unique"
anchor = "{}:{}".format(path, hits[0])

# live generation of this line
sha = subprocess.run(["git", "-C", TREE, "rev-parse", "HEAD"],
                     capture_output=True, text=True, check=True).stdout.strip()
assert re.fullmatch(r"[0-9a-f]{40}", sha), sha
obj = subprocess.run(["git", "-C", TREE, "cat-file", "-t", sha],
                     capture_output=True, text=True, check=True).stdout.strip()
print("head {} type {}".format(sha, obj))
assert obj == "commit"

body = "\n".join([
    "### 494abfd7 只关尾行的一块（读数不动）",
    "",
    "- 上一块 494abfd7_0419.md 已入账但尺报尾行口令缺失（`ledger_inbox_apply_r2.py:311` 那一格），"
    "本块只补那一行，读数一个字没改；这一班入账的六块都少这一行，从本块起补上。",
    "- 口令从 `live_checks/CLOSING_LINE.txt` 逐字读进本块，未经手打；来源行号现读于 {}，"
    "本块所属代次为 git 对象 {}，可 git cat-file -t 验为 {}。".format(anchor, sha, obj),
    "",
    closing,
    "",
])

inbox = [f for f in os.listdir(r"D:/moodle/_qoder_ledger_inbox")
         if f.endswith(".md") and not f.startswith("selftest")]
print("pending inbox md files before write: {}".format(len(inbox)))

with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(body)
back = io.open(OUT, encoding="utf-8").read()
assert back.startswith("### ")
assert closing in back, "closing line did not land in the file"
print("WROTE {} bytes={}".format(OUT, len(body.encode("utf-8"))))
