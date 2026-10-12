# R7.4 identity corroboration contract

Core invariant: one provider candidate is never identity proof.

Safe escalation: a unique Photon candidate with a stable OSM id may trigger an exact read of that same OSM object. The follow-up cannot substitute another entity.

Allowed current-name evidence should be explicit and receipt-visible. Minimum set: name, official_name, short_name, alt_name, full_name, localized name:*.

Insufficient alone: fuzzy score, substring, prefix, same country/admin level, geographic plausibility, web snippet, model output, or a different OSM entity.

Error semantics:
- successful exact lookup + exact allowed-name match -> RESOLVED;
- successful exact lookup + no match -> NO_MATCH;
- failed exact lookup -> RUNTIME_FAILURE/retryable;
- different entity id -> malformed evidence/fail closed.

No Gongshan-specific exception. Mission A OPEN. P7=false.
