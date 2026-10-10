import io, sys

P = "frontend/src/features/simulation/SimulationPanel.tsx"
with io.open(P, "r", encoding="utf-8", newline="") as f:
    s = f.read()

K1 = "simulation.readsDidNotAnswerWhichIsNotTheSameAsNoSlot"
K2 = "simulation.theServerAnsweredWithProposalsStillOpenAcceptTheProposalBelowNowPointsAtAcceptingIsWhatChangesThePlan"
K3 = "simulation.theServerProducedProposalsButNoneOfTheItNowListsIsOpenSoAcceptTheProposalWillRefuseAndSayWhyOnItsOwnLine"
K4 = "simulation.now"
K5 = "simulation.thisActionIsUnavailableRightNow"
K6 = "simulation.thePreviousActionHasNotReturnedYet"

edits = [
    (u'一个都没给${bookableRead.data.unreadable ? `（另有 ${bookableRead.data.unreadable} 次没读到，那不是"没有时段"）` : ""}',
     u'一个都没给${bookableRead.data.unreadable ? t("%s", { n: bookableRead.data.unreadable }) : ""}' % K1),
    (u'no slot at all${bookableRead.data.unreadable ? ` (${bookableRead.data.unreadable} reads did not answer, which is not the same as "no slot")` : ""}',
     u'no slot at all${bookableRead.data.unreadable ? t("%s", { n: bookableRead.data.unreadable }) : ""}' % K1),
    (u'? `服务器回了 ${listed.length} 份方案，其中 ${open.length} 份还开着；下面「接受方案」那一行现在拿的是 ${shortId(open[0].id)}。接受才会换计划。`',
     u'? t("%s", { listed: listed.length, open: open.length, id: shortId(open[0].id) })' % K2),
    (u': `服务器回了方案，但它现在列出的 ${listed.length} 份里没有还开着的那一份，所以「接受方案」这一行会说不给按——理由在它自己那行。`',
     u': t("%s", { listed: listed.length })' % K3),
    (u'? `The server answered with ${listed.length} proposals, ${open.length} still open; "Accept the proposal" below now points at ${shortId(open[0].id)}. Accepting is what changes the plan.`',
     u'? t("%s", { listed: listed.length, open: open.length, id: shortId(open[0].id) })' % K2),
    (u': `The server produced proposals, but none of the ${listed.length} it now lists is open, so "Accept the proposal" will refuse and say why on its own line.`',
     u': t("%s", { listed: listed.length })' % K3),
    (u'zh: `服务器把信号夹具设为 OUTAGE${fixture?.state ? `（现值 ${fixture.state}）` : ""}。这只影响这台演示舞台，不是真实世界变了。`',
     u'zh: `服务器把信号夹具设为 OUTAGE${fixture?.state ? t("%s", { state: fixture.state }) : ""}。这只影响这台演示舞台，不是真实世界变了。`' % K4),
    (u'en: `The server set the signal fixture to OUTAGE${fixture?.state ? ` (now ${fixture.state})` : ""}. This moves the stage only, not the real world.`',
     u'en: `The server set the signal fixture to OUTAGE${fixture?.state ? t("%s", { state: fixture.state }) : ""}. This moves the stage only, not the real world.`' % K4),
    (u'zh: `服务器把信号夹具设回 NORMAL${fixture?.state ? `（现值 ${fixture.state}）` : ""}。`',
     u'zh: `服务器把信号夹具设回 NORMAL${fixture?.state ? t("%s", { state: fixture.state }) : ""}。`' % K4),
    (u'en: `The server returned the fixture to NORMAL${fixture?.state ? ` (now ${fixture.state})` : ""}.`',
     u'en: `The server returned the fixture to NORMAL${fixture?.state ? t("%s", { state: fixture.state }) : ""}.`' % K4),
    (u'? `这个动作现在做不了：${row.blocked.zh}`',
     u'? t("%s", { reason: row.blocked.zh })' % K5),
    (u': "上一个动作还没回来，先等它。",',
     u': t("%s"),' % K6),
    (u'? `This action is unavailable right now: ${row.blocked.en}`',
     u'? t("%s", { reason: row.blocked.en })' % K5),
    (u': "The previous action has not returned yet.",',
     u': t("%s"),' % K6),
]

bad = []
for old, new in edits:
    n = s.count(old)
    if n != 1:
        bad.append((n, old[:60]))
if bad:
    for n, frag in bad:
        sys.stdout.write("ABORT hits=%d frag=%s\n" % (n, frag))
    sys.exit(3)

for old, new in edits:
    s = s.replace(old, new, 1)

with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write(s)
sys.stdout.write("OK edits=%d\n" % len(edits))
