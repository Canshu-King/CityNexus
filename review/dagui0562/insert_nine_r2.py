import io, re, sys

P = "frontend/src/i18n/LocaleContext.tsx"
with io.open(P, "r", encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")

NINE = [
    ("simulation.closeStage", "Close the stage", u"收起舞台"),
    ("simulation.now", " (now {state})", u"（现值 {state}）"),
    ("simulation.onStage", "On stage", u"台上行程"),
    ("simulation.readsDidNotAnswerWhichIsNotTheSameAsNoSlot",
     ' ({n} reads did not answer, which is not the same as \\"no slot\\")',
     u'（另有 {n} 次没读到，那不是\\"没有时段\\"）'),
    ("simulation.sceneWindow", "Scene window", u"场景窗口"),
    ("simulation.thePreviousActionHasNotReturnedYet",
     "The previous action has not returned yet.", u"上一个动作还没回来，先等它。"),
    ("simulation.theServerAnsweredWithProposalsStillOpenAcceptTheProposalBelowNowPointsAtAcceptingIsWhatChangesThePlan",
     'The server answered with {listed} proposals, {open} still open; \\"Accept the proposal\\" below now points at {id}. Accepting is what changes the plan.',
     u"服务器回了 {listed} 份方案，其中 {open} 份还开着；下面「接受方案」那一行现在拿的是 {id}。接受才会换计划。"),
    ("simulation.theServerProducedProposalsButNoneOfTheItNowListsIsOpenSoAcceptTheProposalWillRefuseAndSayWhyOnItsOwnLine",
     'The server produced proposals, but none of the {listed} it now lists is open, so \\"Accept the proposal\\" will refuse and say why on its own line.',
     u"服务器回了方案，但它现在列出的 {listed} 份里没有还开着的那一份，所以「接受方案」这一行会说不给按——理由在它自己那行。"),
    ("simulation.thisActionIsUnavailableRightNow",
     "This action is unavailable right now: {reason}", u"这个动作现在做不了：{reason}"),
]

KEY = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')


def side_counts(rows):
    text = "\n".join(rows)
    i = text.index("const en: Dict")
    j = text.index("const zhCN: Dict")
    k = text.index("const dictionaries")
    out = []
    for ch in (text[i:j], text[j:k]):
        n = 0
        for line in ch.split("\n"):
            s = line.strip()
            if s.startswith("//") or s.startswith("*"):
                continue
            if KEY.match(line):
                n += 1
        out.append(n)
    return out


def close_index(rows, start_pat):
    starts = [n for n, l in enumerate(rows) if l.startswith(start_pat)]
    assert len(starts) == 1, start_pat
    for n in range(starts[0] + 1, len(rows)):
        if rows[n] == "};":
            return n
    raise AssertionError("no close for " + start_pat)


def comment_span(rows, idx):
    """how many open /* blocks sit above this insertion point"""
    text = "\n".join(rows[:idx])
    return text.count("/*") - text.count("*/")


for k, en, zh in NINE:
    assert sum(1 for l in lines if l.startswith('  "%s":' % k)) == 0, "already there: " + k

before = side_counts(lines)
# insert the later block first, and recompute the earlier index afterwards
zh_at = close_index(lines, "const zhCN: Dict")
assert comment_span(lines, zh_at) == 0, "zh insertion point is inside a comment"
zh_block = [u"  // ── ORD-0562 bare-key clearance, SimulationPanel stage (nine keys) ──"]
zh_block += ['  "%s": "%s",' % (k, zh) for k, en, zh in NINE]
lines[zh_at:zh_at] = [u""] + zh_block

en_at = close_index(lines, "const en: Dict")
assert comment_span(lines, en_at) == 0, "en insertion point is inside a comment"
en_block = [u"  // ── ORD-0562 bare-key clearance, SimulationPanel stage (nine keys) ──"]
en_block += ['  "%s": "%s",' % (k, en) for k, en, zh in NINE]
lines[en_at:en_at] = [u""] + en_block

after = side_counts(lines)
sys.stdout.write("en %d -> %d, zh %d -> %d\n" % (before[0], after[0], before[1], after[1]))
assert after[0] == before[0] + 9 and after[1] == before[1] + 9, "count mismatch"
for k, en, zh in NINE:
    hits = [n + 1 for n, l in enumerate(lines) if l.startswith('  "%s":' % k)]
    assert len(hits) == 2, (k, hits)
assert comment_span(lines, close_index(lines, "const en: Dict")) == 0
assert comment_span(lines, close_index(lines, "const zhCN: Dict")) == 0
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(lines))
sys.stdout.write("OK nine_on_both_sides=%d inserted_after_recount=1 comment_free=1\n" % len(NINE))
