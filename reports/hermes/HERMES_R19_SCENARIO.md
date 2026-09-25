# Hermes R19 — Runtime mobility fallback reliability

R19 exercises the actual CityNexus runtime path in which the configured
Valhalla mobility provider fails, the deterministic mock fallback supplies the
route facts, and the resulting snapshot is marked degraded. The Valhalla URL is
the loopback blackhole `http://127.0.0.1:1`; no external provider egress occurs.

The real Hermes model may request a proposal in the first arm. The receipt must
show a degraded snapshot, synthetic fallback route provenance, complete
proposal contract, persisted proposal IDs, unchanged Journey authority and no
acceptance/commerce/commitment mutation. The read-only arm must not generate.

The provider failure is a `SYNTHETIC_HARNESS_FIXTURE`; mock fallback evidence is
not LIVE provider evidence. Runtime is `PLAN_ONLY`, `P7=false`.
