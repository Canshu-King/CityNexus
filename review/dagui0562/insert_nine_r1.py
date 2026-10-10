import io, re, sys

P = "frontend/src/i18n/LocaleContext.tsx"
with io.open(P, "r", encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")

# the nine keys, in the order the ORD-0562 table lists them
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


def counts(rows):
    text = "\n".join(rows)
    i, j, k = text.index("const en: Dict"), text.index("const zhCN: Dict"), text.index("const dictionaries")
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


def close_index(start_pat):
    starts = [n for n, l in enumerate(lines) if l.startswith(start_pat)]
    assert len(starts) == 1, start_pat
    for n in range(starts[0] + 1, len(lines)):
        if lines[n] == "};":
            return n
    raise AssertionError("no close")


for k, en, zh in NINE:
    assert sum(1 for l in lines if l.startswith('  "%s":' % k)) == 0, "key already present: " + k

before = counts(lines)
for side, idx in (("en", close_index("const en: Dict")), ("zh", close_index("const zhCN: Dict"))):
    block = [u"  // ── ORD-0562 bare-key clearance, SimulationPanel stage (nine keys) ──"]
    for k, en, zh in NINE:
        block.append('  "%s": "%s",' % (k, en if side == "en" else zh))
    lines[idx:idx] = [u""] + block
after = counts(lines)
sys.stdout.write("en %d -> %d, zh %d -> %d\n" % (before[0], after[0], before[1], after[1]))
assert after[0] == before[0] + 9 and after[1] == before[1] + 9
sys.stdout.write("baseline two-side delta=%d\n" % (before[1] - before[0]))
for k, en, zh in NINE:
    assert sum(1 for l in lines if l.startswith('  "%s":' % k)) == 2, k
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(lines))
sys.stdout.write("OK nine_keys_on_both_sides=9\n")
sys.stdout.write("side_totals en=%d zh=%d equal=%d\n" % (after[0], after[1], int(after[0] == after[1])))
