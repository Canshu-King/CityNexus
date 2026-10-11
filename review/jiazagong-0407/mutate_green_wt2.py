"""Green control arm (加闸工, ORD-0407 slice 2): temporarily give the four census cells their own
button, so the same ruler that just read red is shown to move with the product. Nothing here is
committed -- the three product files are reverted by the caller right after the run.

Every anchor is counted before any write; the script refuses on a count other than 1."""

import io
import sys

FRONT = r"D:\moodle\_qoder_jiazagong_0407\wt2\frontend\src"
BUTTON = "<button type=\"button\">临时对照</button>"

EDITS = [
    (
        FRONT + r"\features\trip\SpendPanel.tsx",
        '            {t("spend.emptyBody", { unpriced: model.lines.length })}\n          </p>',
        '            {t("spend.emptyBody", { unpriced: model.lines.length })}\n          </p>\n          ' + BUTTON,
    ),
    (
        FRONT + r"\features\trip\SpendPanel.tsx",
        '            {t("spend.noLines")}\n          </p>',
        '            {t("spend.noLines")}\n          ' + BUTTON + "\n          </p>",
    ),
    (
        FRONT + r"\features\traveler-twin\TwinPanel.tsx",
        'return <p className="v8-empty-note">{t("twin.noCapabilityFacts")}</p>;',
        'return <p className="v8-empty-note">{t("twin.noCapabilityFacts")}' + BUTTON + "</p>;",
    ),
    (
        FRONT + r"\features\inbox\JourneyInboxWorkbench.tsx",
        '<p data-testid="inbox-pending-empty">{t("inbox.queueEmpty")}</p>',
        '<p data-testid="inbox-pending-empty">{t("inbox.queueEmpty")}' + BUTTON + "</p>",
    ),
]

for path, old, _new in EDITS:
    src = io.open(path, encoding="utf-8", newline="").read()
    n = src.count(old)
    if n != 1:
        print("ABORT anchor count %d in %s for %r" % (n, path, old[:60]))
        sys.exit(1)

for path, old, new in EDITS:
    src = io.open(path, encoding="utf-8", newline="").read()
    io.open(path, "w", encoding="utf-8", newline="").write(src.replace(old, new, 1))
    print("mutated", path.split("\\")[-1])
print("4 insertions done")
