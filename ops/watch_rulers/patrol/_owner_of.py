import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
L = io.open(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md", encoding="utf-8", errors="replace").read().split("\n")
heads = [(i + 1, l.strip()) for i, l in enumerate(L) if l.startswith("### ")]
for want in [int(x) for x in sys.argv[1:]]:
    owner = None
    for ln, h in heads:
        if ln <= want:
            owner = (ln, h)
        else:
            break
    print(":%d  属于块头 :%s  「%s」" % (want, owner[0], owner[1][:150]))
