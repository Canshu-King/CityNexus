# Lanes that themselves edit `frontend/src/features/planning/PlanWithAiSheet.tsx`

Method, per ref under `refs/heads/` on origin (authoritative line excluded), against base `b6a8ea5c625d7e3e82f7348fad57d595a8a403c0`:
1. `git merge-base --is-ancestor <sha> <base>` - skipped when the ref is already in the base.
2. `git merge-base <base> <sha>` to get the branch point.
3. `git diff --name-only <branch point> <sha> -- frontend/src/features/planning/PlanWithAiSheet.tsx` - non-empty means the BRANCH changed the
   file. Diffing against the base instead is symmetric and would also list the base's own edits,
  which is the method error in my earlier hand-off; that count is retracted below.

Refs scanned: 159. Branches that change the file on their own side: 28

- arbiter/anywhere-contract — sha `cbc112d64be0d51d863622b5028c7edb3f3c79d4`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- chatgpt-high-risk-auth-test-20260925 — sha `a9c2504274dd3284b1a98b6707f7c4c9f7071cc3`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- codex/harness-recovery-20260922 — sha `b7bbf7cce4d9739845fe9224f5d1d874d72548d2`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- codex/mobile-golden-path-20260922 — sha `827f0a0d25bdd4396fefdf8c67a87bd8ad300a37`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- eac/v19.2.2-realphone-codegate — sha `1da4d3d2eab20e3fb828a3814c0296fe5e9d178a`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- gpt-permission-probe-20260923 — sha `6398343fbab6bcca21de0355052289d10f1b7f30`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- gpt/revolution-r6-h11-r61-prep-20260923 — sha `187263c67a5348d565adfc5ad8f01877fb56267d`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- gpt/revolution-r61-h12-r62-prep-20260923 — sha `9fd3d221214901ba372924d60a8e9e0bfd859938`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- gpt/revolution-r62-r63-prep-20260923 — sha `1c3a2d019921dbfd2df00ec67085998615780b2e`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- gpt/revolution-r7-r71-prep-20260923 — sha `03f8d0e3f0025e6a5c088e87d3ce7d12bc608f4d`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- gpt/revolution-r71-r72-prep-20260923 — sha `d1a05785839ad08649c65d48080fd70dbd9446aa`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- gpt/revolution-r72-r73-prep-20260923 — sha `c7c5ccbb7d093a43558a94cdc4072586a2de6a5e`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- gpt/revolution-r73-r74-prep-20260924 — sha `d4bdbcbc84abf82caf3322ea87b9df9683d78d8c`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- gpt/revolution-r74-r75-breakthrough-20260924 — sha `eb165b9737b5ede483a252b2a2e09ac08c669973`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- hermes/validation-0212 — sha `5de4f770e4624154c485c8caa2161c677fcd304b`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- permission-probe/hermes-20260923-1048 — sha `7732decf07670324231ef2b86b42eabb5706e09c`, branch point `7d22cd0eb7840121ba42a5ba363e1a4c7ca1a7e7`
- review/0269-reparent-c79e2b4 — sha `5f319c0239b66efc18eeaf4b375772e6be936da1`, branch point `c79e2b4f4efe414dba22a071a7136ae10b5c84aa`
- review/0278-0253-on-45b0a5e — sha `0671704546f9c9ea1d1b57627b059124c7800803`, branch point `45b0a5e281cae9c37715173afd3ac5778f309ca7`
- review/0278-0253-on-5c4608ce — sha `9023e023c9e8612d2e51cef78ebda6af5d69556f`, branch point `5c4608cede6cb7bd5f3ac7e704bfee379ca47abc`
- review/0278-0253-on-6d041dcc — sha `833c413f9f2adb0f017eec0b4c944fc36f325975`, branch point `6d041dcce11d05f28a55abadd40717f321b4db38`
- review/0278-on-0269-rebased — sha `e7cf57986b5afd8137ba6f8255f337d19f41f19c`, branch point `9d82d7665384a5d4924bd4bea83e508a0b505338`
- review/0280-attribution-label — sha `48827a9d6402aaabffc5ff47b1540407fafed620`, branch point `45b0a5e281cae9c37715173afd3ac5778f309ca7`
- review/0280-attribution-label-r2 — sha `549ac8f1b20bc04e70eadbd238ade737eefbff01`, branch point `5c4608cede6cb7bd5f3ac7e704bfee379ca47abc`
- review/0292-arm-receipt-tooling — sha `954f61ac9c20d2e28e992a316b5ddcb1bbae0bc9`, branch point `45b0a5e281cae9c37715173afd3ac5778f309ca7`
- review/0302-unreadable-server-body-b3 — sha `2f191eb5fd1682a53cf95f883c7200f00cbb6ebe`, branch point `13af1ff4ba4516aa1a39cda67428ed4a2a34ac69`
- review/0302-unreadable-server-body-b4 — sha `4fc0de91c18a966f99fc40fcd7ce136a5e2b8936`, branch point `2344145ce6342b6ac32ac4d0955c0f524d8c9320`
- review/0302-unreadable-server-body-b5 — sha `b6e1dd3295aafa3330cc9142a4475ac359eb7a3e`, branch point `2344145ce6342b6ac32ac4d0955c0f524d8c9320`
- review/ord0310-keyless-deadline-d — sha `b025432ded0381d83ebf36b85202a345bede2fcb`, branch point `5aff3722d5c36c760a424f5fea5c3a771298f9ac`

Retracted: the `9` in my ORD-0359 hand-off block. That figure came from listing the last refs of
an ls-remote tail and diffing each against the base, which counts base-side edits and is not a
contending-lane count. The count that is measured by the method above is the list here.
