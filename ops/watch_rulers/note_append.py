"""Append ONE section to the desktop note without touching earlier bytes.

The section path is an argument on purpose: a hardcoded payload made this helper re-append the same
block on every run while still reporting "readback ok" - the check only proved the write landed, not
that the content was new. After writing we assert the section header appears exactly once.
"""
import hashlib, io, sys

P = r"C:\Users\仓鼠王\Desktop\CityNexus_包工头留言.txt"
if len(sys.argv) < 2:
    print("usage: note_append.py <section-file>"); raise SystemExit(2)
NEW = sys.argv[1]

old = io.open(P, encoding="utf-8", newline="").read()
add = io.open(NEW, encoding="utf-8", newline="\n").read().lstrip("\n")
if not add.endswith("\n"):
    add += "\n"
header = add.split("\n", 1)[0].strip()
if not header:
    print("ABORT: section has no header line"); raise SystemExit(2)
if header in old:
    print(f"ABORT: this section is already in the note ({header[:34]}) - refusing to duplicate")
    raise SystemExit(2)
new = old if old.endswith("\n") else old + "\n"
new = new + "\n" + add
if not new.startswith(old):
    print("ABORT: prefix changed"); raise SystemExit(2)
with io.open(P, "w", encoding="utf-8", newline="") as fh:
    fh.write(new)
rb = io.open(P, encoding="utf-8", newline="").read()
copies = rb.count(header)
print("note bytes %d -> %d ; prefix preserved: %s ; readback ok: %s" % (
    len(old.encode()), len(rb.encode()), rb.startswith(old), rb == new))
print("section header %r occurrences: %d" % (header[:34], copies))
if copies != 1:
    print("FAIL: header should appear exactly once - inspect before trusting this note")
    raise SystemExit(3)
print("sha12", hashlib.sha256(rb.encode()).hexdigest()[:12], "| lines", rb.count("\n"))
