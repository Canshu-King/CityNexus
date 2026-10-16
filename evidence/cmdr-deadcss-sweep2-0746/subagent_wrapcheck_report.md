# CityNexus mobile text-wrap claims — round 1 verification

Measured 2026-10-17 against the already-running dev server `http://127.0.0.1:8121` (vite, source
`D:/moodle/_cmdr_fe_rev_1016/tip/frontend/src`), backend `:8011`. No server was started or stopped.
**READ-ONLY on the repo** — no file under `tip/` was edited and no state-changing git command was run.
All scripts and outputs are under `D:/moodle/_cmdr_fe_rev_1016/` prefixed `_cmdr_wrapcheck_`.

Raw machine-readable results: `D:/moodle/_cmdr_fe_rev_1016/_cmdr_wrapcheck_r1.json`

## Headline

| # | Claim | Verdict |
|---|-------|---------|
| 1 | 「证据」 renders one character per line at 320 | **CONFIRMED** at 320, zh-CN, both themes. English sibling **not** affected |
| 2 | 「模拟承诺」 orphans 「承诺」 onto its own line at 360 | **CONFIRMED** at 360, zh-CN, both themes |
| 3 | 「中途」 is split across lines mid-word at 360 | **REFUTED at 360** — the word sits whole on one line. The same split is real at **320** |

Theme (light/dark) changed nothing at any cell. All three are zh-CN-only.

## Three corrections to the brief, before anything else

1. **The locale seed value `en-US` is rejected by the app.** `TripLocale` is `"en" | "zh-CN"`
   (`frontend/src/i18n/LocaleContext.tsx:4`) and the reader is
   `if (stored === "zh-CN" || stored === "en") return stored;` (`…LocaleContext.tsx:3152`) — anything
   else falls through to `navigator.language`. My first recon pass seeded `en-US` and *both arms
   rendered Chinese with identical DOM sizes*; I caught it only because I read
   `document.documentElement.lang` back. **Every cell in the accepted matrix re-seeded with `en` and
   verified `lang === "en"`.** If an earlier headless pass seeded `en-US`, its whole locale axis was
   silently zh-CN.
2. **`el.click()` inside `page.evaluate` works at every width**, including ≤680 — I used it
   exclusively and never once needed `page.click`. No cell was lost to a 0x0 nav button.
3. **「模拟承诺」 and 「中途」 are NOT on the default Trips view.** `WalletCommitments` mounts only
   under the Trips → 预订/Bookings tab (`[data-testid="trips-tab-bookings"]`, shell at
   `frontend/src/app/V8Experience.tsx:2401-2404`), and 「中途」 lives in the Journey Memory panel on
   that *same* tab (`frontend/src/features/inbox/JourneyInboxWorkbench.tsx:827-829`), not on the
   itinerary. A pass that clicks `nav-trips` and stops sees **zero** of both words and would report
   "not found" for claims 2 and 3. `.trip-stop-type` measured 0 instances on this journey.

## Method (and why it is trustworthy)

* `chromium.launch({ channel: "chrome", headless: true })`, Playwright required by absolute path from
  `D:/moodle/CityNexus/frontend/node_modules`. 16-cell matrix (4 widths × 2 themes × 2 locales), plus a
  12-cell glyph pass and a 36-cell all-screen sweep. `viewport-fit=cover` is honoured by the app's own
  meta (`frontend/index.html:8`).
* **Line boxes, not `boundingBox()`.** Every verdict rests on
  `range.selectNodeContents(el); range.getClientRects()` **and** a second pass that rects
  *each character individually* (`setStart(node,i)/setEnd(node,i+1)`) and groups them by rect `top`.
  The per-character pass is what names *which* glyph orphaned onto *which* line — `getClientRects()`
  alone cannot say that.
* **Rendered, not merely present.** After scrolling, each glyph is hit-tested with
  `document.elementFromPoint` at its own rect centre and required to resolve to the element or a
  descendant. `painted == glyphTotal` at every decisive cell (2/2, 5/5, 17/17, 23/23, 29/29).
* **Scroll proof.** `window.scrollTo` does nothing here, so I walked ancestors for computed
  `overflowY ∈ (auto, scroll)` with `scrollHeight > clientHeight`, then read `scrollTop` before/after.
  On this build the only real scroller for these sites is `document.scrollingElement` (`html`);
  recorded deltas reach **1353px** (Live drawer) and **223px** (booking badge). Both are in the JSON.
* **Citations are byte-exact `split('\n')` line numbers, re-checked against disk after measuring.**
  Caveat for anyone acting on this: another lane is editing this working tree live — `cn-pulse.css`
  shrank from 655 to 643 lines *during* this pass, which moved the precedent comment cited under claim 2
  from `:650-653` to `:638-641`. Every `file:line` in this report was re-grepped as the last step; if you
  pull the tree later, re-grep the string rather than trusting the number.
* **Instrument honesty — one of my own passes was wrong and I re-ran it.** The all-screen sweep
  hit-tested glyphs *before* scrolling, so it printed a fake `0/N painted` on every row, including
  perfectly good ones. I did not report from it; `_cmdr_wrapcheck_glyph.cjs` scrolls first and then
  tests, which is the pass the verdicts rest on.

* **`overflow-x:auto` exclusion checked per site and it does not save any of them.** Claims 2 and 3
  have `overflowAncestors == []`. Claim 1's only non-visible-overflow ancestor is
  `details.v9-evidence-drawer { overflow: hidden }` with `scrollWidth 284 ≤ clientWidth 286` — a corner
  clip, not a designed scroller. The earlier refutation shape is real but belongs to a *different*
  element: `button[data-testid="rank-sort-evidence"]` (硬可用证据段数) genuinely sits inside
  `div.plan-ranking-scroll { overflow-x: auto }` — `frontend/src/features/planning/planRanking.css:19`
  (byte-exact) — and I excluded it on that basis rather than counting it.

---

## Claim 1 — 「证据」 one character per line at 320 — CONFIRMED

**Where it lives.** 今天 → Live screen (reached by `today-hero-cta` → `navigate("live")`,
`frontend/src/app/V8Experience.tsx:3287`). It is the `<summary>` label of the evidence disclosure
drawer, *above the fold of the closed drawer*, so it is visible without opening anything. Note the
bottom bar reads `aria-current` on `nav-map`, because `map` and `live` deliberately share one active
state (`frontend/src/app/V8Experience.tsx:2248`).

**Element.** `span` — no class, no `data-testid` — first child of `summary.v9-evidence-summary`,
inside `details.v8-comparison.v9-evidence-drawer`. Source:
`<span>{t("live.evidence")}</span>` at `frontend/src/app/V8Experience.tsx:3990`; copy at
`frontend/src/i18n/LocaleContext.tsx:1981` (`"live.evidence": "证据"`) and `:416` (`"EVIDENCE"`).

**Measurement (320 × light × zh-CN; dark identical to 0.01px).**

```
box / content box : 29.48 x 42   (no padding or border on the span)
Range.getClientRects() after selectNodeContents :
  rect 0  top 400.58  left 58.00  w 16.00  h 21
  rect 1  top 421.58  left 58.00  w 16.00  h 21
per-character lines :  line 1 = 「证」    line 2 = 「据」
glyphs painted / total : 2/2    in viewport : 2/2
scroll proof : html.scrollTop 0 -> 1353 (delta 1353)
computed     : display block, flex 0 1 auto, min-width auto, font-size 16px,
               white-space normal, overflow-wrap normal
```

Two line boxes, both exactly one 16px glyph wide, the two glyphs stacked vertically. That is the claim
verbatim.

**Why it happens (arithmetic, not guesswork).** `summary.v9-evidence-summary` is a flex row with
`padding: 20px` and `gap: 12px`. Measured flex container at 320 = **244px**, so content = 204px. The
row's max-content is `证据` 32 + gap 12 + sub-label 150 + gap 12 + the `::after` "+" marker ≈ **217** —
over-constrained by ~13px. With `flex-shrink: 1` and `min-width: auto`, a CJK flex item's floor is
*one glyph* (16px), so the label is shrunk **32.00 → 29.48**, i.e. 2.52px short of the 32px its two
16px glyphs need, and it drops to one character per line. Corroboration that the whole row squeezed
rather than the label being intrinsically narrow: at the same width the sibling `<small>` also breaks
to two lines (`供应商路线、时效、费用和可` / `行性`).

**Widths/locales where it does NOT happen.** 360, 390, 430 zh-CN: one line box, `w 32`, `h 21`,
`charLines ["证据"]` — the label keeps its full 32px. Every en cell: `EVIDENCE` is one line box of
`w 71.58 h 21` at all four widths; Latin with `overflow-wrap: normal` has no break opportunity inside
the word. **The English sibling is refuted.**

**Governing CSS (grepped from the class token, cited as measured).**
`frontend/src/styles.css:359` (byte-exact; the same line also carries the drawer's clip):

```css
.v9-evidence-drawer { padding: 0; overflow: hidden; }
.v9-evidence-summary { display: flex; align-items: center; justify-content: space-between;
                       gap: 12px; padding: 20px; color: var(--v8-ink); cursor: pointer; list-style: none; }
.v9-evidence-summary small { margin-left: auto; color: #7f8a99; font-size: 10px; }
```

Supporting: `frontend/src/styles.css:285` `@media (max-width:680px){ summary{ min-height:var(--cn-touch-min); line-height:var(--cn-touch-min);} }`,
`frontend/src/styles.css:288` `@media (max-width:680px){ .v9-evidence-summary{ line-height:normal; } }`,
and the page gutter that sets the 286px drawer width, `frontend/src/styles.css:185`
`.v8-content { padding: 27px 17px 34px; }`. There is **no** rule for the bare `> span`, which is why
it inherits the shrinkable `flex: 0 1 auto`.

**Fix location.** In the **word's own container**, not a width rule. `.v9-evidence-summary > span`
needs `flex: none` (or `white-space: nowrap` / `min-width: max-content`). A `@media (max-width:320px)`
band-aid would only move the threshold: the trigger is a ~13px over-constraint created by the 10px
sub-label, so any longer `live.evidenceSub` copy re-breaks it at 360.

---

## Claim 2 — 「模拟承诺」 orphans 「承诺」 at 360 — CONFIRMED

**Where it lives.** Trips → 预订/Bookings tab → the travel-wallet commitment card. Source:
`frontend/src/app/V8Experience.tsx:4433-4438`, badge
`<b data-testid="wallet-commitment-simulated">{" · "}{t("bookings.commitmentSimulated")}</b>` inside
`span.v8-selected-label`, inside `.v8-booking-card > div`. Copy at
`frontend/src/i18n/LocaleContext.tsx:2029` (`模拟承诺`) / `:470` (`simulated commitment`). The badge
only exists when `external_ref` starts with `mock-`; on this journey exactly 1 of 1 cards qualifies
(`data-simulated == ["true"]`).

**Measurement (360 × light × zh-CN; dark identical).**

```
badge  b[data-testid=wallet-commitment-simulated]  text "· 模拟承诺"
       box 138.69 x 33   | Range.getClientRects():
         rect 0  top 405.44  left 213.80  w  7.89  h 12     (the ·)
         rect 1  top 405.44  left 221.69  w 18.00  h 12     (模拟)
         rect 2  top 426.44  left 101.00  w 18.00  h 12     (承诺)  <- alone on its own line
       per-character lines :  line 1 = 「·模拟」   line 2 = 「承诺」
       glyphs painted 5/5, in viewport 5/5, computed overflow-wrap: anywhere

label  span.v8-selected-label  text "预订 · 受保护锚点 · 生效中 · 模拟承诺"
       box 138.69 x 41 (content box 124.69 x 33)
       per-character lines :  line 1 = 「预订·受保护锚点·生效中·模拟」   line 2 = 「承诺」
       glyphs painted 17/17
scroll proof : html.scrollTop 841 -> 1064 on the badge (delta 223); already settled for the label
overflowAncestors : []   (no scroll or clip container anywhere above it)
```

The word breaks between 拟 and 承, and 「承诺」 occupies line 2 **entirely by itself** — the line's full
text is `承诺`. Confirmed exactly as claimed.

**Scope beyond the claim.** This is **not** a 360-only defect; 360 is only where it happens to land
inside 模拟承诺. At 320 the same rule splits a different word instead —
`["预订·受保护锚点·生效", "中·模拟承诺"]` (生效中 broken, 模拟承诺 intact) — and only at 390/430 does
the label fit on one line (`["预订·受保护锚点·生效中·模拟承诺"]`, box 163.69×20). **en at 360 behaves
correctly**: `["·simulated", "commitment"]` breaks at the inter-word space, never inside a word.

**Governing CSS (as measured).** The break authority is on the *card's text column*, inherited down to
both elements (`overflow-wrap: anywhere` was read off both the badge and the label):
`frontend/src/styles.css:335`

```css
.v8-booking-card > div { min-width: 0; overflow-wrap: anywhere; }
```

with the badge's own type at `frontend/src/styles.css:179`
`.v8-selected-label { padding: var(--cn-s-4) 7px; … font-size: 9px; font-weight: 800; }` and the card
layout at `frontend/src/styles.css:337`. The comment block at `frontend/src/styles.css:331-334` shows
`anywhere` was added deliberately by ORD-0146 to stop a long `confirmation_ref` forcing a 508px min-content
row inside a 360px viewport.

**Fix location.** In the **word's own container** — specifically, narrow that one rule.
`overflow-wrap: anywhere` does two things here: it authorises an inter-character break inside a CJK
word, *and* it participates in min-content sizing so the column can be squeezed. Dropping it to
`overflow-wrap: break-word` keeps the ORD-0146 rescue (long unbroken tokens still escape) while
removing the licence to split 模拟承诺, and adding `word-break: keep-all` finishes it. **This is the
repo's own documented self-correction, verbatim**: `frontend/src/cn-pulse.css:638-641` (comment at `:633-637`) —
*"原来写的是 `overflow-wrap: anywhere`，它确实救下了 Asia/Shanghai，但代价是连中文也一起拆——实测导语在
「· 行 / 程时区」处断开（词内断行，读起来像漏字）。`anywhere` 还会参与 min-content 计算，把弹性列压得更窄。
换成：`break-word` … `keep-all` 让中日韩不在词内断。"* The same mistake was already found and fixed on
`.v8-lede`; it was never fixed on `.v8-booking-card > div`. A width-specific rule is the wrong shape
here — it would chase 320, 360 and every future label length separately.

---

## Claim 3 — 「中途」 split mid-word at 360 — REFUTED at 360, CONFIRMED at 320

**Where it lives.** Trips → 预订/Bookings tab, Journey Memory panel —
`strong[data-testid="v13-2-memory-name"]`, child of `li[data-testid="v13-2-memory-row"]` inside
`section.v13-2-memory-panel ol`. Source `frontend/src/features/inbox/JourneyInboxWorkbench.tsx:827-829`
(`{memoryRowName(item, t)} · {roleLabel(item.role, zh)}`); the word is
`MID_TRIP: { zh: "中途", en: "Mid-trip" }` at `frontend/src/i18n/travelerLabels.ts:34`. Rendered text:
`Nexus River Cruise Pier · 中途`.

**Refutation measurement (360 × light × zh-CN) — what I actually read:**

```
box 219.52 x 21        <- one line tall; a split word would need >= 42
Range.getClientRects():
  rect 0  top 411.44  left  74.00  w 174.34  h 21    ("Nexus River Cruise Pier")
  rect 1  top 411.44  left 248.34  w  13.17  h 21    (" · ")
  rect 2  top 411.44  left 261.52  w  32.00  h 21    ("中途"  <- both glyphs, one rect)
per-character lines :  ["NexusRiverCruisePier·中途"]   (one line, 23 characters)
glyphs painted 23/23, in viewport 23/23
scroll proof : html.scrollTop 1064 -> 592 (delta -472)
computed : white-space normal, overflow-wrap normal, word-break normal
```

All three rects share `top 411.44`, and the third is **32.00px = both 16px glyphs side by side**. 中 and
途 are on the same line box. Identical in dark. **The claim, as filed at 360, does not reproduce.**

**But the defect is real one width down.** At **320** (light and dark):

```
box 203.52 x 42
Range.getClientRects():
  rect 0  top 401.44  left  74.00  w 174.34  h 21
  rect 1  top 401.44  left 248.34  w  13.17  h 21
  rect 2  top 401.44  left 261.52  w  16.00  h 21    (中 only)
  rect 3  top 422.44  left  74.00  w  16.00  h 21    (途 alone on line 2)
per-character lines :  ["NexusRiverCruisePier·中", "途"]
glyphs painted 23/23, in viewport 23/23
```

`rect 2` collapses from 32px to 16px and a fourth rect appears on a new line: 「途」 is orphaned. So the
right filing is "320", not "360".

**English sibling.** At 360 en the row reads `["NexusRiverCruisePier·Mid-", "trip"]` — it *does* take
two lines, but the break is at the hyphen already inside the token `Mid-trip`, which is normal English
hyphenation, not a CJK intra-word split. At 320 en and at 390/430 en it is whole
(`["NexusRiverCruisePier·", "Mid-trip"]`, `["NexusRiverCruisePier·Mid-trip"]`).

**Governing CSS.** **There is none for this word** — that *is* the finding. Grepping the class tokens
`v13-2-memory-name` / `v13-2-memory-row` across `frontend/src/**/*.css` returns no match; the only
rules touching this panel are cosmetic and never mention wrapping, `frontend/src/design-tokens.css:334`
(radius + shadow), `:348` (background + border) and `:384`
`.v8-page .v13-2-memory-panel { padding: var(--cn-card-pad); }`. The measured element therefore wraps
on the UA default — `white-space: normal`, `overflow-wrap: normal`, `word-break: normal` (all read back
from the live element, not assumed) — and under default CJK line-breaking a break is legal between any
two ideographs whenever the line runs out of room. `overflowAncestors == []`.

**Fix location.** In the **word's own container**: `word-break: keep-all` on
`[data-testid="v13-2-memory-name"]` (or `white-space: nowrap` around the role label so the name and its
role can wrap *between* the two segments but never *inside* 中途). A width-specific rule is pointless
here — it would only relocate the break to the next word, and the panel has no wrap rule at all to make
narrower.

---

## Collateral findings (measured, not claimed — free with the matrix)

* **「路线证据」 splits the same way, at three widths.** The next heading down in the very same drawer
  (`span` child of `.v8-aside-heading`) reads `["路线证", "据"]` at 320, 360 **and** 390 zh-CN. Same
  family as claim 1, one screen-section away, and it is worse (three widths, not one). Fix it in the
  same pass.
* **The claim-2 rule breaks 生效中 at 320** (documented above), so a fix scoped to "the 模拟承诺 badge"
  would leave a visible regression at 320.
* **Claim 1 has nothing to do with `summary { min-height: 44px }`.** `styles.css:285` applies to the
  element and `styles.css:288` deliberately restores `line-height: normal` for this drawer, so the
  42px box is one label *wrapped to two lines*, not a touch-target rule. Don't "fix" ORD-0247 by
  accident.
* **Excluded as by-design:** `button[data-testid="rank-sort-evidence"]` (硬可用证据段数) on the hub
  screen does render `["硬可用证据段数", "↕"]` inside a horizontally scrolling wrapper —
  `div.plan-ranking-scroll` with `scrollWidth > clientWidth`, `frontend/src/features/planning/planRanking.css:19`.
  That is the earlier refutation shape; it is not filed as a defect.

## Artefacts

| File | What |
|------|------|
| `_cmdr_wrapcheck_r1.json` | verdicts + raw 16-cell matrix + glyph pass + 36-cell sweep + instrument notes |
| `_cmdr_wrapcheck_measure.cjs` / `_cmdr_wrapcheck_helpers.js` | the 16-cell matrix and the in-page line-box machinery |
| `_cmdr_wrapcheck_glyph.cjs` / `_cmdr_wrapcheck_glyph.json` | scroll-then-hit-test verification of every glyph |
| `_cmdr_wrapcheck_verify.cjs` / `_cmdr_wrapcheck_verify.json` | all-screen sweep (see instrument note on its pre-scroll hit-test flaw) |
| `_cmdr_wrapcheck_analyze.py` | turns line boxes into the verdict tables |
| `_cmdr_wrapcheck_recon.cjs`, `_cmdr_wrapcheck_recon2.cjs` | reachability recon; found the `en-US` seed bug and the missing Bookings tab |
| `_cmdr_wrapcheck_shots.cjs` / `_cmdr_wrapcheck_shots.json` | element crops for the decisive cells + their controls |

Screenshots live in `D:/moodle/_cmdr_fe_rev_1016/shots/` (ASCII names, `_cmdr_wrapcheck_` prefixed; the
directory is shared with other lanes so the prefix keeps them distinguishable):

| File | Shows |
|------|-------|
| `_cmdr_wrapcheck_c1_evidence_one_char_per_line_w320.png` | 证 / 据 stacked on two lines — matches the two 16px rects |
| `_cmdr_wrapcheck_c1_evidence_intact_control_w360.png` | 证据 on one line (control) |
| `_cmdr_wrapcheck_c2_commitment_orphan_w360.png` | `…生效中 · 模拟` then 「承诺」 alone on line 2 |
| `_cmdr_wrapcheck_c2_selected_label_control_w320.png` | the same rule splitting 生效中 instead |
| `_cmdr_wrapcheck_c3_memory_zhongtu_split_w320.png` | `Nexus River Cruise Pier · 中` then 「途」 starting line 2 |
| `_cmdr_wrapcheck_c3_memory_zhongtu_intact_control_w360.png` | `… · 中途` whole on one line — the refutation, in pixels |

Each crop was read back visually and agrees with the `Range.getClientRects()` numbers above; the
screenshots are corroboration, and the line boxes remain the evidence of record.

