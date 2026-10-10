

### CMDR-0925-1655 两枚号令者自查（16:55+08）：换代的现成工单 + X-5 在**已部署代**里的字节读数

一、换代工单已写：`live_checks/SWAP_RUNBOOK.md`，发布件 `evidence/cmdr-runbook/SWAP_RUNBOOK_r1.md` blob `e8588b257176b9b1a5fd08de2080ea883c7014c7`（5760 B）。它把今晚 ORD-0302 落地后那一跳要做的事按顺序钉死：前置四条（P1 已落地且尖相等、P2 两把尺跑在**要部署的那份字节**上且 `claims checked > 0`、P3 无硬链快照、P4 数据面状态如实标）、`DEPLOY_BUNDLE_RETENTION` 的**先并资产再换 index**、隧道侧 `phone_side_probe_r1.py` 的五条判定、发布路径冻结（改名=新文件，绝不覆盖已引用件）、以及这一串仪表坑（共享端口归属、管道吃退出码、shell `date` 是 UTC、反斜杠/反引号/直双引号被吃、`git rev-parse <rev>:<path>` 找不到也回显参数）。最后一节明写这份工单**不覆盖**什么：不覆盖重启后端/`:8000`、不覆盖真机 SW 缓存驱逐、不覆盖"乘客能不能走完一次规划"那道门。

二、X-5 到底在不在用户设备上那代里——我自己读了一遍**字节**（不是运行时）：`evidence/cmdr-phone-chain-1654/bundle_string_read_r1.json`。从 `:4781` 取 `index.html`（1200 B），它点名 2 枚资产，逐条取回并算 git blob sha1：JS 是 `/assets/index--q2k569d.js`（1253228 B，blob `d6e8d468c86a029d3294ac276db53fcdd396cada`），与磁盘逐字节相同 = True，无一枚以 HTML 兜底。句子里的承诺串「原因原文在」命中 1 次、`NO_PLANS_PRODUCED` 命中 2 次、「技术详情」这个标签命中 8 次。
⇒ 结论只到这一步：**X-5 的代码路径确实在手机当前被服务的那一代里**（这比我早上做的"源码区域级 sha1 相等"更近一层）。但"屏上真的印出这句话"仍要一次运行时读数，而那 5 形（200 + 空/畸形 payload）需要后端在跑——数据面现在是断的，所以那一半照旧记 `NOT-DEPLOYED-OBSERVED`，等 `:8000` 恢复（等用户回字）或由 HJ-P3 在她自己的 rig 上量（ORD-0306 已加代次绑定 `### CMDR-0925-1652`）。

纪律：本拍权威线未移动、0 ref 推送、产品码 0 改动、`demo/reset` 0、`_live`/`_preview` 0 读写、凭据 0 打印（我只取未鉴权的本地预览口，隧道那条走文件路径不打印值）。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度