# Revolution R104 — First Genuine Two-Place City Outing

Date: 2026-10-12
Branch: `codex/revolution-r63-planned-parallel-journey`
Scope: R104 only; no R58–R103 historical campaign was rerun.

## Reviewer fixes integrated

GPT's R103 review was merged as PR #13 and its narrow fixes were cherry-picked
onto this work branch before the R104 acceptance run:

- `ffc050ae69` — require both atomic-import candidates to belong to the signed
  member's exact `SHARED_PUBLIC_REFERENCE` receipt before any shortlist write.
- `d6fc51ac5e` — invalidate in-flight lookup/save responses when imported text,
  stop order, preview, or walking budget changes.
- `abd3fc790a` and `63d9b6b360` — sanitize untrusted OSM names/categories in
  public share text while retaining exactly two canonical source links.
- `05735a149e` — reject an ordinary discovery receipt attempting to authorize a
  friend's atomic Pocket Walk.

## Controlled signed A/B evidence

Run: `r104-two-place-20261012-g`
Viewport: `390x844`, Chromium, signed sender/recipient
Frontend: `:4280`
Backend: `:8280`
Database: `backend/_r104-two-place-20261012-g.db`
Python: `C:\Users\仓鼠王\AppData\Local\Programs\Python\Python313\python.exe`
AI: disabled
Result: **2 passed** (authoritative real-seed plus the R104 flow)

The flow used one named city search (`Shanghai`), one explicit public map pin,
one deliberate `ART_HISTORY` discovery, and a loopback `TEST_PROVIDER` fixture
returning three source-linked OSM candidates. The sender selected two public
identities and shared public-only text without first saving a Pocket Walk. The
recipient previewed locally with no provider call, gave separate consent, made
one exact-object lookup, and used one atomic action to save its own two private
shortlist items and Pocket Walk. Reload restored the card and ordered stops.
Destination-only directions and public-to-public walking were each released
under their own map consent.

The same run also verified the R104 review boundaries:

- A candidate name containing an embedded URL and a control character was
  rendered as safe text; the URL and control character were absent from the
  share preview.
- A delayed exact-lookup response was released only after the recipient edited
  the pasted text; the old response produced no result panel and no provider
  request was added.
- A tampered credential marker in pasted text was rejected locally without a
  provider request.
- The exact lookup request body contained only `node/103001` and `node/103002`.
  It contained no Journey ID, member ID, receipt ID, bearer token, GPS, or
  private text.

| Explore-only record | Sender | Recipient |
| --- | ---: | ---: |
| `places` | 0 | 0 |
| `plan_versions` | 0 | 0 |
| `agent_runs` | 0 | 0 |
| `guardian_runs` | 0 | 0 |
| `bookings` | 0 | 0 |
| physical arrival / route commitments | 0 | 0 |

Controlled provider calls were exactly one city search, one discovery request,
and one recipient exact-object lookup. The fixture's `TEST_PROVIDER` grade and
synthetic node IDs are not real-world evidence.

## Focused checks

- `py -3.13 -m pytest -q backend/tests/test_r102_shared_city_outing.py backend/tests/test_r100_pocket_walk.py backend/tests/test_r101_shared_walk.py` — **29 passed**.
- `npm exec playwright test e2e/r103-real-two-place-shareable-city-discovery.spec.ts --reporter=line` in the fresh authoritative environment — **2 passed**.
- `npm run typecheck:all` — passed.
- `npm run build` — passed; Vite emitted only its existing large-chunk advisory.
- `py -3.13 -m compileall -q backend/app backend/tests` — passed.
- `git diff --check` — passed before the final report was added.

## Real-provider outcome

`LIVE_BLOCKED`: the optional one-shot public Overpass operation was not made.
This relay had no operator-approved HTTPS provider, no real city/center chosen
by the human in this run, and no separate live-query authorization. Network
recovery alone is not a real-city consent or source receipt. I did not alter
provider settings to force a green result, invent OSM identities, or classify a
loopback HTTP fixture as `LIVE_PROVIDER`.

The next user-facing capability is already wired: an operator can configure an
approved HTTPS city-search/Overpass endpoint, a traveler can name a real city
and pin a public center, and one explicit consent can record the single live
source receipt. If that one attempt returns one usable place, the product must
say `PARTIAL`; it must never manufacture a two-place outing.
