# 值守交接简报 · 2026-09-25 夜 → 09-26 早 11:00

写给"下一拍的我"或任何接手值守的会话。**这份简报自带全部坐标，不需要读旧对话。**

## 我的职责（用户原话拆出来的四件事）

1. 解决包工头（号令者 `494abfd7`）在跑工作流时遇到的困难；
2. 谁停下了就发消息让他继续；
3. 保证车队至少工作到 **2026-09-26 早上 11:00**；
4. 检查工人有没有在干活 = **读他们的任务**，不是看进程。

**Codex 客户端不在范围内**（用户 2026-09-25 21:50 明确说「现在不用照看codex了」）。别去碰那个 app，也别再敲它的窗口。

## 车道名册（总线自署 ↔ 会话 id ↔ 原始标题）

| 名号 | 会话 id 前缀 | 会话原标题 |
|---|---|---|
| 号令者 / 包工头 | `494abfd7` | 评估窗口任务表现 |
| F | `8ccd71d8` | 实现 Simulation 面板组件 |
| B | `c01d72a3` | 生成 Simulation 插入点地图 |
| D | `e345b9d6` | 优化移动端夜间 UI |
| E（红队） | `d2305848` | 红队接管重验 ORD-0204 |
| HJ-P3 | `aad2d1f2` | Simulate impatient mobile user |

**字母名册会随班次漂**（`beat.py`/`patrol_watch.py` 里旧标签曾把 `c01d72a3` 标成 "C"、`8ccd71d8` 标成 "面板 B"）。指认车道一律带 8 位 id，别只说字母。

## 判"停没停"的凭据（按可靠性排序）

1. `python -X utf8 qoder_watch.py 1 0` → **10 条**会话距上次写入的分钟数（名册会漂，`fleet_state.py` 现扫 `projects\D--moodle\*.jsonl`，只排掉我自己 `42d1a6fa`）；超过 20 分钟会顺手把该会话**最后一条 assistant 文本**抄进 `watch_qoder.log`。
2. `python -X utf8 last_text.py <id前缀>` → 单条会话的最后 user / assistant 文本。**敲之前必做**。
3. `python -X utf8 patrol_watch.py` → 60 秒字节增量（**前台跑、不要接管道**，管道会吞掉输出和退出码）。
4. `python -X utf8 pending_check.py` → 谁被最新那块点名且 idle；判据含「块名义时间 + 20 分钟」那道（09-26 07:26 补，见下节）。`--selftest` 16/16。
5. `python -X utf8 inbox_latency.py` → 单写者代插的**实测等待分布**（mtime=作者写 → 尾标 `.inserted_HHMMSS`=插入）。别再用"最老一枚的年龄"当管道健康度：09-26 07:07 我就是这么报的，全量重算后中位只有 2.3 分钟。
6. `runtimeState`（`list_chat_sessions`）**不可信**：它会一边报 running 一边冻死。
7. **不要** `read_chat_session` 打 `494abfd7` —— 那个 JSONL 126 MB，会倒出几百条工具记录。

## 什么时候敲、什么时候闭嘴

- 尾句是"交了 / 等 X 验收 / 等仲裁回字" ⇒ **不敲**。催一个刚交完单的车道只会让它空转或重复投递。
- 尾句是具名阻塞（等某个依赖、等用户动作）⇒ **不催**。
- 账本收件箱里有点名它、它还没回的新块，而它 idle ⇒ **敲一次**，只发一行"账本里有给你的 verdict，去重读"，**不带任务正文**；发完就等，不追第二遍。
- **`WAKE_CANDIDATE` 是分流提示，不是开枪许可。** 它只证明"账本比她新 + 那块出现过她的名字 + idle ≥ 8 分钟"，而"出现过名字"很可能只是顺带提及。今晚两例真读数：
  - 22:34 我敲过一次（有效，她醒来做完 a4）；22:48 尺又报她 —— 事后读她尾句才发现她已是"等号令者读她"，**那时该敲的是号令者不是她**。
  - 23:25 尺第二次报她（idle 13.2m）。她 23:11 的尾句写得很清楚：「a4 已获号令者三把尺全过，ORD-0314 实质收口只差他在账本里落 CLOSED」⇒ **不敲**，欠的是号令者手上的动作。
  - 09-26 07:26 报 S1 `8e094dec`（idle 11.8m）——**根因是尺自己的判据**：它拿"账本 mtime 比她新"当"有新字给她"，
    但账本 mtime 会因为**别人插块**前进，点名她那块其实是 03:35 的旧字、她 07:14 交完 ORD-0339 之后早看过 ⇒ 假候选，没敲。
    已修：加「她最后落盘 < 块名义时间(`CMDR-MMDD-HHMM`) + 20 分钟」，并把两个时间分开打印；`pending_check --selftest` 16/16（含 4 枚新反件）。
  - 所以开枪前先做一件事：`python -X utf8 last_text.py <id前缀>` 读她最后一句，问"**她欠的是信息，还是别人手上的动作？**"——欠信息才敲，欠动作就不敲（要敲也敲那个欠动作的人）。
- 冷却：`wake_pings.json` 记每次敲门，40 分钟内同一车道只报 `SUPPRESSED`（`pending_check.py --selftest` 7 向，含 3 向冷却）。别指望记性，尺会替你拦。
- 死尾（`runtimeState=running` + `queuedTurnCount≥1` + 落盘冻结）⇒ 需要先掐那一回合；掐之前必须先看窗口标题确认是自己的会话。
- `error` 状态常常是链路抖动的假红（`QODER_EXECUTION_CONTROL_FAILED` / `Network attempt failed at connect`）⇒ 先量字节再决定，别急着重发；实测 3/5 会在 ~10 秒内自愈。

## 23:07 之后的新瓶颈（必须盯）

车道不再直接写账本：交付先落 `D:\moodle\_qoder_ledger_inbox\<lane>_<HHMM>.md`（首行 `### `），由号令者 `ledger_inbox_apply_r1.py --apply` 代插，他自己承诺 **≤15 分钟一轮**。
⇒ 协调链多了一个**单点瓶颈**：他一旦睡着或卡住，车道的交付就永远进不了账本，而**从车道那一侧看一切正常**（照常落盘、照常发帖），我原来那套"看会话有没有在写字"完全看不见这种停摆。
`inbox_check.py` 专量这个（三向自检 PASS：60 分钟前的块必报 / 只有新鲜块不报 / 空箱不报）：根目录存在 >20 分钟的 `.md` ⇒ `INBOX_BACKLOG`；已插的会被改名成 `*.inserted_*` 移进 `_processed`，所以不会误算。首枚实测往返 3 分 29 秒（E 23:10 落箱 → 23:13:29 号令者代插）。


## 通道与硬边界

- 账本 `D:\moodle\CITYNEXUS_AGENT_CONTROL.md`（约 5.96 MB）**只读，我永远不编辑**。今天有人用 `contents` API 读到 0 字节后整本重写，差点毁掉它 ⇒ 我这边挂了 `ledger_guard.py` 独立盯远端体积，下降 >5% 或为 0 就报警，好尺寸的 `commit+blob` 存在 `ledger_guard_state.json`。
- 权威分支 `commander/control` **只有号令者能移动**（`AUTHORITATIVE_BRANCH_SINGLE_WRITER_V1`）。我不 push、不建分支、不动别人的工作树。
- 总线 = `Canshu-King/CityNexus-Workspace` Issue **#1**（产品仓库的 issue 会 404，那不是故障）。读增量：`python bus_new.py <水位线id> --repo Canshu-King/CityNexus-Workspace`；回读单条：`/issues/comments/{id}`（**不是** `/issues/1/comments/{id}`）。大页面会中途 reset，别拿整页当完整。
- 任何外发给 GPT/总线的帖子，**最后一句必须逐字取自** `D:\moodle\_qoder_cmdr_ref_20260921\live_checks\CLOSING_LINE.txt`（83 B，blob sha1 `b82ca923501c312b6931ad894c607ab9e43e1137`，22:33 现算现证：`sha1("blob 83\0" + 文件字节)`）。不许手打、不许凭记忆抄 40 位。
- 勘误一律发**新帖**，不改不删旧帖。
- 不打印预览 Basic 口令、不打印那把泄漏的 API key（值只在 `D:\moodle\_qoder_preview_20260920\run\preview_auth.txt`，TAB 分隔）。
- 不建 cron、不建"无上下文自动代理"（用户明确反对）。检测交给脚本，判断留在会话里。

## 只有用户能解的两件（别代做、别催）

1. 两枚 key × 两层的轮换（含 `HKCU\Environment` 那一层）。
2. `:8000` 数据面 —— 仲裁 Q61 已裁"保持 NOT AVAILABLE 是**决定**，不要让任何 Agent 偷补"，所以它**不是**待修项。

## 已知环境坑（今天真咬过）

- 三个 CPython，只有 3.12.14 那个 venv 能跑套件；shell `date` 打的是 UTC 而机器在 +08 ⇒ 写时间戳前先 `date` 再抄。
- PowerShell 5.1 按 ANSI 读无 BOM 的 `.ps1`，脚本里的中文会吞引号 ⇒ 生成的 `.ps1` 必须纯 ASCII。
- Python 字面量里出现 `C:\Users\...` 会撞 `\U` 转义 ⇒ 用 `r"""…"""`。
- bash 会把 PowerShell 的 `$_` 吃掉；跨语言传中文一律走 UTF-8 文件，不走命令行。
- `computer-use` MCP 今晚 20:53 崩掉后没再回来（`ECONNRESET` → server 消失）。要用它之前先 `mcp_list` 确认。
- 这台机器 8 天 8 次蓝屏（`ntoskrnl` + WHEA 处理器内部奇偶错）；合盖动作在 "Turbo" 电源计划里查不到，别合盖。

## 现在（09-26 05:00）的状态快照

- **车道名册是 10 条，不是 6 条**（03:21 才发现号令者半夜新开了四条工具车道）：
  号令者 `494abfd7` · F `8ccd71d8` · B `c01d72a3` · D `e345b9d6` · E 红队 `d2305848` · HJ-P3 `aad2d1f2`
  · S1 `8e094dec`（Q64 前端扫描）· S2 `d9e2c9ae`（Hermes 测试移植）· S3 `a17ae861`（工单状态板）· S4 `1d64acf5`（AST 污点尺）
- 权威尖：03:35 那次落地是**今晚第一次移动产品字节**（ORD-0302 落并部署到手机，代次 `9a669c8b…`）。手机侧仍按 Q61 不再换代。
- 05:00 读数：七条在 0.4 分钟内有落盘；HJ-P3 `DECLINED`（九臂重跑已交，等验收）、E parked 27 分钟（刚把 ORD-0302 记进 CLOSED + Q68 落章）、S3 parked 101 分钟（她的状态板尺已交付）。`quota_dead=0/6`。
- 收件箱：04:50 起 `FRESH`（S4 那枚等过 31 分钟后被代插；我没发帖，他自己巡逻到了）。
- 仪表四把：`fleet_state.py`（名册自动发现）、`pending_check.py`（点名+账本更新+idle，带 `--declined` 与 40 分钟冷却，自检 7/7）、`inbox_check.py`（单写者瓶颈，自检 3/3）、`quota_check.py`（日额度死亡，自检 4/4）、`ledger_guard.py`（远端体积）；`qoder_watch.py` 每 5 分钟一轮并**自报 WATCH_GAP**（自检 4/4 含跨午夜）。
- 巡检批 `bbxxaqpxe` 到 05:50，之后每批 18 轮接力到 11:00。

