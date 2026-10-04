# CMDR 02:04 rulings 1-3, ruler side only

Two shipped test files changed; 0 product bytes, 0 contract bytes.
- test_qoder_ord197_four_class_receipt.py: r3 and r4 now take the module's own
   before asserting concluded fields (outcome /
  provider_attempts / survey). The arms used to read the row straight after the two
  POSTs, so which side they landed on depended on when the worker concluded.
- test_qoder_city_failure_reasons.py: the two 5xx expectations move from
  PROVIDER_BAD_RESPONSE to PROVIDER_SERVER_ERROR, the name the product has used for 5xx
  since the  commit. The malformed-payload expectation
  (KeyError -> PROVIDER_BAD_RESPONSE) is unchanged, so the two words stay distinguishable.

Counter-checks in cmdr0204_mutants_r2.txt (same tree, snapshot-restored, all four as
predicted): R1 fix + a 0.4 s hold injected at the worker conclusion = 2 passed x3;
R2 same hold with the fix removed = 2 failed x3; R3 worker writes OUTCOME_PREPARED
instead = r4 fails x3; R4 product maps 5xx back to PROVIDER_BAD_RESPONSE = the city arm
fails x3 (raw tail in r4_mutant_tail.txt). Instruments: cmdr0204_mutants_r1.py.
