#!/usr/bin/env python3
"""ORD-0391 step 2: put a field name in front of every number these rows show a traveller.

Every replacement is counted and asserted, and the sentence is never shortened - the order forbids
turning tier b into tier c by deleting the claim.  Two shapes are used, both already the convention in
this tree (JourneyInboxWorkbench.tsx:312 and failureAttribution.ts:133/140 were born that way):
`http_status=404` beside the prose.  Where the number is rendered through i18n (the studio row), the fix
belongs at the copy, and that is where it is made.
"""
import io
import os
import sys

TREE = r"D:/moodle/_qoder_rel_ord0391"
EDITS = [
    ("frontend/src/lib/failureAttribution.ts", [
        ("（HTTP ${", "（http_status=${", 7),
        ("(HTTP ${", "(http_status=${", 7),
        ("，Content-Type: ${", "，content_type=${", 2),
        (", Content-Type: ${", ", content_type=${", 2),
        ("服务器答了 ${", "服务器答了 http_status=${", 2),
        ("The origin answered ${", "The origin answered http_status=${", 2),
    ]),
    ("frontend/src/features/recovery/RecoveryRequiredPanel.tsx", [
        ('`HTTP ${refusal.http_status}`', '`http_status=${refusal.http_status}`', 1),
    ]),
    ("frontend/src/features/discovery/DestinationPreparationPanel.tsx", [
        ("已经跑了 ${Math.round(job.elapsed_ms / 1000)} 秒。",
         "已经跑了 ${Math.round(job.elapsed_ms / 1000)} 秒（elapsed_ms=${Math.round(job.elapsed_ms)}）。", 1),
        ("running ${Math.round(job.elapsed_ms / 1000)}s.",
         "running ${Math.round(job.elapsed_ms / 1000)}s (elapsed_ms=${Math.round(job.elapsed_ms)}).", 1),
    ]),
    ("frontend/src/i18n/LocaleContext.tsx", [
        ("拒绝了这次请求（HTTP {status}）", "拒绝了这次请求（http_status={status}）", 1),
        ("refused this request (HTTP {status})", "refused this request (http_status={status})", 1),
    ]),
]


def main():
    total = 0
    for rel, subs in EDITS:
        path = os.path.join(TREE, rel)
        s = io.open(path, encoding="utf-8").read()
        before = s
        for old, new, want in subs:
            got = s.count(old)
            assert got == want, (rel, old[:40], "expected %d found %d" % (want, got))
            s = s.replace(old, new)
            total += got
        assert s != before and old not in s
        io.open(path, "w", encoding="utf-8", newline="\n").write(s)
        print("%-58s %d replacements" % (rel, sum(w for _, _, w in subs)))
    print("total replacements", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
