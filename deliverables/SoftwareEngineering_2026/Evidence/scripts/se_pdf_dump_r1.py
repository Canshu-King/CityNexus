import sys, io
from pypdf import PdfReader

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

paths = [
    r"D:\moodle\02 Software Engineering\Software Engineering - Assignment Coursework 2026.pdf",
]
for p in paths:
    r = PdfReader(p)
    print("=== FILE:", p)
    print("=== PAGES:", len(r.pages))
    for i, pg in enumerate(r.pages):
        t = pg.extract_text() or ""
        print("\n----- PAGE %d -----" % (i + 1))
        print(t.strip())
