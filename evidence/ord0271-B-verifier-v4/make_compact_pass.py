"""Publish the compact copy of the pass driver into the MCP-allowed directory.

The Playwright tool echoes the whole file it executes, so a 40-line documented driver costs the same again in
every one of the nine readings. This keeps the documented file in the lab and puts a comment-free copy where the
sandbox reads it, and it proves the two are one instrument rather than two: strip comment and blank lines from
both, and the normalised sha256 must be equal. That hash is written into the copy's own header.
"""
import hashlib
import pathlib

LAB = pathlib.Path(r"D:\moodle\_qoder_harness_ord0254\tools\q8b_pass.js")
MCP = pathlib.Path(r"C:\Users\仓鼠王\cnx0271b\q8b_pass.js")


def norm(text: str) -> str:
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        out.append(line)
    return "\n".join(out)


lab = LAB.read_text(encoding="utf-8")
n_lab = norm(lab)
header = (
    "// ORD-0271-B pass driver, compact copy. Executable bytes are identical to the lab file\n"
    "// tools/q8b_pass.js with its comment lines removed; the normalised sha256 below is computed the same way\n"
    "// over both files, which is what makes this a copy rather than a second instrument.\n"
    "// normalised sha256 = " + hashlib.sha256(n_lab.encode("utf-8")).hexdigest() + "\n"
)
compact = header + n_lab + "\n"
MCP.write_bytes(compact.encode("utf-8"))
assert norm(compact) == n_lab, "normalised code drifted"
print("lab sha256            ", hashlib.sha256(lab.encode("utf-8")).hexdigest()[:16])
print("compact sha256        ", hashlib.sha256(compact.encode("utf-8")).hexdigest()[:16])
print("normalised (both)     ", hashlib.sha256(n_lab.encode("utf-8")).hexdigest()[:16])
print("compact bytes", len(compact.encode("utf-8")), "->", MCP)
