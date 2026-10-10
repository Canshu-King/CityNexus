"""Fix the route plumbing in measureCell (加闸工). Anchors are counted before anything is written, and
the script refuses to touch the file unless every count is what it expects."""

import io
import sys

P = r"D:\moodle\_qoder_jiazagong_0407\wt\frontend\e2e\qoder-ord0407-empty-state-actions.spec.ts"
s = io.open(P, encoding="utf-8", newline="").read()

want = {
    "  async function measureCell(page: Page, cell: (typeof CENSUS_CELLS)[number]) {": 1,
    "          const [sel, txt] = arg;": 1,
    "            route,": 1,
    "[cell.locator, cell.expect_text],": 1,
    "await measureCell(page, cell)": 4,
}
bad = {k: (s.count(k), want[k]) for k in want if s.count(k) != want[k]}
if bad:
    print("ABORT anchor counts:", bad)
    sys.exit(1)

s = s.replace("  async function measureCell(page: Page, cell: (typeof CENSUS_CELLS)[number]) {",
              "  async function measureCell(page: Page, cell: (typeof CENSUS_CELLS)[number], route: string) {", 1)
s = s.replace("          const [sel, txt] = arg;", "          const [sel, txt, rt] = arg;", 1)
s = s.replace("            route,", "            route: rt,", 1)
s = s.replace("[cell.locator, cell.expect_text],", "[cell.locator, cell.expect_text, route],", 1)
s = s.replace("await measureCell(page, cell)", "await measureCell(page, cell, route)")

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("APPLIED plumbing; bare callsites left:", s.count("measureCell(page, cell)"),
      "| fixed callsites:", s.count("measureCell(page, cell, route)"),
      "| braces", s.count("{") - s.count("}"), "| parens", s.count("(") - s.count(")"))
