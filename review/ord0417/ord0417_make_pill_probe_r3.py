"""ORD-0417 lane: build a throwaway probe copy of my geometry arm.

The gate says a control was lost at 414x896/en but not WHY: `lost` is the set difference of three
predicates (answers a hit-test at its own centre, centre above the 768 px line, inside the viewport).
This copy prints the two census entries for the lost control (idle and live, so the flipped predicate is
visible) and, straight off the DOM, the control's box, the element that answers the hit-test at its
centre, and its computed `position`.  It is a copy in my own disposable export -- the published spec's
bytes are untouched, so the arm's verdict stays the arm's verdict.

Two earlier versions failed on their own quoting and are worth recording: r2 matched the lost control by
its accessible text and printed `probe: []`, because `lost` holds the census IDENTITY KEY (`testid`, else
`name#n`) and not a textContent; and the first r3 died in Python because `\\"` inside a double-quoted
string ends the string.  JS strings here are single-quoted for that reason.

usage: python ord0417_make_pill_probe_r3.py <export frontend dir>
"""
import pathlib
import sys

FE = pathlib.Path(sys.argv[1])
SRC = FE / "e2e" / "qoder-ord0417-tap-names-the-stop.spec.ts"
DST = FE / "e2e" / "_tmp_ord0417_pill_probe.spec.ts"

ANCHOR = "      const lost = beforeReachable.filter((k) => !afterReachable.has(k));\n"
L = [
    "      {",
    "        const idleOne = idleControls.find((c) => c.key === lost[0]) ?? null;",
    "        const liveOne = liveControls.find((c) => c.key === lost[0]) ?? null;",
    "        const dom = await page.evaluate((needle: string) => {",
    "          const els = Array.from(document.querySelectorAll<HTMLElement>(",
    "            'button, a[href], [role=\"button\"]'));",
    "          const seen: Record<string, number> = {};",
    "          const out: unknown[] = [];",
    "          for (const el of els) {",
    "            const text = (el.textContent ?? '').replace(/\\s+/g, ' ').trim().slice(0, 40);",
    "            const tid = el.getAttribute('data-testid');",
    "            const bare = tid ?? text;",
    "            seen[bare] = (seen[bare] ?? 0) + 1;",
    "            const key = tid ?? (text + '#' + seen[bare]);",
    "            if (!text.includes(needle) && key !== needle) continue;",
    "            const r = el.getBoundingClientRect();",
    "            const cx = Math.round(r.x + r.width / 2);",
    "            const cy = Math.round(r.y + r.height / 2);",
    "            const top = document.elementFromPoint(cx, cy);",
    "            out.push({ key, box: [Math.round(r.x), Math.round(r.y), Math.round(r.width),",
    "              Math.round(r.height)], centre: [cx, cy], inner_h: window.innerHeight,",
    "              scroll_y: Math.round(window.scrollY), position: getComputedStyle(el).position,",
    "              z: getComputedStyle(el).zIndex,",
    "              top_el: top ? (top.tagName.toLowerCase() + '.' + String(top.className).slice(0, 60)) : 'none',",
    "              top_is_self: !!top && (top === el || el.contains(top) || top.contains(el)) });",
    "          }",
    "          return out;",
    "        }, String(lost[0] ?? 'Copilot'));",
    "        console.log('PILLPROBE ' + JSON.stringify({ arm: `${w}x${h}-${arm.locale}`,",
    "          lost: lost[0] ?? null, idle: idleOne, live: liveOne, dom }));",
    "      }",
]
PROBE = "".join(line + "\n" for line in L)

src = SRC.read_text(encoding="utf-8")
if src.count(ANCHOR) != 1:
    raise SystemExit(f"REFUSE: anchor found {src.count(ANCHOR)} times, expected exactly 1")
DST.write_text(src.replace(ANCHOR, ANCHOR + PROBE, 1), encoding="utf-8")
print(f"wrote {DST} ({DST.stat().st_size} bytes)")
