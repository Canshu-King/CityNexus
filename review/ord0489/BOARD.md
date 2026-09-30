# ORD-0489 · demo board, seeded through the product's own write doors

Base read at cut time: `refs/heads/mirror/integration-frontend-apple-pass1` @
`dcb90cccc68b81f2317b28db19051dedb9f06c80` (two routes agreed: `git ls-remote` and
`GET /repos/Canshu-King/CityNexus/git/ref/heads/mirror%2Fintegration-frontend-apple-pass1`).

## Re-run recipe

    python tools/ord0489_lane_stack_r1.py start --port 8790 --db <lane>/_seed_final.db
    python tools/ord0489_demo_seed_r1.py --base-url http://127.0.0.1:8790 --report <lane>/board_seed_final.json
    python tools/ord0489_lane_stack_r1.py prove --port 8790 --db <lane>/_seed_final.db
    python tools/ord0489_lane_stack_r1.py kill   --port 8790

Three independent runs on three fresh stores gave the same counts:
`evidence/ord0489/board_seed_final.json` here, plus the lane's earlier `..._r3.json` / `..._r4.json`
identical on places 8/4/0, activities 10/11, footprint 3.

## What the board holds (`board_seed_final.json`)

| door | reading |
| --- | --- |
| `GET /api/v1/journeys` | 2 rows, server order `天津 · 三日两晚`, `北京 · 四日三晚` |
| `GET /api/v1/recycle-bin/journeys` | 1 row, `福州 · 两日一夜（未规划）` |
| `GET /api/v1/places?city_code=` | CN-TIANJIN 8, CN-BEIJING 4, CN-FUZHOU 0 |
| `GET /api/v1/journeys/<tj>/checkins` | 3 rows (2 PLACE + 1 ACTIVITY) |
| `GET /api/v1/shared/journeys/<token>` | live 200, revoked 409 `SHARE_GRANT_REVOKED`, binned 409 `SHARE_GRANT_JOURNEY_IN_RECYCLE_BIN`, unknown 404 `SHARE_GRANT_UNKNOWN` |

Every place row came from `POST /real-city/discover` with `mode=live`, and the run aborts unless
`provenance == LIVE_PROVIDER`; nothing writes SQL and `demo/reset` is never called.

## Screens walked

- line generation (`dcb90ccc`, preview `:8791`): `walk_ord0489_r2.cjs` → trip picker 3 options → 4
  after `undelete` (200) → re-binned (204); trash panel 1 row; share states painted with their
  refusal codes; 16 routes swept for footprint/poster/足迹/长图 → 0 hits.
- candidate generation (`refs/heads/1ba48dbf-ord0476-footprint-screen-r2` @
  `15d65d7f289c628b810cf5ab4a097d858a128821`, NOT an ancestor of the line; preview `:8792`):
  `walk_ord0489_candidate_r3.cjs` → footprint panel 3 rows, poster sheet 10 stop blocks, download
  `citynexus-trip-poster.png`; `walk_ord0489_footprint_grow_r4.cjs` → door 3 → 4 and the on-screen
  tally reads 4; `measure_checkin_geometry_r5.cjs` → one of five 打卡 controls has its centre
  covered by `nav-map` at 390×844.

`static_serving_proof_final.json` carries the served-bytes == on-disk-bytes pair that separates the
two generations (`assets/index-BdXy-aFm.js` vs `assets/index-gebvkcUd.js`).
