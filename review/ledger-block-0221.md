### 🔬 e345b9d6（SESSION=e345b9d6）ORD-0221 交付：仲裁要的四件运行读数（①blob 我从 GitHub 自己回读核对；②两条配对反例＋一条按实报的 SURVIVED；③④可见文本 before→after，逐面分开量）@2026-09-22 19:0x +08 → 提交 **`b41b4cc`**

**报数六要素**：树 `D:/moodle/_qoder_integration_20260919`（有 .git）；`git log -1` = **`b41b4cc 2026-09-22 19:0x +0800 test(frontend): per-surface before/after readings for the wizard hint, and bytes_changed in the kill receipts (ORD-0221)`**；解释器 Node/Playwright ＋ `D:/moodle/CityNexus/.venv/Scripts/python.exe` = **3.12.14**；收集＝执行同一把形制：`python review/run_spec.py "e2e/qoder-wizard-hint-surface-readings.spec.ts" 4532 --config playwright.prod-gate.config.ts` → 收集 **3 节点**（1 real-seed ＋ 2 读数节点），执行 **exit 0 / 3 passed**（`review/run-run074597.log`；同形制前一把 `run-run074473.log` 亦 3/3）；`tsc --noEmit -p tsconfig.check.json` **exit 0**（`review/tsc-0221b.txt`）；`git status --short -- frontend` 空（`backend/tests/conftest.py`、`tools/verification/mutation_campaign.py` 两个**不是我的**脏文件我原样留着）。
**这些读数跑在 `b41b4cc`/`25165d9` 上，审的是 `50b35e0` 的行为——这条我用 diff 证明而不是声明**：`git diff 50b35e0..HEAD -- frontend/src` 只动 3 个文件、29+/14-，其中 `JourneyTrialSetup.tsx` 的代码行只有 `onUseTianjinDemo → onUseSealedDemo` 三行改名，**`missingStep` 在 ± 行里出现 0 次**（提示重算那段一个字节都没变）；`V8Experience.tsx` 1 行（同名改名的调用点）；`LocaleContext.tsx` 全是文案。**不混交**：`3e259bd`/`522c414` 的语义不在这四件里被签收，也没被我拿来当证据。

**① 证据面我自己在 GitHub 上回读了一遍**（`review/verify-ord0221-evidence-surface.py`，走 contents API，token 从 git credential helper 取、不打印）：

```text
https://github.com/Canshu-King/CityNexus/tree/commander/control/evidence/ord0216
  50b35e0__50b35e0.patch        8,343 B  blob d6b5caa03c34adda  -> MATCHES
  3e259bd__3e259bd.patch       27,113 B  blob dfb25bda4e2784e9  -> MATCHES
  522c414__522c414.patch        1,590 B  blob 74b2270ea3d29043  -> MATCHES
  50b35e0__50b35e0.files.txt      202 B  blob 41eac4f6df89156e  -> MATCHES
quoted-but-absent=[]  present-but-unquoted=[]
```

⇒ 四个 blob 名字、字节、sha16 与单里所引逐项一致，目录里既无缺也无多。**我接受这条结构性事实**：账本里的 SHA 对外部审计者等于不存在，`50b35e0` 我自己复核也是 422。今后我的交付块把"外部可读坐标"当成必字段——发布仍归你（`publish_evidence.py` 是你那条通道），我这侧负责把 patch 与清单交齐、并在块里引用你发布后的 blob。

**② 两条配对门反例（形制＝单节点 `--grep`，exact SHA `b41b4cc`，每把独立进程＋独立临时库；`bytes_changed` 是量具在磁盘上实测的文件字节差，不是字符串长度差）**：

| 反例 | 靶文件:锚 | mutation（改成什么） | anchor_hits | anchor_bytes | bytes_changed | exact nodeid | verdict |
|---|---|---|---|---|---|---|---|
| 留数字、删 caveat | `src/app/V8Experience.tsx` `<strong>{advisory.text}</strong>\n<span>{advisory.hint}</span>\n<div class="today-advisory-actions">` | 删掉 `<span>{advisory.hint}</span>` 一行 | 1 | 98 B | **−43** | `e2e/qoder-budget-advisory-tiers.spec.ts :: ord0212-stripping-the-caveat-while-keeping-the-number-must-go-red` | **KILLED** |
| 留 caveat、删数字（killU1 从未覆盖的方向，本轮新增） | 同上锚（90 B 段） | 删掉 `<strong>{advisory.text}</strong>` 一行 | 1 | 90 B | **−47** | `... :: ord0212-the-hub-keeps-only-the-tight-verdict-and-it-keeps-its-caveat-and-action` | **KILLED** |

两条变红原文（截自 `review/kill-0221-pair.txt`，控制台按 gbk 出所以 CJK 糊了，JSON/日志里是原字）：`the hub prints the derived number without its caveat: "3 天 · 2 人 · 每人每天约…"` ／ `the tight advisory lost the derived number: "按这个预算，住宿、交通和吃饭…"`。两把都 `restored OK`（跑完 SHA-256 还原）。

**⚠ 同一次里我把 `killV1` 也重跑了一遍，并把新的分面读数节点加进它的靶子——两条都 SURVIVED，这是按实报不是凑数**：`missingStep3 = [...missingStep1, ...missingStep2]` 改回 `= missingStep1`（anchor 72 B，bytes_changed **−35**）→ `ord0216-a-fixed-field-leaves-the-hint-on-the-next-step` **SURVIVED**，`ord0221-4-step3-visible-hint-and-live-region-read-apart` **也 SURVIVED**。原因由 ③④ 的读数给出，不是解释：**在第 3 步，两种拼写的可见提示都是"元素不存在"**（下面 ④ 原文），所以任何只读可见文本的断言都不可能杀掉它——旧缺陷真正残留的地方是 `.v8-sr-only` 播报区。⇒ 我此前 ③ 那句"最小回归点已修"的**门侧证明不成立**（那条门只能防"提示写死不含现值"这一类，防不住 HJ-P1 报的那一条），这条我按红队的判定收回，并按 ORD-0220 ② 重做。

**③ 第 2 步"改完当场消失"的 before→after 可见文本**（逐元素读 `textContent` ＋ 元素自己的 box；收据 `review/evidence/ui-overnight/ord0221-step2-visible-before-after.json`）：

```text
before（总预算=0，下一步 aria-disabled=true）
  元素 [data-testid="trial-required-hint"]  文本「还需要填写：总预算」
  rect top=1224 h=85 w=350   computed visibility=visible display=block opacity=1
  visuallyRendered=true   insideSrOnly=false   inViewport=false
after（同一屏把总预算改成 1500，中间不跳转、不刷新）
  元素 exists=false  文本 ""   —— 提示整块消失，不是被改写
```

量具自纠一条（写在这里免得下一个人重踩）：第一次我把"可见"定义为"有渲染盒且非 sr-only"，结果读到 `opacity: 0.282` 的**半透明淡入中间态**——提示是带 fade 上屏的（实测：刚拦下时 opacity 0，1.5s 后为 1，`review/run-run074395.log`）。现在 before 要求 `visuallyRendered && opacity === "1"`，有界 10s，等不到就带着最后一次读数报红。

**④ 第 3 步同一项的 before→after，并且"看见的"与"听到的"分开量**（先按 HJ-P1 的原路**强制按下**被拦的 下一步 让播报区真的被写过——防"没触发的桩读成绿"；收据 `ord0221-step3-visible-before-after.json`）：

```text
按下被拦的 下一步 时（播报区写入瞬间）
  #trial-next-reason  文本「还需要填写：总预算」  rect 1x1  insideSrOnly=true  visuallyRendered=false
第 3 步（把总预算改成 1500 后进入确认屏）
  可见提示 [data-testid="trial-required-hint"]  exists=false  文本 ""      ← 屏幕上确实没有残留（HJ-P1 18:07 的自撤成立）
  播报区 #trial-next-reason                     文本「还需要填写：总预算」  insideSrOnly=true  ← 仍在播这一句（陈旧）
  确认行 review-budget                          「CNY 1500 / 1000 · 我们替你填的」
```

⇒ 这一格按仲裁的口径落定：**没有可见残留可给我签**，残留只在读屏路径上 ⇒ 判类 `HUMAN_ACCESSIBILITY`，靶子是那个 live region 不按现值重算——我按 ORD-0220 ② 修，修完再交一条能杀的门。禁令遵守：全程没用 `body.innerText` 判可见（`method` 字段写进两份收据），没有拿提交说明代替读数。

**门禁**：新 spec 3/3（两把独立进程）；`tsc` exit 0；突变两杀一实录存活。**本车道 0 次 push**（按单："我已经替你把证据面建好了…不用自己发 GitHub"）——对外可解析坐标就是你那四个 blob，`b41b4cc` 若要上同一个证据面，说一声我把 patch 交给你发、不自己动 `commander/control`；未碰 `:4781/:4782/:8693` 与 `_live.db`；未 `demo/reset`；0 次 provider 出网；账本只追加本块。

status: ORD-0221 **DONE@2026-09-22T19:0x+08 by e345b9d6**（四件齐：①blob 4/4 逐项 MATCHES；②killU1/killU2 KILLED 带 anchor_hits/bytes_changed/变红原文，killV1 双节点 SURVIVED 按实报；③④可见文本 before→after 逐面读数）。**同时收回**我 ORD-0216 ③ 的门侧证明（该门防不住 HJ-P1 那条），改由 ORD-0220 ② 承接。
evidence: `frontend/e2e/qoder-wizard-hint-surface-readings.spec.ts`、`review/evidence/ui-overnight/ord0221-step2-visible-before-after.json`＋`.png`、`ord0221-step3-visible-before-after.json`＋`.png`、`review/kill-0221-pair.txt`、`review/verify-ord0221-evidence-surface.py`、`review/run-run074473.log`/`run-run074597.log`/`run-run074395.log`、`review/tsc-0221b.txt`、`review/ord0082_0087_kill_drivers.py`（killU2 新增、bytes_changed 上报、killV1 双靶）。**未 push**。
