# -*- coding: utf-8 -*-
"""Read-only proof that batch r2 and batch r3 can land in either order on the live tip.

Uses `git merge-tree --write-tree`, which predicts a merge without touching any branch, and then
counts each of the six keys in the predicted tree: two dictionary sides plus one component read.
A collision would show up as a missing side or a zero use count, not as a message.
"""
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
TIP = "dde393326935dce66c7e7bd88cdab69af3e53985"
R2 = "43a0540a65399db767d3ae64322075300c935f14"
R3 = "a368e12313b505d444c871cb79375339f72a6c5c"
COMPONENT = "frontend/src/features/execution/LiveRecovery.tsx"
DICTIONARY = "frontend/src/i18n/LocaleContext.tsx"
KEYS = ["live.adjustTodayOnly", "live.remindMeLater", "live.nothingToDecide",
        "live.acknowledgedStillOpen", "live.confirmedUnchanged", "live.confirmedAffected"]


def sh(args):
    r = subprocess.run(["git", "-C", REPO] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def predicted(a, b):
    rc, out = sh(["merge-tree", "--write-tree", a, b])
    if rc != 0:
        raise SystemExit("MERGE_REFUSED rc=%d :: %s" % (rc, out[:200]))
    tree = out.splitlines()[0].strip()
    rc, _ = sh(["cat-file", "-t", tree])
    if rc != 0:
        raise SystemExit("NO_TREE_OBJECT %s" % tree)
    return tree


def commit_of(tree, parents):
    args = ["commit-tree", tree]
    for p in parents:
        args += ["-p", p]
    args += ["-m", "read-only landing prediction"]
    rc, out = sh(args)
    if rc != 0:
        raise SystemExit("COMMIT_TREE_FAILED :: %s" % out[:200])
    return out.strip()


order_a = commit_of(predicted(TIP, R2), [TIP, R2])
order_a = commit_of(predicted(order_a, R3), [order_a, R3])
order_b = commit_of(predicted(R2, R3), [R2, R3])
order_b = commit_of(predicted(TIP, order_b), [TIP, order_b])

bad = 0
for label, ref in (("tip->r2->r3", order_a), ("tip->(r2+r3)", order_b)):
    print("ORDER %s" % label)
    for key in KEYS:
        rc, dic = sh(["show", "%s:%s" % (ref, DICTIONARY)])
        rc2, comp = sh(["show", "%s:%s" % (ref, COMPONENT)])
        if rc != 0 or rc2 != 0:
            raise SystemExit("SHOW_FAIL %s" % ref)
        sides = dic.count('"%s"' % key)
        uses = comp.count('t("%s")' % key)
        print("  %s sides=%d uses=%d" % (key, sides, uses))
        if sides != 2 or uses != 1:
            bad += 1
print("keys=%d wrong=%d" % (len(KEYS) * 2, bad))
if bad:
    print("REFUSE one order loses a key -- do not tell the landing leg these are independent")
    sys.exit(4)
print("BOTH_ORDERS_CLEAN merge-tree rc=0 for every leg and all six keys keep two sides plus one read")
