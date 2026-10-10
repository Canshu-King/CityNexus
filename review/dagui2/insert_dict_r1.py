import io, re, sys

P = "frontend/src/i18n/LocaleContext.tsx"
with io.open(P, "r", encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")

KEYS = {
    "en": [
        ("simulation.closeStage", "Close the stage"),
        ("simulation.onStage", "On stage"),
        ("simulation.sceneWindow", "Scene window"),
    ],
    "zh": [
        (u"simulation.closeStage", u"收起舞台"),
        (u"simulation.onStage", u"台上行程"),
        (u"simulation.sceneWindow", u"场景窗口"),
    ],
}
COMMENT = {"en": u"  // ── Simulation stage (inline bilingual fallbacks, ORD-0557) ──",
           "zh": u"  // ── 模拟舞台（内联双语兜底，ORD-0557） ──"}


def count_keys():
    text = "\n".join(lines)
    i = text.index("const en: Dict")
    j = text.index("const zhCN: Dict")
    k = text.index("const dictionaries")
    out = []
    for chunk in (text[i:j], text[j:k]):
        out.append(len(re.findall(r'^\s*"[^"]+":\s*"', chunk, re.M)))
    return out


def close_line(start_pat):
    starts = [n for n, l in enumerate(lines) if l.startswith(start_pat)]
    assert len(starts) == 1, start_pat
    for n in range(starts[0] + 1, len(lines)):
        if lines[n] == "};":
            return n
    raise AssertionError("no close for " + start_pat)


before = count_keys()
for side, start_pat in (("en", "const en: Dict"), ("zh", "const zhCN: Dict")):
    at = close_line(start_pat)
    block = [COMMENT[side]] + ['  "%s": "%s",' % (k, v) for k, v in KEYS[side]]
    lines[at:at] = [u""] + block
after = count_keys()
sys.stdout.write("keys_before en=%d zh=%d -> after en=%d zh=%d\n"
                 % (before[0], before[1], after[0], after[1]))
assert after[0] == before[0] + 3 and after[1] == before[1] + 3, "insert count mismatch"
for side in ("en", "zh"):
    for k, v in KEYS[side]:
        assert sum(1 for l in lines if l.startswith('  "%s":' % k)) == 2, k
        assert sum(1 for l in lines if l == '  "%s": "%s",' % (k, v)) == 1, (k, v)
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(lines))
sys.stdout.write("OK inserted_keys=%d per_side=3\n" % len(KEYS["en"]))
