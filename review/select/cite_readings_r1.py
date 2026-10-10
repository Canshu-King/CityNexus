"""Print the files this lane cites, with their line numbers.

The relay gate refuses a block whose numbers appear in no evidence output -- including
the line numbers the block points at. Printing the file content without its line numbers
satisfies neither, so this emits numbered lines for the readings dump, the claim scan,
and the one standing rule the block quotes from the ledger.
"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = [
    os.path.join(HERE, "select_readings_1009.txt"),
    os.path.join(HERE, "claim_scan_0547_2340.txt"),
    (r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md", (1112,)),
]

for entry in TARGETS:
    if isinstance(entry, tuple):
        path, wanted = entry
    else:
        path, wanted = entry, None
    print("===== %s" % path.replace("\\", "/"))
    with io.open(path, encoding="utf-8", errors="replace") as handle:
        for number, line in enumerate(handle, start=1):
            if wanted is not None and number not in wanted:
                continue
            print("%d: %s" % (number, line.rstrip()))
