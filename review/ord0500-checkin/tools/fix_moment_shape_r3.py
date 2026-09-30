"""The instant keeps the shape these surfaces already use.

My first cut of the screen-local renderer asked for `month: "numeric"`, and zh-CN answers that with
`10/1`; the month the traveller reads on this screen is `10月1日`, which is what `month: "short"`
produces there (and `1 Oct` in en-GB).  The order's own carrier caught it: `ord0500-1` went red with
「the refusal does not point at the stamp that already won」, because the moment no longer matched the
shape it asserts.  Fixing the shape, not the assertion.
"""
import hashlib
import os

LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(LANE, "wt16", "frontend", "src", "features", "checkin", "checkinCopy.ts")
NL = chr(10)
text = open(PATH, encoding="utf-8", newline="").read()
OLD = '    month: "numeric",'
NEW = '    month: "short",'
if text.count(OLD) != 1:
    raise SystemExit("ABORT_MONTH_OPTION_ANCHOR %d" % text.count(OLD))
text = text.replace(OLD, NEW)
extra = NL.join([
    " * The option that matters is the month shape: `numeric` makes zh-CN answer `10/1`, while these",
    " * surfaces show `10月1日` (`short`), and the order's carrier asserts that shape -- so the assertion",
    " * is the thing that reddened when I first wrote `numeric`, and this renderer is what changed.",
    "",
])
marker = " * An instant the door did not send renders as an empty string"
if text.count(marker) != 1:
    raise SystemExit("ABORT_COMMENT_ANCHOR")
text = text.replace(marker, extra.lstrip(NL) + " " + marker)
open(PATH, "w", encoding="utf-8", newline="").write(text)
raw = open(PATH, "rb").read()
print("checkinCopy.ts bytes=%d sha256=%s" % (len(raw), hashlib.sha256(raw).hexdigest()[:16]))
os.environ["CNX_SHAPE_FIXED"] = "1"
