# The `NOT_REACHED` initialisation gets its assertion, and a single-variable mutant shows it is load-bearing

Lane `5a53846b`, self-declared: the field my CMDR 02:35(5) hand initialises had no arm reading it.
Measured on the head, the whole `backend/` tree mentions `NOT_REACHED` exactly once - the product's
own initialisation line at `backend/app/integrations/discovery/real_city.py:1542` - and zero times
under `backend/tests/`.

Reachability first, because I got it wrong once. A throwaway probe that POSTed malformed city codes
straight to `/api/v1/journeys` came back `VALIDATION_ERROR`, and I wrote that down as "the schema
refuses it at the door". That reading is retracted: the probe's own payload was missing fields the
real helper sends. The existing arm `backend/tests/test_qoder_city_failure_reasons.py:359`
(`test_our_own_malformed_label_is_not_blamed_on_the_provider`) already reaches the path through the
product with `_journey("CN-CN-TIANJIN")`, so no new arm was needed - only the missing assertion. This
branch adds one assertion and three comment lines; it adds no test, mocks nothing the product did not
already mock in that fixture, and touches no other arm.

## The run, single variable

- control: the module on this head = `7 passed, 2 warnings`, exit 0.
- mutant: delete the line `fallback_geocode = "NOT_REACHED"` and run only that arm ->
  `1 failed`, exit 1, reason
  `backend/app/integrations/discovery/real_city.py:1770: UnboundLocalError: cannot access local
  variable 'fallback_geocode' where it is not associated to a value`.
  That unbound name is precisely what the comment at the initialisation site warns about, and it
  would replace the named reason code with a 500 - the defect the new assertion now keeps out.
- restore: the product file came back byte-identical (digest compared before and after).

## Why it belongs to this lane

`NOT_REACHED` was introduced by this lane's CMDR 02:35(5) hand (the guard against an unbound name on
a path that raises before any leg is asked). The guard has been on the line ever since with nobody
watching it; this closes that, in the file this lane last edited.
