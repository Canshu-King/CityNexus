"""F4's arm judged the wrong element, so its fields direction had nothing to bite.

`v13-2-review` is the role/confirm block; the interpretation line -- the one my F4 fix touched, and the one
whose machine fields the counter-arm strips -- is `v13-2-interpretation`. This step only *records* what that
block renders on the candidate (plus a stub fix so the interpretation is the draft's own), because an
assertion written against a string I have not read is a guess. The equality assertion comes next, against the
value this prints.
"""
from __future__ import annotations

import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SPEC = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend\e2e\qoder-ord0323-two-exposure-cells.spec.ts")
t = SPEC.read_text(encoding="utf-8")


def rep(old: str, new: str, want: int = 1) -> None:
    global t
    n = t.count(old)
    if n != want:
        raise SystemExit(f"expected {want}, found {n} for:\n{old[:200]}")
    t = t.replace(old, new)


# the stub draft now carries the interpretation fields the line reads
rep(
    """  extracted: {title: "天津西 → 北京南 高铁", reservation_type: "RAIL"},""",
    """  extracted: {title: "天津西 → 北京南 高铁", reservation_type: "RAIL", anchor_role: "MID_TRIP"},""",
)
rep(
    """  interpretation: {...draftRow.interpretation, reasoning_summary: F_SENTINELS.F4, payment_status: "PAID"},""",
    """  interpretation: {...draftRow.interpretation, reasoning_summary: F_SENTINELS.F4, payment_status: "PAID",
                   anchor_role_confidence: 0.8},
  extracted: {...draftRow.extracted, anchor_role: "MID_TRIP"},""",
)

# record, do not yet assert: what the interpretation block actually renders
rep(
    """  const review = clean(await page.getByTestId("v13-2-review").textContent());""",
    """  const review = clean(await page.getByTestId("v13-2-review").textContent());
  const interp = clean(await page.getByTestId("v13-2-interpretation").textContent().catch(() => ""));""",
)
rep(
    """    own_fields_present: review.includes("到站") || review.includes("MID_TRIP") || /0\\.8|80%/.test(review),""",
    """    interpretation_text: interp,
    interpretation_percent_field: (interp.match(/(\\d+)\\s*%/) || [null, ""])[1],
    own_fields_present: review.includes("到站") || review.includes("MID_TRIP") || /0\\.8|80%/.test(review),""",
)
SPEC.write_text(t, encoding="utf-8", newline="\n")
print("F4 instrument retargeted; interpretation text will now be recorded")
