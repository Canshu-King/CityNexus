# CMDR SWAP RUNBOOK (r1, 2026-09-25 16:5x+08) — how to change the phone's frontend generation without breaking it

Who this is for: the commander (me) or the next shift, executing the NEXT generation swap
(e.g. after ORD-0302 lands). Everything here is a rule already paid for with an incident; the
bracketed tags name the ruling so nobody re-litigates it mid-swap.

Working dir for all commands: `D:\moodle\_qoder_cmdr_ref_20260921\live_checks`
Interpreter: the system `python` (3.10) is enough for the rulers; the frontend build uses the
repo's own `npm`/`vite` (see step 2 warning).

## 0. Preconditions — do not start without all four

| # | condition | how to prove it |
|---|---|---|
| P1 | the candidate is LANDED (authoritative tip == the candidate's tip) | `python land_authoritative_ref.py <want40> <expect_base40>` prints its three read-back routes; the tip is only moved by the commander, ff-only (`AUTHORITATIVE_BRANCH_SINGLE_WRITER_V1`) |
| P2 | the two rulers were green **on the bytes being deployed**, not on a neighbour's copy (`Q46=③`) | `python receipt_cell_derivation_check_r2.py --receipt <that receipt>` == `Q38_GATE_GREEN`, and `python claim_coordinate_check_r4b.py --text <the prose>` == `Q43_GATE_GREEN` with `claims checked > 0` (`NO_CLAIM_FOUND` is not a pass) |
| P3 | no hardlink/junction snapshot is anywhere in the bundle (`HARDLINK_SNAPSHOT_PROHIBITION_V1`) | the pre-swap scan artifact: see step 3, `ruler_hardlink_scan_*` |
| P4 | `:8000` data plane state is recorded honestly | if nothing listens there, the swap proves the **shell** only; every product sentence must then be labelled `NOT-DEPLOYED-OBSERVED`, never "the phone shows X" |

## 1. Read the tip one second before you build

```
git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1
```
The 40 hex you build must be the 40 hex you deploy. A 16-hex prefix is not a coordinate.

## 2. Build the bundle from a CLEAN tree, into a private out-dir

`vite build` reads the **working tree**. If any lane has `frontend/src` dirty, building there
produces a bundle nobody verified. Either build from a `git archive <sha>` export, or wait.

```
git -c core.autocrlf=false archive <tip40> frontend | tar -x -C <private-export-dir>
```
(git apply/checkout under autocrlf writes CRLF and will silently change bytes — use archive.)

## 3. Pre-swap double gate (union-first), both artifacts get NEW file names

```
CNX_DEPLOY_BASE=<cmdr-live-base> CNX_DEPLOY_BASE_IS_CMDR_LIVE=1 \
CNX_DEPLOY_PROXY_BASE=http://127.0.0.1:4782 CNX_DEPLOY_TUNNEL_BASE=https://<tunnel-host> \
CNX_DEPLOY_AUTH_FILE=<path-only, never print it> \
python deploy_bundle.py --src <new-dist> --serve <served-dist-root> --preflight-check
```
- `DEPLOY_BUNDLE_RETENTION`: **union the old assets into the served root BEFORE switching
  `index.html`**, then switch. A live URL answering `200 + text/html` at a `.js` path is the
  failure this rule exists to prevent (stale clients, white page, strict MIME).
- Never pass `--print-auth`, never paste the auth value into a bus post, ledger, or receipt.
  Only the file path travels.
- Published evidence paths are frozen: a revision gets a new file name; never overwrite or delete
  a path that was already cited.

## 4. Switch, then prove identity from the phone's side (not from disk)

```
python phone_side_probe_r1.py --out _phone_chain_<HHMM>.json
```
The verdict must be `DEPLOYED_AND_BYTE_IDENTICAL_ON_PHONE_SIDE` with all five decision flags true
(status 200 / bytes equal to disk / no asset served as HTML / JS content type correct / every named
ref present). Note the probe's own `generation_under_test` field: it proves transport identity only.
Bind the generation in the deploy receipt, not in the probe.

## 5. Post-swap

1. Publish the deploy receipt to a NEW `evidence/...` path and cite its full 40-hex blob in the bus
   post (`EXTERNALLY_READABLE_EVIDENCE`, `GENERATION_TRANSFER_BY_CITED_BLOB_EQUALITY_V1`).
2. Carry rule: nothing from the previous generation's measurements transfers unless the specific
   subtree is byte-equal — and when only a region is equal, say `region-level`, never `blob-level`.
   Durations never transfer across generations (`Q25`).
3. Cleanup is a **real-phone gate**, keep current + previous, delete by named list + blob sha1 only.
   Never a name-shape sweep, never delete a cited path.
4. If the swap introduced a user-visible regression, the ruling style here is fix-forward
   (`Q49=①`): do not revert a deployed generation; land the narrow fix and swap again.

## 6. Known instrument traps in this chain (each one already cost a turn)

- A 200 on a shared port may be another lane's backend: prove ownership (listener's parent pid == the
  pid you spawned, plus its log, plus the resolved DB file) before claiming anything from it.
- `-X utf8` + naive netstat parsing can crash a whole batch — parse by column, tolerate.
- Pipes mask exit codes (`cmd | tail` reports tail's rc); use `${PIPESTATUS[0]}` or a file.
- Shell `date` prints UTC on this box (+08 local); stamp local time by computing UTC+8.
- Backticks and straight `"` inside generated strings get eaten by the shell/JS: write the text to a
  file (or a Python list of lines) instead of inlining it.
- `git rev-parse <rev>:<path>` echoes the argument when the file is absent — match `[0-9a-f]{40}`
  before concluding anything exists.

## 7. What is still NOT covered by this runbook (say so, don't improvise)

It does not cover restarting the backend / `:8000` (protected demo state; needs the user's word),
nor service-worker cache eviction on real phones (the offline chain is ORD-0267/0268 territory), nor
the walkthrough gate (a green swap receipt is transport identity, not "a traveller can finish a plan").
