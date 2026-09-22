"""Add the ORD-0209 kill mutant to the harness: restoring the creation POSTs must turn the gate red.

The order asks for this mutant specifically and for the anchor to be guarded by
`live_checks/mutation_anchor_guard.py` semantics -- a 0-hit anchor or a byte-identical write is a
false verdict, and both are refused mechanically (the harness's own `anchor hits`/`on_disk` print
plus the skip path below already do this; this script only adds the case).

Written as a file because the anchors carry escaped quotes a heredoc mangles.
"""

import io

PATH = "D:/moodle/_qoder_integration_20260919/review/ord0082_0087_kill_drivers.py"

CONST_OLD = 'TONGUE_SPEC = "e2e/qoder-speaks-the-travellers-language.spec.ts"\n'
CONST_NEW = CONST_OLD + 'DEMO_SPEC = "e2e/qoder-demo-entry-addresses-dont-create.spec.ts"\n'

TAIL_OLD = (
    '        [(TONGUE_SPEC, ["ord0208-the-day-card-speaks-the-language-the-screen-uses"])],\n'
    "    ),\n"
    "]\n"
)

TAIL_NEW = (
    '        [(TONGUE_SPEC, ["ord0208-the-day-card-speaks-the-language-the-screen-uses"])],\n'
    "    ),\n"
    "    (\n"
    "        # ORD-0209: the exact defect the arbitration ruled on -- the entry creates a traveller\n"
    "        # and a journey again.  The seed of the old body is restored in front of the addressing\n"
    "        # branch, so the network-count gate must go red on it.\n"
    '        "killT1-demo-entry-creates-again",\n'
    "        EXPERIENCE,\n"
    '        "      const sealedId = scene.journey_id ?? null;\\n",\n'
    '        "      await v8Request<{ id: string }>(\\"/api/v1/travelers\\", { method: \\"POST\\", body: JSON.stringify({ display_name: \\"City traveler\\" }) });\\n"\n'
    '        "      await v8Request<{ id: string }>(\\"/api/v1/journeys\\", { method: \\"POST\\", body: JSON.stringify({ title: \\"Tianjin demo\\" }) });\\n"\n'
    '        "      const sealedId = scene.journey_id ?? null;\\n",\n'
    '        [(DEMO_SPEC, ["ord0209-the-demo-entry-addresses-the-sealed-journey"])],\n'
    "    ),\n"
    "]\n"
)


def main() -> int:
    text = io.open(PATH, encoding="utf-8", newline="").read()
    for old, new, label in ((CONST_OLD, CONST_NEW, "const"), (TAIL_OLD, TAIL_NEW, "tail")):
        count = text.count(old)
        if count != 1:
            print(f"ABORT: {label} anchor appears {count} times, expected 1")
            return 2
        text = text.replace(old, new, 1)
    io.open(PATH, "w", encoding="utf-8", newline="").write(text)
    after = io.open(PATH, encoding="utf-8", newline="").read()
    print(f"killT1={'killT1' in after} DEMO_SPEC={'DEMO_SPEC' in after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
