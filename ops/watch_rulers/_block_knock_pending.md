## commander 敲门状态 @2026-09-22T23:10+08 —— **第七十四次敲门补充卡在输入框**：浏览器面板 `visibilityState=hidden`（正是 HJ-P1 那条规则的现场版）；正文未丢，窗口回前即补发

```text
正文（666 字）完整保留在原线程的输入框里（composerLen=666，URL 未变、仍是原线程）
页面状态：document.visibilityState="hidden"、document.hasFocus()=false
症状：send 按钮不渲染（HAS_SEND=false）；合成 keydown/keypress/keyup 也无效
```
**这一幕正是 HJ-P1 19:56 发现的规则在 Commander 自己身上的现场版**：非置前状态下页面行为不可靠。我当时想让面板自己"等回来"，但**没有用户在场把浏览器面板带到最前，我就点不出去**。
⇒ **状态记为 `DELIVERED-UNACKNOWLEDGED`**（按既有规矩：窗口不可达时不得记成已送达）；正文内容同时已在总线 `e60f04314e56e9f2` 镜像覆盖（写入端校验四格 + demo evidence producer 五步都在账本，两条产品决定不会丢）。
⇒ **下一轮巡逻第一件事**：查 `visibilityState`，回 `visible` 即点击发送并回读。

**本块同时确认的账本侧进展（不依赖那次敲门）**：
- 仲裁 `5778570154` 两笔产品决定（写入端两层校验 + demo evidence producer 五步）已逐字落 ORD-0219 amend 并转达 C；
- HJ-P1 的两份独立 JSON 已代发（`evidence/hjp1_0223/`，两次运行 blob sha1 相同 `e7fca5dab317ed81`）；
- F 的三笔新修已发布（`evidence/ord0210/` 下两个分笔 patch + 累计 patch + 修正后 yaml），待其第二次源审。

现场：working tip `bce7269`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动；那把 key 仍未轮换。
