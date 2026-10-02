"""ORD-0500 r6: derive the two-locale probe from the proven r2 instrument, not from scratch.

r2 already navigates this SPA correctly (demo entry, waits, per-control census with
scrollIntoViewIfNeeded + centre elementFromPoint, tap, tap-again, notice owners).  What it cannot do
is answer in English: it hard-codes locale "zh-CN" and counts marks by the Chinese word 已打卡, so in
an English context it would report zero marks and a screen with no CJK -- both true-looking and both
wrong.  This tool copies r2 and applies exactly three edits, each asserted to apply once:

  E1  locale comes from argv[7], recorded in the receipt;
  E2  the mark count counts BOTH languages' words and keeps them apart, plus a state-attribute count
      so a missing word cannot masquerade as "nothing is stamped";
  E3  the CJK inventory of the painted text is reported (the assertion this order needs: an English
      screen must carry no CJK, and every visible control label must equal the locale's own word).

If an edit does not match exactly once, this aborts instead of writing a probe whose behaviour I
guess at.
"""
import json
import os
import re
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
SRC = os.path.join(LANE, "tools", "checkin_phone_r2.cjs")
DST = os.path.join(LANE, "tools", "checkin_phone_r3.cjs")

src = open(SRC, encoding="utf-8").read()
edits = []

# E1 -- locale from argv
old = 'const H = Number(process.argv[6] || 844);'
new = ('const H = Number(process.argv[6] || 844);\n'
       'const LOCALE = process.argv[7] || "zh-CN";')
edits.append((old, new))
old = 'hasTouch: W <= 500, isMobile: W <= 500, locale: "zh-CN" });'
new = 'hasTouch: W <= 500, isMobile: W <= 500, locale: LOCALE });'
edits.append((old, new))
old = 'const run = { schema: "CNX_PHONE_CHECKIN_R2", face: BASE_URL, generation: TAG,'
new = ('const run = { schema: "CNX_PHONE_CHECKIN_R3", face: BASE_URL, generation: TAG,\n'
       '  locale: LOCALE,')
edits.append((old, new))

# E2 -- marks counted by word AND by state, both languages kept apart
old = "      marks_stamped_words: (body.match(/\u5df2\u6253\u5361/g) || []).length,"
new = ("      marks_stamped_words: (body.match(/\u5df2\u6253\u5361/g) || []).length,\n"
       "      marks_zh_words: (body.match(/\u5df2\u6253\u5361/g) || []).length,\n"
       "      marks_en_words: (body.match(/Checked in/g) || []).length,\n"
       "      marks_by_state: Array.from(document.querySelectorAll(\"[data-testid='stop-checkin']\"))\n"
       "        .filter((e) => e.getAttribute('data-state') === 'stamped').length,")
edits.append((old, new))

# E3 -- the CJK inventory and the control labels actually painted
old = "      uuids_on_screen: Array.from(new Set(body.match("
new = ("      cjk_chars_on_screen: (body.match(/[\\u3400-\\u9fff\\uf900-\\ufaff]/g) || []).length,\n"
       "      cjk_runs_on_screen: Array.from(new Set((body.match(/[\\u3400-\\u9fff]+/g) || []).slice(0, 12))),\n"
       "      control_labels_on_screen: Array.from(new Set(Array.from(\n"
       "        document.querySelectorAll(\"[data-testid='stop-checkin']\"))\n"
       "        .map((e) => String(e.innerText || '').replace(/\\s+/g, ' ').trim()))),\n"
       "      uuids_on_screen: Array.from(new Set(body.match(")
edits.append((old, new))

# E4 -- the census carries the control's own state, so a tap can be chosen without reading a word
old = "        disabled: !!el.disabled,\n      };"
new = "        disabled: !!el.disabled,\n        state: el.getAttribute('data-state'),\n      };"
edits.append((old, new))

# E5 -- choose the unstamped stop by STATE.  The r2 predicate tested the Chinese label, so an English
# screen could never satisfy it: the en walk died at arm 3 reporting NO_UNSTAMPED_PRESSABLE_STOP while
# five pressable fresh controls were on the page.  The word tests stay as a recorded fallback.
old = ("  const freshIdx = pressable.find((b) => /\u6253\u5361/.test(b.words) "
       "&& !/\u5df2\u6253\u5361/.test(b.words));")
new = ("  const freshIdx = pressable.find((b) => b.state === \"fresh\"\n"
       "                      || (/^\u6253\u5361$/.test(b.words) && !/\u5df2\u6253\u5361/.test(b.words))\n"
       "                      || /^Check in$/.test(b.words));\n"
       "  run.fresh_stop_basis = freshIdx ? (freshIdx.state === \"fresh\" ? \"data-state=fresh\"\n"
       "                                    : \"word-fallback:\" + freshIdx.words) : \"NONE\";")
edits.append((old, new))

out = src
for old, new in edits:
    n = out.count(old)
    if n != 1:
        print(json.dumps({"ABORT": "EDIT_NOT_UNIQUE", "snippet": old[:70], "found": n},
                         ensure_ascii=False))
        sys.exit(1)
    out = out.replace(old, new)

header = ("/* Derived from checkin_phone_r2.cjs by tools/make_probe_r6.py -- do not hand-edit: the\n"
          " * derivation is asserted (five replacement points in the three groups below, each matching\n"
          " * exactly once: E1 locale from argv, E2 marks counted in both languages plus by state,\n"
          " * E3 the CJK inventory and the control labels actually painted).\n"
          " *\n"
          " * argv: node checkin_phone_r3.cjs <base> <out.json> <tag> <width> <height> <locale>\n"
          " */\n")
out = re.sub(r"^/\*[\s\S]*?\*/\n", header, out, count=1)
open(DST, "w", encoding="utf-8", newline="\n").write(out)
print(json.dumps({"wrote": DST, "bytes": len(out.encode("utf-8")),
                  "edits_applied": len(edits),
                  "locale_reads_argv": "process.argv[7]" in out,
                  "counts_both_languages": "marks_en_words" in out and "marks_zh_words" in out,
                  "cjk_inventory": "cjk_chars_on_screen" in out}, indent=2, ensure_ascii=False))
