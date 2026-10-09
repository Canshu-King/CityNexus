### SESSION=494abfd7 · 隧道侧我亲手量了（ ORD-0186 有一件可以升 REPRODUCED），但**发现一条必须写进晨报的真实现状**：用户手机上"没预录过的县"仍然被回 `unresolved:<hash>` + 「换个目的地」 @01:5x

`STATUS: TUNNEL-MEASURED-BY-ME + LIVE-BACKEND-GAP-CONFIRMED | 树：无改动（纯只读 HTTP 探针，凭据不出现在输出里）| 隧道 host 与 `:4782` 两条路径各测一次 |`

#### ① 隧道侧（真机走的那条路）
| 探针 | 带凭据 | 匿名 |
|---|---|---|
| `GET /manifest.webmanifest` | **200** | **401** |
| `GET /api/v1/destinations/capability?query=云和县` | **200** | **401** |
⇒ **manifest 的 401 悬案定性**：端点没问题；是**浏览器不给 manifest/SW 注册这类子资源带上 URL 内嵌凭据**。⇒ 属"预览代理的鉴权方式与浏览器子资源请求不兼容"，**不是产品缺陷**；我按"控制台噪声 + PWA 安装降级"记，**不立产品单**（要立也只能立在代理侧）。
⇒ 这条给 E 的 ORD-0186：**manifest 那一臂我复核成立**（401 只在匿名侧）。

#### ② 真正要进晨报的一条硬事实（我原样贴，不粉饰）
**用户此刻手机上，"输入一个没预录过的县"的结果仍然是错的**：
```
200 GET /api/v1/destinations/capability?query=云和县
canonical_destination_id = "unresolved:8fccf2bbf123e3df"   ← hash 当身份（R10 明令禁止）
destination_resolution   = "unresolved"
capability / reason_code = "UNAVAILABLE" / "NO_CANONICAL_IDENTITY"
recommended_action       = "CHOOSE_ANOTHER_DESTINATION"     ← 对一座真实存在的县说"换个目的地"
place_count              = 0，六类 coverage 全 MISSING
```
⇒ **原因不是没修，而是修好的东西没部署**：C 的身份修复在 `f2708dd`（我 01:2x 复跑 19/19 认了），但按 P0 冻结，**用户预览后端一直钉在 `53fe8e8` 不动** ⇒ 手机看到的行为仍是旧的。
⇒ 这条正是"权威树已修 ≠ 用户可感已修"，**晨报里我按 `REPRODUCED(树) / NOT-DEPLOYED(用户可见)` 分两格写**，绝不用绿的测试代表用户屏幕。

#### ③ 因此我建议（明早之前不擅自做）：开一条 **canary 后端**
在**自有端口 + 自有库副本**上跑当前 tip 后端，只给真人组与 Harness 走，用于验证"未预录县 → HYDRATABLE + 真解析"的用户可见形状；**主预览继续 `53fe8e8`**，P0 不破。
⇒ 要请仲裁一字确认（或我按 P7 七条成立后自然推进）：canary 只读用户不可达，不构成"部署"。
⇒ 顺带：**`P7_RESOLVER_INTEGRATED` 仍 false**（产品码 0 处消费 B 的 typed result），Harness / P1–P4 继续不唤醒。

#### ④ 我自己这边：账本第三次被刷成 CRLF，已按新规矩处理
- 本轮写入前发现 **18,018 对 CRLF**；我先做 **newline profile 检查 → 归一 LF → 可逆校验**，再写；
- 新建 `live_checks/ledger_write.py`：写前测 EOL、**邻域锚点（前一区块尾 + 目标结构 + 后一行）**而非裸行号/全局替换、**写后证明逆操作可还原**、**读后若文件被他人改过就 ABORT 不盲写**。本块即用它写入。

status: 隧道侧实测完成（manifest/capability 带凭据 200、匿名 401 ⇒ 401 属代理鉴权与浏览器子资源不兼容，非产品缺陷）；确认用户手机仍见 `unresolved:hash` + 「换个目的地」，原因是修复未部署（P0 冻结后端）；提出 canary 后端方案待批；账本写入器已按新规矩硬化并用于本块
