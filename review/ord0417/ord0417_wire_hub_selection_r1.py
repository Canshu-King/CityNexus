"""ORD-0417 (hub slice): wire the hub's map into the same selection the map page already shares.

Three edits, all in `frontend/src/app/V8Experience.tsx`, and each one is anchored on text that occurs
exactly once so a silent mis-apply is impossible:

  1. the `<Hub …>` call site gains `selectedActivityId={detailActivityId}` and
     `onSelectActivity={setDetailActivityId}` -- the same pair `<MapPage …>` is given, from the same
     shell state, so a pin picked on Today is the same selection the map screen would show;
  2. `function Hub({…})` declares both, typed the way `MapPage` types them;
  3. the hub's `<MapPanel …>` forwards them.

Nothing in `MapPanel` changes: its pin already calls `selectRef.current?.(point.id ?? null)` and paints
`mapComp.selectedStopOnMap` when a selection exists.  The hub simply never handed it a callback, so the
optional call discarded every tap in silence.

usage: python ord0417_wire_hub_selection_r1.py <path to V8Experience.tsx> [--check-only]
"""
import sys

PATH = sys.argv[1]
CHECK_ONLY = "--check-only" in sys.argv

EDITS = [
    (
        """        onStageChanged={() => {
          void load(data.journey.id);
          void authoritativeTwin.refetch();
        }}
      />""",
        """        onStageChanged={() => {
          void load(data.journey.id);
          void authoritativeTwin.refetch();
        }}
        /* ORD-0417 (hub slice): Today's hero carries a real map with real pins, so a pin here has to
           answer the same way one on the map screen does.  The shell already owns this selection --
           `detailActivityId` is what `<MapPage>` reads and writes -- and handing the hub the same pair
           is what makes a tap visible instead of a no-op on a control that advertises `role="button"`. */
        selectedActivityId={detailActivityId}
        onSelectActivity={setDetailActivityId}
      />""",
    ),
    (
        """  onStageChanged,
}: {""",
        """  onStageChanged,
  selectedActivityId,
  onSelectActivity,
}: {""",
    ),
    (
        """  onStageChanged: () => void;
}) {
  const t = useT();""",
        """  onStageChanged: () => void;
  /** ORD-0417 (hub slice): the shared stop selection, owned by the shell.  `null` means nothing is
      picked, which the panel must be able to say out loud -- an unwired callback used to make every
      pin click vanish without a trace. */
  selectedActivityId: string | null;
  onSelectActivity: (id: string | null) => void;
}) {
  const t = useT();""",
    ),
    (
        """        <MapPanel
          data={data}
          option={selected}
          onNoLocationChange={setMapReportsNoLocation}
        />""",
        """        <MapPanel
          data={data}
          option={selected}
          onNoLocationChange={setMapReportsNoLocation}
          selectedActivityId={selectedActivityId}
          onSelectActivity={onSelectActivity}
        />""",
    ),
]

src = open(PATH, encoding="utf-8").read()
report = []
out = src
for old, new in EDITS:
    n = out.count(old)
    report.append({"anchor_hits": n, "first_line": old.split(chr(10))[0][:70]})
    if n != 1:
        for r in report:
            print(r)
        raise SystemExit(f"REFUSE: an anchor matched {n} times, expected exactly 1")
    out = out.replace(old, new, 1)

for r in report:
    print(r)
print(f"added {len(out) - len(src)} bytes; selectedActivityId hits: {out.count('selectedActivityId')}")
if CHECK_ONLY:
    print("check-only: nothing written")
else:
    open(PATH, "w", encoding="utf-8", newline=chr(10)).write(out)
    print("patched", PATH)
