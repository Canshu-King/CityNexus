# ORD-0380 naming decision: (b) keep the blocks, make the ruler read the pairing

中文结论：选 (b)。不改任何色值、不加 `_night` 变体名，CSS 产品字节为零改动；
配对由尺的两格 NIGHT_PAIRING / CONSTANT_CLAIM_USED 检查，「不翻转」必须是可查的声明。
理由见下文第 2 节。Plan (b) chosen; zero product CSS bytes changed.

## 1. What the measurement says (all figures re-derivable from PAIRING.json)

40 colour tokens are written in a root theme scope. Each lands in exactly one of
five states, and every one of the 40 is currently explained:

| state | count | why it is acceptable |
|---|---|---|
| PAIRED_IN_DARK | 17 | the token itself is re-written in `:root[data-theme=\"dark\"]` and the colour moves |
| PAIRED_INHERITED | 10 | never written in the dark block, yet moves, because a node above it in its var() chain is re-written |
| NEUTRAL_BY_NAME | 13 | does not move and its family name says it must not |
| UNACCOUNTED / DEAD_PAIR / DARK_ORPHAN | 0 | the three red states |

The two states that did not exist as checkable claims before this order are the
interesting ones:

- PAIRED_INHERITED is entirely `--v8-*` plus `--cn-nav-bg` -- 12 tokens whose
  *light* value is written in the `:root, .v8-product-shell` block (line 172),
  which the ruler's own block splitter skips (`cnx_token_tiers_r1.py:36`, a
  selector must be bare `:root` to count). A diff of the two theme blocks cannot
  see them at all, and PARITY/TIERS/CONSTANT_* still report 0 for them because
  they never reach those denominators.
- NEUTRAL_BY_NAME splits 1 `--cn-always-*` + 10 `--cn-tint-*` + 2 aliases that
  resolve into the always family through var(). Nothing checked that claim.

## 2. Why (b) and not (a)

(a) `_night` twin names does not remove the switch, it duplicates it. CSS has no
name lookup: `--cn-canvas_night` still only takes effect if some block writes
`--cn-canvas: var(--cn-canvas_night)` under `[data-theme=\"dark\"]`. So (a) buys a
second spelling of a fact the cascade already states once, and pays for it with
two places that can disagree, plus ~24 new colour literals written into the light
scope of a public repo -- which is exactly the surface the compliance line in the
source analysis report (§6) is about. Its original form works there because that
product resolves resources by *field name* at build time; that mechanism is not
available to a CSS custom property.

(b) keeps one source of truth and makes it checkable. Under (b) the proof I can
offer is stronger than "PARITY did not break": PARITY is not merely green, it is
untouched, because the change has no product bytes in it (see §4).

## 3. What the two new cells enforce

**NIGHT_PAIRING** -- every colour token in a root theme scope must be in one of
the three explained states. "Not flipping" is only admissible as a claim made by
the name, and a name earns that claim only if the claim propagates: an alias into
an invariant family is neutral because its leaf is (`--v8-accent` ->
`--cn-accent-solid` -> `--cn-always-accent-solid`), not because anybody said so.

**CONSTANT_CLAIM_USED** -- an `--cn-always-*` with no `var()` consumer is a claim
about nothing. Counted as real `var()` references across the CSS the app loads,
not as substring hits: this file discusses tokens in prose and a prose mention
must not be able to make a dead claim look consumed. `--cn-always-accent-solid`
has exactly 1 real reference today; it appears 4 times as a substring.

The invariant families are `--cn-always-*` and `--cn-tint-*`. The tint ladder
earns it because a tier is an ingredient and the theme switch happens one level
up at the consumer -- evidenced in this same file, where `--cn-hairline` picks
`--cn-tint-black-08` in light and `--cn-tint-white-10` in dark while neither tier
is ever re-themed. That is a ruling to disagree with, and if it is wrong the cell
goes red the moment a tier is written in the dark block.

## 4. Evidence discipline

- Old five cells (PARITY, TIERS, LADDER_USED, CONSTANT_DUP, CONSTANT_IN_DARK)
  emit byte-identical name+measure+detail before and after this change, run
  against the same baseline: the denominators did not shift, so nothing was
  relaxed and nothing was silently widened.
- 8 mutants, each asserting the *owning* cell went red and, where the point is
  reach rather than redundancy, that a named control stayed green:
  M5 deletes a dark pairing (NIGHT_PAIRING), M6 gives a flipping base an
  always_ name and leaves the dark token dangling (NIGHT_PAIRING, with
  CONSTANT_DUP + CONSTANT_IN_DARK as controls -- neither old CONSTANT cell sees
  it), M7 is `#b06000` vs `#b06000ff`, one colour two spellings (NIGHT_PAIRING,
  with CONSTANT_DUP + TIERS as controls, since the raw string compare cannot see
  that equality), M8 is an unconsumed always_ claim (CONSTANT_CLAIM_USED, with
  NIGHT_PAIRING as control). M1-M4 are the four that shipped, unchanged.
- The self-test got stricter on purpose: before this order a mutant passed if
  *any* cell went red, so M1 with no `--baseline` passed vacuously on M2's
  co-fire. It now needs its owner. Two defects were found this way in the ruler
  itself, and both are recorded here rather than smoothed over.

## 5. Not improved by this order

- The old five cells keep their narrow parser. 12 of 40 colour tokens are still
  outside their denominators; only NIGHT_PAIRING sees them. Fixing that means
  re-baselining PARITY, which is a separate order.
- LADDER_USED still counts substring hits, so a tier mentioned only in prose
  would read as used. CONSTANT_CLAIM_USED does not have that weakness; making the
  older cell match it changes a shipped denominator.
- Hard-coded colours in dark *rules* (`:root[data-theme=\"dark\"] .v8-* { color: #7bd88f }`)
  are a separate pairing surface and untouched here; PAIRING.json only covers
  tokens.
- Nothing at runtime is observed. `data-theme` is written by `frontend/src/theme.ts:68`,
  but no screenshot or computed-style reading was taken in this order.
