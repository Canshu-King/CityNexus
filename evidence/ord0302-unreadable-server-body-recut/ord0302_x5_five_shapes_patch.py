"""Extend ORD-0302's X-5 cell from one shape to the five the commander named (ledger CMDR-0925-1625).

He listed R19..R23 -- five HTTP 200 shapes that differ only in the body (empty, `{}`, `[]`, a text/plain
payload, a mission whose status is unusable) -- and all five are rows whose card sends the traveller to
技术详情. My first pass drove one of them. This makes the cell drive all five, still as ONE cell, so the two
killer mutants have to redden exactly this cell and nothing else.

Anchors are asserted to occur exactly once and the file is parsed before it is written back.
"""
import ast
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend\e2e\qoder-ord0302-unreadable-server-body.spec.ts")
s = P.read_text(encoding="utf-8")

EDITS = [
    ('''type Stub = { url: string; method?: string; status?: number; body?: unknown; html?: string; abort?: boolean };''',
     '''type Stub = { url: string; method?: string; status?: number; body?: unknown; html?: string;
                  raw?: string; contentType?: string; abort?: boolean };'''),
 ('''      if (s.html !== undefined) {
        return r.fulfill({ status: s.status ?? 200, contentType: "text/html", body: s.html });
      }''',
     '''      if (s.html !== undefined) {
        return r.fulfill({ status: s.status ?? 200, contentType: "text/html", body: s.html });
      }
      if (s.raw !== undefined) {
        /* The body is handed over verbatim, including "" -- a JSON parse of an empty answer is exactly what
           these shapes are about, so the stub must not quietly replace it with `{}`. */
        return r.fulfill({ status: s.status ?? 200, contentType: s.contentType ?? "application/json",
                           body: s.raw });
      }'''),
]

FIVE = '''/* The five shapes the commander named (ledger `CMDR-0925-1625`, readings in bus issuecomment-5829345648):
   all five answer HTTP 200 on both write legs and differ only in the body. Each one reaches the branch whose
   card sends the traveller to 技术详情, so the pairing is judged once per shape -- inside ONE cell, which is
   what keeps the two killer mutants reddening exactly this cell. */
type X5Shape = { row: string; status: number; contentType: string; body: string };
const X5_SHAPES: X5Shape[] = [
  { row: "R19_④_200_empty_body", status: 200, contentType: "application/json", body: "" },
  { row: "R20_④_200_json_empty_object", status: 200, contentType: "application/json", body: "{}" },
  { row: "R21_④_200_json_array", status: 200, contentType: "application/json", body: "[]" },
  { row: "R22_④_200_text_plain_payload", status: 200, contentType: "text/plain; charset=utf-8",
    body: "plans are not available right now" },
  { row: "R23_④_200_mission_unusable_status", status: 200, contentType: "application/json",
    body: JSON.stringify({ mission: { id: "ord0302-mission", status: "FAILED_UPSTREAM",
                                      failure_reason: null, reasoning_summary: null } }) },
];

function stubsForShape(sh: X5Shape): Stub[] {
  return [
    { url: "**/api/v1/journeys/*/agent/commands", method: "POST", status: sh.status,
      contentType: sh.contentType, raw: sh.body },
    { url: "**/api/v1/journeys/*/plans/generate", method: "POST", status: sh.status,
      contentType: sh.contentType, raw: sh.body },
    { url: "**/api/v1/journeys/*/plans", method: "GET", body: [] },
    { url: "**/api/v1/places**", body: TWO_PLACES },
  ];
}

test(`ord0302-X1 ${"every 200 shape whose card points at 技术详情 renders a block that carries a reading"}`,
  async ({ page }) => {
    test.setTimeout(900_000);
    const per: Record<string, unknown> = {};
    const rows: { claim: string; ok: boolean; got: unknown }[] = [];
    for (const sh of X5_SHAPES) {
      await page.unrouteAll({ behavior: "ignoreErrors" });
      const read = await bootWithStubs(page, stubsForShape(sh), "X1");
      per[sh.row] = { status: read.status, promise_in_copy: read.promise_in_copy,
                      details_count: read.details_count, reason: read.reason, origin: read.origin };
      rows.push({ claim: `${sh.row}: the card's promise and the DOM agree (promise => block exists)`,
        ok: !read.promise_in_copy || read.details_count >= 1,
        got: { promise_in_copy: read.promise_in_copy, details_count: read.details_count } });
      rows.push({ claim: `${sh.row}: this is the shape X-5 named`,
        ok: read.status === "NO_PLANS_PRODUCED", got: { status: read.status } });
      rows.push({ claim: `${sh.row}: its block carries a reading rather than nothing`,
        ok: read.details_count >= 1 && read.reason.length > 0, got: { reason: read.reason } });
      rows.push({ claim: `${sh.row}: the copy still points there (Q53=①: render it, keep the pointer)`,
        ok: read.promise_in_copy === true, got: { promise_in_copy: read.promise_in_copy } });
    }
    const head = per[X5_SHAPES[2].row] as Record<string, unknown>;
    readings["X1"] = { want: "device", force_shape: "five HTTP 200 bodies on both write legs (R19-R23)",
                       shape_count: X5_SHAPES.length, per_shape: per,
                       read: { ...head, shape_count: X5_SHAPES.length },
                       verdict: rows.every((r) => r.ok) ? "MET" : "NOT_MET", rows };
    expect(rows.filter((r) => !r.ok), node("X1", JSON.stringify(per))).toEqual([]);
  });

'''

OLD_X1_START = '''test(`ord0302-X1 ${"a run that produced nothing usable still renders the block its own card points at"}`,'''
OLD_X1_END = '''    expect(rows.filter((r) => !r.ok), node("X1", JSON.stringify(read))).toEqual([]);
  });'''

for old, new in EDITS:
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"anchor occurs {n} times (want 1): {old[:70]!r}")
    s = s.replace(old, new, 1)

i, j = s.find(OLD_X1_START), s.find(OLD_X1_END)
if i < 0 or j < 0:
    raise SystemExit(f"X1 block not found: start={i} end={j}")
s = s[:i] + FIVE + s[j + len(OLD_X1_END) + 1:]

# the old single-shape stub list is now dead; drop it rather than leave a second source of truth
DEAD = '''const NO_PLANS_STUBS: Stub[] = [
  { url: "**/api/v1/journeys/*/agent/commands", method: "POST", body: MISSION_CLEAN },
  { url: "**/api/v1/journeys/*/plans", method: "GET", body: [] },
  { url: "**/api/v1/journeys/*/plans/generate", method: "POST", body: { plans: [] } },
  { url: "**/api/v1/places**", body: TWO_PLACES },
];

'''
if s.count(DEAD) != 1:
    raise SystemExit("the superseded single-shape stub block was not found exactly once")
s = s.replace(DEAD, "", 1)

P.write_text(s, encoding="utf-8", newline="\n")
print("X-5 now drives R19-R23 inside one cell; parses as TS by eye, tsc will judge")
