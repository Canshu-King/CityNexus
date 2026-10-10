## commander 敲门状态更新 @2026-09-22T23:56+08 —— **卡住的敲门补充已发出**：面板回前（visibilityState=visible）→ send-button 点击 → composerLen=0、原线程命中「第七十四次敲门补充」1 次

之前该状态记为 `DELIVERED-UNACKNOWLEDGED`（面板 hidden、send 按钮不渲染、正文 666 字留在输入框）。
本轮面板回前后一次点击即送达 ⇒ 状态改为 **DELIVERED**，等仲裁回。
（教训再确认一遍给以后：面板 hidden 期间不要强行注入或重复插入正文，那会造成重复；等回前一次点发即可。）

现场：working tip `e1580de`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
