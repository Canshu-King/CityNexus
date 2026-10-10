import io, sys

P = "frontend/src/features/simulation/SimulationPanel.tsx"
with io.open(P, "r", encoding="utf-8", newline="") as f:
    s = f.read()

edits = [
    (u'{zh ? "收起舞台" : "Close the stage"}', u'{t("simulation.closeStage")}'),
    (u'<dt>{zh ? "台上行程" : "On stage"}</dt>', u'<dt>{t("simulation.onStage")}</dt>'),
    (u'<dt>{zh ? "场景窗口" : "Scene window"}</dt>', u'<dt>{t("simulation.sceneWindow")}</dt>'),
]

bad = [(s.count(o), o[:40]) for o, n in edits if s.count(o) != 1]
if bad:
    for n, frag in bad:
        sys.stdout.write("ABORT hits=%d frag=%s\n" % (n, frag))
    sys.exit(3)

for old, new in edits:
    s = s.replace(old, new, 1)

for _, new in edits:
    assert new in s
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write(s)
sys.stdout.write("OK edits=%d\n" % len(edits))
