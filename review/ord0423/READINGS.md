# ORD-0423 readings - the bookings screen stops printing machine speech

lane rel (session a68b0631). Tip this candidate was cut from: `8a7665be2061a2f38aa2227f81c57003ca4caacb`; candidate commit: `d7d19c42be227248e085cf54e0f81bba50c749dd`.
Stack: my own build, my own backend, my own sqlite copy. Nothing shared was written.

## 1. The two judged lines, read as rendered text (textContent of the rendered nodes)

Source: `screen/arm_zh.json` and `screen/arm_en.json`, produced by `node ord0423_arm_reader_r1.cjs http://127.0.0.1:4813 <locale> <out>`.

| arm | path | h3 heading | row span (label + instant) | row strong | page_errors |
| --- | --- | --- | --- | --- | --- |
| zh | /v8/bookings | `已保存的行程事实` | `Nexus River Cruise Pier · 10月10日 15:30` | `Nexus River Cruise Pier · 中途` | 0 |
| en | /v8/bookings | `Saved trip facts` | `Nexus River Cruise Pier · 10 Oct, 15:30` | `Nexus River Cruise Pier · Mid-trip` | 0 |

The counter-proof that this is not the old shape: the published instrument's checklist, run against the same screen, reports for both arms:

| expected literal | zh arm | en arm |
| --- | --- | --- |
| `已保存的行程事实` | True | False |
| `Saved trip facts` | False | False |
| `Journey Memory` | False | False |
| `Nexus River Cruise Pier · 10月10日 15:30` | True | False |
| `Nexus River Cruise Pier · 10 Oct, 15:30` | False | False |
| `Nexus River Cruise Pier · 2026-10-10T15:30:00+08:00` | False | False |
| `时间待定` | False | False |
| `time pending` | False | False |

Instrument: the published blob `41a69ce5e9dc0c8c28c8c89d9105c6e6a7834c67`, used unmodified; its own output ships in this branch as `review/ord0423/untranslated_bookings_r2.json`. Scroll reach for the zh arm: `max=1681 deepest=1681 bottom_reached=True` (from `zh.scroll_reached[0]` of that file).

## 2. One limitation of that published instrument, stated rather than worked around

Its `en` arm never reaches `/v8/bookings`: it enters the demo stage by clicking the literal `使用封装的演示行程`, which is Chinese-only, so the English arm stays on the wizard (`en.ascii_prose_count=38`, first leaves: `Try CityNexus with your ow`, `Create a trip`). The English row above therefore comes from `ord0423_arm_reader_r1.cjs`, which clicks the same button by its locale-independent testid (`frontend/src/features/setup/JourneyTrialSetup.tsx:1534`) and reads the same channel (textContent). Fixing the instrument belongs to its owner, not to this order.

## 3. The empty-instant counter-arm: not reachable through the product's own doors

Attempted, with the server's own answers, in order:

1. UI door: `inbox-tab-manual` -> `manual-title` -> `manual-submit` with departure and arrival left empty. It creates a draft, and the server itself says what is missing: `status=NEEDS_REVIEW`, `unresolved_fields=['origin', 'destination', 'scheduled_departure_at', 'scheduled_arrival_at', 'confirmation_ref']`.
2. The panel's confirm button is gated on exactly that list (`frontend/src/features/inbox/JourneyInboxWorkbench.tsx:911`: `disabled={busy || Boolean(draft.unresolved_fields.length) || draft.status === "CONFIRMED"}`), so the click never lands - playwright reported the node as `disabled` and timed out.
3. The server's own door, called directly: `POST .../inbox/<draft>/confirm` -> HTTP 409 `This booking still needs a few details before it can be saved: departure place, arrival place, departure time, arrival time, booking reference` (trace 9d27d4d9-6166, receipt CNX-T386MT2M).
4. The projection cannot answer an empty instant either: this stack's `transport_reservations` table has 0 rows and `commitments` has 1 (read with sqlite3 mode=ro over my own copy), and the single memory item carries `at='2026-10-10T15:30:00+08:00'`.

So `inbox.timePending` was **NOT_MEASURED_ON_SCREEN**: reaching it would mean writing a reservation row by hand, which is fabricating the very data the arm is supposed to be read from. What was measured instead is the shipped code's own behaviour, by running the module the branch carries (`node ord0423_formatwhen_run_r1.cjs`, esbuild-transpiled, no stub):

| case | output |
| --- | --- |
| instant zh | `10月10日 15:30` |
| instant en | `10 Oct, 15:30` |
| null zh | `时间待定` |
| null en | `time pending` |
| empty string zh | `时间待定` |
| undefined zh | `时间待定` |
| blank spaces zh | `时间待定` |
| unparseable zh | `next Tuesday evening` |

An instant we cannot read is returned as-is rather than as "时间待定": the server did say something about time, so calling it pending would put a false statement on the screen.

## 4. Backend: server-authored prose in `backend/app/integrations/inbox/semantic_intake.py`

Report only - **this order changes 0 backend bytes**. Full inventory with each source line quoted is in `backend_prose_inventory.txt` beside this file.

---- D:/moodle/_qoder_rel_ord0423_wt/backend/app/integrations/inbox/semantic_intake.py:489
         source_line=return {"journey_id": journey.id, "title": "Journey Memory", "items": items}
         what=the panel heading, authored in English here
         rendered_at=JourneyInboxWorkbench.tsx:755 (before)
         measured=BEFORE: `Journey Memory` was on the zh screen (published reading, grep count=1 in blob bf772e96e171e7cc33b3b3b27b9b7ca7d6360950). AFTER: instrument expect says `Journey Memory` NOT_ON_SCREEN and the h3 reads 已保存的行程事实 / Saved trip facts.
---- D:/moodle/_qoder_rel_ord0423_wt/backend/app/integrations/inbox/semantic_intake.py:448
         source_line="MID_TRIP": "Journey commitment",
         what=RESERVATION title, one of four authored literals
         rendered_at=JourneyInboxWorkbench.tsx:767
         measured=NOT-DEMONSTRATED-ON-SCREEN: this stack's `transport_reservations` table holds 0 rows, so no RESERVATION item reaches the panel; the single memory item is kind=COMMITMENT.
---- D:/moodle/_qoder_rel_ord0423_wt/backend/app/integrations/inbox/semantic_intake.py:449
         source_line=}.get(role, "Travel fact"),
         what=RESERVATION title fallback literal
         rendered_at=JourneyInboxWorkbench.tsx:767
         measured=NOT-DEMONSTRATED-ON-SCREEN, same reason as :448.
---- D:/moodle/_qoder_rel_ord0423_wt/backend/app/integrations/inbox/semantic_intake.py:159
         source_line="label": "Arrival anchor" if role == "ARRIVAL" else "Departure anchor",
         what=STRUCTURAL_ANCHOR label, authored in English
         rendered_at=JourneyInboxWorkbench.tsx:768 (the `item.label` half)
         measured=NOT-DEMONSTRATED-ON-SCREEN here (no anchor item in this journey's memory). NOTE: this order localises the *instant* on that line only - if an anchor row ever reaches the screen, its label still arrives as server English.
---- D:/moodle/_qoder_rel_ord0423_wt/backend/app/integrations/inbox/semantic_intake.py:484
         source_line="reasoning_summary": "Protected by a confirmed Journey commitment.",
         what=a full sentence authored in English
         rendered_at=held back: JourneyInboxWorkbench.tsx:772
         measured=NOT_ON_SCREEN: the row prints `reasoning_summary=held 原文不在这一屏` instead; my arms read the protected/confidence line, not this sentence.
---- D:/moodle/_qoder_rel_ord0423_wt/backend/app/integrations/inbox/semantic_intake.py:329
         source_line=or ("Traveller entered this booking for this Journey." if user_entered else ""),
         what=candidate_journey_match.reason, authored in English
         rendered_at=no reader in frontend/src
         measured=NOT_ON_SCREEN: `grep -rn candidate_journey_match frontend/src` returns 0 files.
---- D:/moodle/_qoder_rel_ord0423_wt/backend/app/integrations/inbox/semantic_intake.py:456
         source_line="reasoning_summary": extracted.get("reasoning_summary") or "",
         what=upstream model sentence, passed through, not authored here
         rendered_at=held back: JourneyInboxWorkbench.tsx:772
         measured=PASSTHROUGH: same held-back slot as :484.
---- D:/moodle/_qoder_rel_ord0423_wt/backend/app/integrations/inbox/semantic_intake.py:126
         source_line="label": item.title or (place.name if place else semantic_key),
         what=label taken from the place/item name, real content
         rendered_at=JourneyInboxWorkbench.tsx:768
         measured=PASSTHROUGH, not invented: on my stack this is where `Nexus River Cruise Pier` comes from.
filter_condition=every string literal of >=3 words, plus 2-word literals whose first word is
  capitalised, walked with `ast` over the whole file; result: 10 literals, of which 3 are
  docstrings (:1, :55, :275) and 7 are values - the 7 are the sites above plus :159's second
  literal. Inventory artifact: D:/moodle/_qoder_rel_ord0423_wk/semintake_prose_inventory.txt

## 5. Gates, each with the command that produced it

- `npx tsc -p tsconfig.check.json --noEmit` -> exit 0, output 0 bytes (`_qoder_rel_ord0423_wk/tsc_check.txt`).
- `npx tsc -p tsconfig.typecheck.json --noEmit` -> exit 0, output 0 bytes (`_qoder_rel_ord0423_wk/tsc_typecheck.txt`).
- non-vacuity: `--listFiles` includes both changed files once each (`formatWhen.ts` and `JourneyInboxWorkbench.tsx`; lines containing `/src/` = 84 for tsconfig.check.json and 134 for tsconfig.typecheck.json).
- bundle arm: `python cmdr_build_bundle_r1.py --sha d7d19c42... --tag rel0423` -> vite exit 0 in 15.5 s, asset `index-OjJFdcGW.js`, and it proves the export carries the tip's bytes for `JourneyInboxWorkbench.tsx` (blob c43cd672358b24e1ff566b05daf3a98b882a3174).
- the screen arms above ran against that same built asset through my own static+api proxy.

