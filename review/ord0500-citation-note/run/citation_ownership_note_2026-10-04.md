ORD-0500 全线尺的归属清单（2026-10-04 这一天的第 1 枚，也是唯一一枚）：本尺看到 185 条引用，判 173 条（我自己名下的），不判 12 条，出自 9 位作者 commit。不判的那些我一枚没改。

按形状算（若它们归我判会报什么）：BLANK_LINE_CITED 9 条、ORPHAN_BARE 1 条、UNRESOLVED_PATH 2 条。

| 引用所在（path:line，现读） | 机械判语 | 写下那一行的 commit（完整 sha，可 cat-file） |
|---|---|---|
| backend/tests/test_qoder_ord0383_journey_soft_delete.py:6 | ORPHAN_BARE | 9dab83eb0a5f4fc98e4df138d10123b4b01e0453 |
| backend/tests/test_qoder_ord0386_plan_version_history.py:5 | BLANK_LINE_CITED | 244fa3851ab5cf8fc9d3b02330516153634d46ec |
| backend/tests/test_qoder_ord0434_share_grants.py:4 | BLANK_LINE_CITED | 6ce96146e020eca6528db05c9fca4ebd3e12183a |
| backend/tests/test_qoder_ord0467_v13_contract_family.py:3 | UNRESOLVED_PATH | 942b7f239f723456cfa70a6d4fb664fac8fa1000 |
| backend/tests/test_qoder_ord0490_shared_after_restore.py:319 | BLANK_LINE_CITED | 5972c09578fb57ada8e9725f879435a11ec32bd9 |
| backend/tests/test_qoder_ord0490_shared_after_restore.py:418 | BLANK_LINE_CITED | 5972c09578fb57ada8e9725f879435a11ec32bd9 |
| frontend/src/components/v8/MapPanel.tsx:739 | UNRESOLVED_PATH | 1943db0749c6ce773aa3c2747cfe556a18ec5dac |
| frontend/src/features/access/accessDoors.ts:7 | BLANK_LINE_CITED | 17291be2e174eb0b8f1c7d717fbb50efd1358789 |
| frontend/src/features/inbox/shareGrantRead.ts:33 | BLANK_LINE_CITED | 36841487f9b3cd52dd6a7b8bfd231a11d93d3386 |
| frontend/src/features/pending/pendingSet.ts:289 | BLANK_LINE_CITED | de1aaf321ab5950fa73876697ec029dcaac63a65 |
| frontend/src/features/poster/posterShare.ts:81 | BLANK_LINE_CITED | 36841487f9b3cd52dd6a7b8bfd231a11d93d3386 |
| frontend/src/features/studio/planVersionHistoryCopy.ts:16 | BLANK_LINE_CITED | 244fa3851ab5cf8fc9d3b02330516153634d46ec |

读数出处：`citation_audit_r21.json`（本车道窗口内现跑的全线尺件，取数 `python tools/citation_audit_r8.py`，它扫 74 枚文件）。空一天这一枚就不发，按 2026-10-04 那句裁语②办。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
