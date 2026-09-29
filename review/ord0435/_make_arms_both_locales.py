"""Rewrite the five ORD-0435 arms so each body is registered twice, once per locale.

A text transform rather than five hand edits, because the point of the change is that the two arms
cannot drift: one body, two registrations. Bodies are found by their `test("Qn_` heads and the first
column-zero `});` after each, so nothing depends on line numbers typed by hand.
"""
import re
import sys
import pathlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = pathlib.Path("frontend/e2e/qoder-ord0435-poi-batch-multiselect.spec.ts")
lines = p.read_text(encoding="utf-8").split("\n")

heads = [i for i, l in enumerate(lines) if l.startswith('test("Q')]
assert len(heads) == 5, "expected 5 test heads, found %d" % len(heads)
tails = [next(i for i in range(h + 1, len(lines)) if lines[i] == "});") for h in heads]
assert tails == sorted(tails), "test bodies overlap -- file is not in the expected shape"

SWAPS = [
    ('toContain("承诺")', 'toContain(want(locale)("承诺", "commitment"))'),
    ('toContain("还没有")', 'toContain(want(locale)("还没有", "Not written to a day"))'),
]
swapped = 0
for a, b in SWAPS:
    for i, l in enumerate(lines):
        if a in l:
            lines[i] = l.replace(a, b)
            swapped += 1
print("locale-aware expectations rewritten: %d" % swapped)

out = list(lines)
# Back to front: inserting a registration shifts every line below it, so the earlier heads would
# otherwise point into the block just written (that is what made the first run crash on test #2).
for n, (h, t) in reversed(list(enumerate(zip(heads, tails), start=1))):
    head = out[h]
    title = re.match(r'test\("([^"]+)"', head).group(1)
    subject = title.split(" — ")[1]
    uses_request = "request }" in head
    params = "page: Page, locale: Locale, tag: string"
    if uses_request:
        params += ", request: APIRequestContext"
    out[t] = "}"
    out[h] = "async function q%d(%s) {" % (n, params)
    for i in range(h, t + 1):
        out[i] = out[i].replace('const arm = "Q%d";' % n, "const arm = `Q%d${tag}`;" % n)
    req_arg = ", request" if uses_request else ""
    register = "\n".join(
        [
            "for (const [locale, tag] of LOCALES) {",
            "  test(`Q%d${tag}_${locale} — %s`, async ({ page%s }) => {" % (n, subject, req_arg),
            "    test.setTimeout(480_000);",
            "    await q%d(page, locale, tag%s);" % (n, req_arg),
            "  });",
            "}",
        ]
    )
    out.insert(t + 1, register)

p.write_text("\n".join(out), encoding="utf-8", newline="")
text = "\n".join(out)
print("registered arms: %d" % len(re.findall(r"^  test\(`Q\d", text, re.M)))
print("body functions: %d" % len(re.findall(r"^async function q\d\(", text, re.M)))
