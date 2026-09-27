# ORD-0367 r2 -- the RENDERED arm the copy ruler cannot see (supersedes nothing, adds a cell)

Tree measured: authoritative export of `4ef864cfa49b805e3d41b7f079f5fb4184ccec3d` at `frontend/src` only, `80` `.ts`/`.tsx` files outside `frontend/src/i18n/LocaleContext.tsx` (the dictionary itself is excluded because every key appears there exactly once per language block).

A key is counted as rendered when the quoted form `"<key>"` appears in a non-dictionary source file. Dynamic construction was checked separately and exists only for the `nav.` namespace, so a zero here is not a scanner artifact.

| key | uses outside the dictionary | slot of each use | sites |
|---|---|---|---|
| `agent.sendError` | 2 | FALLBACK_SLOT(nullish) | `features/agent/AgentComposer.tsx:105`, `features/agent/CopilotDock.tsx:644` |
| `discovery.composeError` | 1 | direct | `features/discovery/RealCityDiscoveryPanel.tsx:149` |
| `inbox.confirmFailed` | 0 | none | none |
| `inbox.correctionsFailed` | 0 | none | none |
| `inbox.imageFailed` | 0 | none | none |
| `inbox.memoryLoadError` | 1 | direct | `features/inbox/JourneyInboxWorkbench.tsx:356` |
| `inbox.readError` | 0 | none | none |
| `inbox.smartApplyFailed` | 0 | none | none |
| `inbox.textFailed` | 0 | none | none |
| `live.unresolvedStepHint` | 1 | direct | `app/V8Experience.tsx:3455` |
| `shell.loadError` | 2 | FALLBACK_SLOT(refusalSentence) | `app/V8Experience.tsx:1114`, `app/V8Experience.tsx:985` |

## Counting consequence for this order

- distinct keys edited: 11 (the order touched both language blocks of some keys,
  which is why the copy ruler counted edited *values* rather than keys)
- keys with at least one use outside the dictionary: 5
- keys with **zero** uses outside the dictionary: 6
  - `inbox.confirmFailed` -- nothing in the shipped frontend ever asks for this sentence
  - `inbox.correctionsFailed` -- nothing in the shipped frontend ever asks for this sentence
  - `inbox.imageFailed` -- nothing in the shipped frontend ever asks for this sentence
  - `inbox.readError` -- nothing in the shipped frontend ever asks for this sentence
  - `inbox.smartApplyFailed` -- nothing in the shipped frontend ever asks for this sentence
  - `inbox.textFailed` -- nothing in the shipped frontend ever asks for this sentence

## What this does NOT say

- It does not say the landing was wrong. The register fix, the zero-growth property, and the
  tier ladder are all measured green in the acceptance note
  (`b83202eb7f9b165c1c8428615e86e00f37be122c`), and dictionary rows that nothing reads are
  harmless bytes, not a runtime defect.
- It does not say the user saw no change. `live.unresolvedStepHint`, `discovery.composeError`
  and `inbox.memoryLoadError` do render, and `shell.loadError` / `agent.sendError` render
  whenever the attribution helper yields no body -- those two sit in a fallback slot, so
  their appearance is conditional rather than absent.
- It does say that any future claim of the shape "this copy pass is user-visible" must
  name which keys have a use site, because six of them do not.

## Ruler consequence (dispatched as part of ORD-0370)

`tools/cnx_copy_tiers_r1.py` should grow a `RENDERED` cell: for every edited key, print the
count of non-dictionary use sites and its denominator, and list the keys it considers
unrendered. The cell must be reported and, for a *new* edit, gated: editing a sentence
nothing reads is churn, and the ruler currently cannot tell that from progress.
Raw per-key counts: `{"agent.sendError": 2, "discovery.composeError": 1, "inbox.confirmFailed": 0, "inbox.correctionsFailed": 0, "inbox.imageFailed": 0, "inbox.memoryLoadError": 1, "inbox.readError": 0, "inbox.smartApplyFailed": 0, "inbox.textFailed": 0, "live.unresolvedStepHint": 1, "shell.loadError": 2}`
