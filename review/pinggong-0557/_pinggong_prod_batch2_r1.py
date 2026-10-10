import io, sys

P = r"D:/moodle/_qoder_pinggong_0557/frontend/src/main.tsx"
s = io.open(P, encoding="utf-8").read()

OPS = [
    (': "no actionable target"}', ': t("main.noActionableTarget")}'),
    ('?? "outcome evidence"', '?? t("main.outcomeEvidence")'),
    ('?? "explicit wins"', '?? t("main.explicitWins")'),
    ('?? "not reported"', '?? t("main.notReported")'),
    ('?? "no upcoming activity"', '?? t("main.noUpcomingActivity")'),
    ('?? "No active C4"', '?? t("main.noActiveC4")'),
    ('? "not available"', '? t("main.notAvailable")'),
]

for old, new in OPS:
    n = s.count(old)
    if n != 1:
        sys.exit("ABORT needle %r hits=%d (need exactly 1)" % (old, n))
    s = s.replace(old, new, 1)
    print("ok", old[:44])

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("BATCH2_APPLIED=%d" % len(OPS))
