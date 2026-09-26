# Raw per-run pytest output, published as retrievable git blobs

The repo root `.gitignore` line 39 is `*.log`, so the originals could never be fetched from the
repository. They are re-published under `.log.txt` names so each one is a real blob. The right-hand
column is the value `git cat-file -e` resolves against commit `2012dc99e6bd277e0a191ffca312c3a187f843db`
and every ref that contains it; the middle column is the plain content sha1 I previously (wrongly)
quoted as a coordinate - a genuine hash of these bytes, but not a git object and therefore not
resolvable. Both are printed so the substitution is auditable rather than silent.

| run log | content sha1 (NOT a git object) | published path | git blob (resolvable) |
|---|---|---|---|
| N2R2-A.log | d78421a5202853a1d0eae4da3c73099c362d40a9 | `review/ord0355-r2-readings/raw/N2R2-A.log.txt` | `b7c3bbac09e52f30fa3032fe6bab5dc94f58972d` |
| N2R2-B.log | c7afb57dbcf6bc5e5ab22b53b1ded95db78411dd | `review/ord0355-r2-readings/raw/N2R2-B.log.txt` | `0b129e2db9cebc0632464bb2e8f848f196e47094` |
| N2R2-C.log | 5404b108d4f75c7a36c7be2e7318a4d575ba0a5e | `review/ord0355-r2-readings/raw/N2R2-C.log.txt` | `1ef35df0f46a1a751dcf4abe49a32c2a78e6ffeb` |
| N2R2-D.log | 80fc7386734c43067f61e4755832b49ef156aa6c | `review/ord0355-r2-readings/raw/N2R2-D.log.txt` | `8c1311063b8f16dc096fbc5ce84bd9daaa690273` |
| N2R2-E.log | a3fd5e37f1434b414f258d23f6157a3422045e02 | `review/ord0355-r2-readings/raw/N2R2-E.log.txt` | `53e078a0083a54e5ff6f4a6961e8876781a503d1` |
| N2R2-F.log | 8f87c22d2752e29340c51d7ccbd1ca5a1c4cb7fa | `review/ord0355-r2-readings/raw/N2R2-F.log.txt` | `f5d4981fad080bbe42cdf1590d985fa8ac35452f` |
| N2R2-G.log | 9f85789c94afe16f4008bea98cb57316dbe1bd8e | `review/ord0355-r2-readings/raw/N2R2-G.log.txt` | `5a13a40a8f3cf78cd2a7d62e51293cb47919810b` |
| N2R2-H.log | daa8cc14c4717d0a8cf29150fbb5753212539ad3 | `review/ord0355-r2-readings/raw/N2R2-H.log.txt` | `a34563d3f625dcbd255194addf57d6b5ddf37c1a` |
| N2R2-I.log | c92504f027f31e12e89f23cc87591232a12abc0e | `review/ord0355-r2-readings/raw/N2R2-I.log.txt` | `c9722114c1f7eb09a57680de33933d57b20914e8` |
| N2R2-J.log | 9d8a52babcfdc6358ab15df345f7ab6b344aedfc | `review/ord0355-r2-readings/raw/N2R2-J.log.txt` | `4161255016db9ed89d4e7631c341e1bf4c2d707d` |
