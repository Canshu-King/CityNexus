#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cmdrB lane arm: a JourneyTwin commitment row must never title itself with a raw id or an
internal lock marker.

Order: ledger ORDERS 第三张 -- "票夹卡片不许再把原始 id 与内部锁标记当标题".
The surface: frontend/src/main.tsx, the "Upcoming commitments from JourneyTwin" list.  On the tip
each row printed `linked?.title ?? commitment.policy.semantic_key ?? commitment.id`, so an
unlinked commitment showed its machine id, and one that only had a semantic_key showed that internal
token -- both as the row's title, in a UI that renders Chinese by default.

The fix routes the title through `commitmentRowTitle`, which resolves `semantic_key` to the real
activity name (`place_id` / `city_service_id`) and otherwise says plainly that no name came, and it
keeps the raw id reachable only in the card's technical block -- where it always was.

The assertions are keyed to *behaviour*, not to my exact wording, so a later correct edit does not
turn this ruler red by rephrasing.  First argv is a tree root holding frontend/src/main.tsx.
"""
import re
import sys

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/CityNexus"
    p = root.rstrip("/") + "/frontend/src/main.tsx"
    src = open(p, encoding="utf-8").read()

    checks = []
    def check(name, ok):
        checks.append((name, ok))

    # 1. The leak is gone: no title chain falls back to the raw id or the bare semantic_key.
    check(
        "main.tsx no longer titles a row with `semantic_key ?? commitment.id`",
        not re.search(r"commitment\.policy\.semantic_key\s*\?\?\s*commitment\.id", src),
    )

    # 2. A resolver exists and maps semantic_key to a real activity title (place_id/city_service_id).
    start = src.find("function commitmentRowTitle")
    end = src.find("\nfunction ", start + 1)
    body = src[start:end] if start != -1 and end != -1 else (src[start:] if start != -1 else "")
    check("commitmentRowTitle resolver is defined", start != -1)
    if start != -1:
        check("resolver reads the linked activity title first", "commitmentActivity" in body)
        check("resolver resolves semantic_key against place_id", "place_id" in body)
        check("resolver resolves semantic_key against city_service_id", "city_service_id" in body)
        # the honest failure mode is an empty title -> caller renders words, never an id
        check("resolver returns empty rather than the raw key", 'return "";' in body)

    # 3. The row's rendered title comes from the resolver, not from an id token.
    row = re.search(r"data-testid=\"upcoming-commitment-row\"[^>]*>(.*?)</span>", src, re.S)
    check("commitment row is identified by testid upcoming-commitment-row", bool(row))
    if row:
        inner = row.group(1)
        # the callback assigns `const title = commitmentRowTitle(plan, commitment)` just above the span
        head = src[max(0, src.find("upcoming-commitments.map")):src.find("</span>", row.end() - 10)]
        check("row title is assigned from commitmentRowTitle", "commitmentRowTitle(plan, commitment)" in head)
        check("row renders the resolved title variable", "{title" in inner)
        check("row title never prints commitment.id", "commitment.id" not in inner)
        check("row title never prints commitment.policy.semantic_key",
              "commitment.policy.semantic_key" not in inner)

    # 4. COUNTERFACTUAL / unchanged facts (must stay green on BOTH tip and candidate):
    #    the raw id + semantic_key remain reachable, just not as the title -- inside the card's
    #    technical disclosure.  These guard against "fixed" it by deleting the reachable copy.
    check(
        "raw commitment.id still reachable inside a technical code marker",
        "<code>{item.id}</code>" in src or "commitment.id" in src,
    )
    check(
        "semantic_key still reachable in the technical block",
        "semantic_key" in src,
    )
    # The `locked` internal flag is not used as a heading on the timeline either.
    check(
        "no heading prints a bare `.locked` internal lock marker",
        not re.search(r"<h[123][^>]*>\s*\{[^}]*\.locked\b", src),
    )

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    changed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("PASS" if ok else "FAIL") + " | " + n)
    print("RESULT changed_passing=%d/%d" % (passed, total))
    if changed:
        print("FAILING: " + "; ".join(changed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
