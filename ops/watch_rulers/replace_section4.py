import io

P = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\block_deploy_2138.md"
NEW = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\section4_new.md"

t = io.open(P, encoding="utf-8", newline="\n").read()
lines = t.split("\n")
start = next(i for i, l in enumerate(lines) if l.startswith("#### \u2463"))
end = next(i for i, l in enumerate(lines[start + 1:], start + 1) if l.startswith("#### \u2464"))
old = "\n".join(lines[start:end]).rstrip("\n")
assert "14 \u6761" in old, old[:80]
new = io.open(NEW, encoding="utf-8", newline="\n").read().rstrip("\n")
out = "\n".join(lines[:start]) + "\n" + new + "\n" + "\n".join(lines[end:])
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("replaced %d chars with %d" % (len(old), len(new)))
print("section headers now:", [l[:26] for l in out.split("\n") if l.startswith("#### ")])
