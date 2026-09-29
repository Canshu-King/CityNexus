# R77 real selectable checkpoint

This receipt closes the real-trip selectable milestone on an unseeded disposable
Suzhou journey. It is not a mock or an explicit-place-only diagnostic.

- Starting commit: `4ee14229f80691cf8e5ea913375c0caf83ac02ee`
- Executed source / final code commit: `8c05fb4373efc866fbcc30e49e6177be4e07721a`
- Final experimental / receipt commit: `fef8ff167cf62e0c74c1bb8bde01ce66c3d0e4ef`
- Branch: `codex/revolution-realtrip-recovery`
- Worktree: `D:\moodle\CityNexus-Revolution-RealTrip-Recovery`
- Destination: `苏州市` / `CN-SUZHOU`
- Journey: `9b11e4cd-c1b5-43e6-aedf-6402a0cfddd2`

The product discovered and persisted two live OSM entities: 网师园
(`overpass:way/44679452`) and 拙政园 (`overpass:way/468359738`). Their opening
hours and paid costs were provider-backed (`KNOWN`, 3000 and 9000 CNY). The
real AUTO planner captured Valhalla mobility, emitted a candidate, and the
candidate's actual used edge was:

```text
real-place-8bc850f117297987997c87cf
  -> real-place-ba7377353c422c39dfd752b7
  42 minutes, LIVE_PROVIDER_CAPTURE
```

`POST /select` returned HTTP 200. Readback showed `PlanVersion.status=SELECTED`,
`Journey.active_plan_version_id` pointing to that plan, `selectable=true`,
`is_current=true`, and `stale=false`.

The bounded repair was to exclude cost-UNKNOWN rows from strict AUTO candidate
templates. They remain discoverable and available to the provisional lane; no
UNKNOWN value was converted to free. Focused gates: **33 passed, 1 existing
warning**.

DeepSeek and Hermes were checked through the supported runtime configuration and
were both `NOT_CONFIGURED`; no live agent execution is claimed. P7 remains false
and no authority/mainline tree was modified.

Full machine evidence is in
[`r77_suzhou_real_selectable_receipt.json`](./r77_suzhou_real_selectable_receipt.json).
