"""Prepend a timestamped block to the user's desktop note without rewriting history.

Asserts before writing (this file is the only thing the user reads in the morning):
 * the note is LF-only (a CRLF flip from write_text is a known trap here);
 * the new URL appears exactly once in the block and zero times in the old body;
 * the previous newest address line is still present afterwards, so nothing was overwritten.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
NOTE = r"C:\Users\仓鼠王\Desktop\CityNexus_包工头留言.txt"
BLOCK = r"D:\moodle\_qoder_preview_20260920\run\_desk_note_head_0934.txt"

old = io.open(NOTE, "rb").read()
block = io.open(BLOCK, "rb").read()
assert b"\r\n" not in old, "note already has CRLF - stop, do not double-convert"
assert b"\r\n" not in block, "block has CRLF - write it LF-only"
assert block.endswith(b"\n"), "block must end with a newline so line 1 stays intact"

new_url = [l for l in block.decode("utf-8").splitlines() if "trycloudflare.com" in l]
assert len(new_url) == 1, f"expected exactly one URL line in the block, got {len(new_url)}"
url = new_url[0].strip()
# A new deployment does NOT always mint a new address: at 05:1x the tunnel stayed the same and only the
# served GENERATION changed.  The original assert assumed "prepend == address change" and refused, which
# would have pushed me into hand-editing the one file the user reads.  So: an unchanged address is allowed
# only when the block says so with a `#URL-UNCHANGED` marker, and then the count must grow by exactly one.
declared_unchanged = any(l.strip() == "#URL-UNCHANGED" for l in block.decode("utf-8").splitlines())
if old.count(url.encode()) == 0:
    pass
elif declared_unchanged:
    print("note: address unchanged (declared); the block documents a generation swap on the same URL")
else:
    raise AssertionError("the new URL is already in the body - refusing to duplicate "
                         "(add a '#URL-UNCHANGED' marker line if the address really did not change)")
head_before = old.decode("utf-8").splitlines()[0]
# the marker is machine-facing; the note is the one file a human reads, so it is stripped before writing
block = b"".join(l.encode("utf-8") + b"\n" for l in block.decode("utf-8").splitlines()
                 if l.strip() != "#URL-UNCHANGED")
out = block + old
assert out.count(url.encode()) == old.count(url.encode()) + 1, "URL count must grow by exactly one"
assert head_before.encode() in out, "previous newest note line disappeared"
assert len(out) == len(old) + len(block), "size did not grow by exactly the block"
io.open(NOTE, "wb").write(out)
print(f"prepended {len(block)} B onto {len(old)} B -> {len(out)} B")
print("first line now:", out.decode('utf-8').splitlines()[0][:70])
print("second line now:", out.decode('utf-8').splitlines()[1][:80])
print("previous first line preserved:", head_before[:56] in out.decode("utf-8"))
print("mtime:", time_ := os.path.getmtime(NOTE))
