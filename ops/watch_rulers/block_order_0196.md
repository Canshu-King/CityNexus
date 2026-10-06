- id: ORD-0196
  to: 5ea3bedc
  priority: P0-critical
  if_head: f2708dd
  order: |
    【**REVOLUTION-LAB-001 已开台**（用户 01:02 直接下令：总线 `5764349798` USER EXPERIMENT ORDER）。你是这条实验车道的主建造者，不是报告撰写者。】
    现场（我已建好，别重复建）：
    - worktree `D:\moodle\CityNexus-RevolutionLab`，分支 `experiment/deepseek-hermes-revolution`，
      **父 SHA = `f2708ddf04f4e4cd11388a0e23590fee9e9185ed`**（今晚权威线最新一片：ORD-0167 第一片），
      台账文件 `REVISION_LAB_PARENT.json` 已写入 worktree 根（含边界与 charter 缺失说明）。
    - **依赖未复制**：不要对 `node_modules` 做 junction/symlink（D-7 事故形状），要就显式复制或自装。
    实验目的（用户原话的转述）：**在隔离实验分支上给 DeepSeek + Hermes 明显更大的自主权，允许它质疑/重写现有架构**，
    用来回答"当前架构是不是已经过度约束"。**这不是替代权威线**，是竞争性实验分支。
    实验室内放开（**不必每个微改动开一张 ORD**，一块 lab 板 + 一条 running log 就够）：
    全仓可改 / 跨 backend-frontend-contracts-tests 重构 / 删废弃抽象 / 换内部 API / 换服务边界 / 增删依赖 /
    重写状态流 / 跑 shell-code-browser-fs 工具 / 直接读写**一次性 lab 库** / 跑 migrations-seeds-resets /
    重做前端段落 / 拉兼容 OSS UI donor / 造本地小工具 / **不同意并可替换现有架构**。
    **只剩四条爆炸半径边界**（其余一律放开）：
    ① 永不改权威/main 工作树与受保护历史；② 永不对用户活库/预览库做破坏性实验（只用 lab 内一次性库）；
    ③ 永不外泄/复制/提交任何密钥；④ 永不执行真实付费、真实预订、不可逆的外部动作。
    【一处我必须上报的缺口】命令里说"我已备好 lab charter，读/拉分支 `arbiter/revolution-lab`，
    文件 `docs/REVOLUTION_LAB_CHARTER.md` 与 `docs/REVOLUTION_LAB_AUTONOMY_PROFILE.md`，commit `847a3ceb` / `43d6af53`" ——
    **我查了：该分支在 GitHub 上不存在，两个 commit 返回 404/422。**
    ⇒ 所以本单的内容来自**命令正文本身**，不是那份 charter；**在 charter 被推上来之前，任何人不得声称"已按 charter 执行"**。
    ⇒ 我已把这件事回报用户与仲裁，请他们推送该分支；推送后你第一件事就是读它并对本单做差异更正。
    【与主线的关系】不抢 B/C/F/D/HERMES 的权威所有权；lab 里怎么乱都行，**唯一不许**是把 lab 的结论当权威线的验收证据。
    【交付节奏】实施优先、文档其次；每小时一条 running log（做了什么 / 否证了哪条现有约束 / 若要移植需要动哪几处）。
  status: DISPATCHED@2026-09-22T01:3x+08 by 494abfd7（lab 已建台并记录父 SHA；charter 分支缺失已如实标注，未冒充已读）
