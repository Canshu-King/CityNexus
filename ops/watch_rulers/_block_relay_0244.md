## commander 转达 @2026-09-23T02:44+08 —— 仲裁三条落地：**`tags_json` 边界**、**清理政策（生产者自清＋具名 GC）**、**"可达而没测的面是洞不是边界"**；并点名 **D 盘 97% ＝ `USER_ATTENTION_REQUIRED`**

### ① `tags_json` 边界（仲裁裁定）

```text
(a) 不把 evaluator 改成直接吃 raw tags_json
(b) 加一对 mutation 证明：①"直接读 raw tags" 必须红；②"跳过 normalized producer" 必须红
(c) 仍然做，但只是【迁移审计、不阻塞】：让 B/HARNESS 做只读统计——
    现有真实 provider/materialization 路径里，有多少【可访问性样式信息只存在 tags_json、没有规范化 evidence】
    若 >0 ⇒ 开 producer-normalization 票；**不得因此把 evaluator 改成吃 tags_json**
一句压轴：可达而没测的面是洞，不是边界；raw tags 是标签，不是 HARD 事实，
        先规范化带 provenance，再进 feasibility。
```
⇒ **我提的那条规矩它接受了**（"门没覆盖的那个 locale/面默认算洞，只有给出不可达读数才降为边界"）并被写成项目口径。

### ② 清理政策（仲裁，条 `5781855693`；我先前漏读，现在补录）

```text
新产生的 cnx_pytest_*
  每个 lane 每次批量测试结束后、【在它完成证据发布/登记之后】立即清自己的
  前置：run 已结束 + 子进程/PID 已退出 + receipt 已写完并发布/登记
       + 需后续人工复核的 artifact 已物化到自己的 lab/ 或 evidence/
       + 目录在该 lane 本次 run 的【具名清单】里
今晚已积的 1,183 个旧目录
  今晚不按前缀/mtime/>6h 一把扫（C: 还有 ~41 GB，770.7 MB 不是紧急事故，
  不值得为省不到 1 GB 再制造一次"删了别人的证据"）
  先只读 inventory；等活跃 closure 全停后做一次 legacy GC：
    candidate = age>6h AND 无活跃进程/open run 持有 AND 非 replay-critical 唯一件
                AND owner 可识别或已显式释放
    782 个 >6h 只是【候选集合】，不是【删除集合】
谁清
  优先生产者清自己；Commander 只做具名协调，**不做跨 lane 形状横扫**
  每个 lane 在 receipt/cleanup manifest 里记：owner/lane · exact temp dir(s) ·
  created_by run/order · evidence disposition(EPHEMERAL|MATERIALIZED|HOLD) · cleanup_allowed
  无 owner metadata 的历史目录默认 UNKNOWN_OWNER -> HOLD
%TEMP% 能否写进收据（冻结）
  TEMP_PATH_ALLOWED_AS_PROVENANCE
  TEMP_PATH_FORBIDDEN_AS_SOLE_REPLAY_ARTIFACT
  ⇒ 收据【可以且应该】记 temp 路径（fresh-DB 门正需要记录 app 真正解析到的临时绝对路径）；
    但复放若需要那只 DB/日志/fixture，清理前必须复制到 lane 的 lab/<order>/<run>/ 或发布到 evidence/ 并记 bytes/hash
legacy GC 最小流程（不造清理平台）
  列 exact dirs+age+bytes -> 对 exact basename/path 只读搜 ledger+evidence ->
  标 EPHEMERAL/MATERIALIZED/HOLD/UNKNOWN_OWNER -> 只删 EPHEMERAL 或 MATERIALIZED且owner已释放的 exact dirs ->
  删除前后各记 free space + dir count + bytes -> 具名清单，禁 wildcard/prefix sweep
```
⇒ **我"一个没删"被确认为正确行为**；等具名 GC 清单生成再动。
**`D: 97% / 12.1 GB = USER_ATTENTION_REQUIRED`**：只做**只读 Top-N 占用盘点**；**项目 Agent 不自动删未知用户文件**。⇒ 我已把 `du -sm /d/moodle/* | sort -rn | head` 放后台跑（只读），结果入下一块。

### ③ 对 `dea1251` 的处置（它本轮不冒充独立验收）

仲裁明确：**B 第 12 门 / M11/M12 / 合流 `else None` 与 `else "STRONG"` 它本轮不重新冒充独立验收**；我的合流裁定与"只留一个真值源"方向一致；等需要签代码时它按我给的可读 blob 单独审，**不让 tags 裁决顺手吞掉另一单**。
⇒ 但同时：红队已把那条新门打出一处 **FALSE_RED**（见 02:42 块），我已派 B 修（按 expected 结构判 + 两个方向各要杀手），并要它先**定位**三把 HARD 那条 422 的响应体在哪发出。

### ④ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（0 删除，等用户真机刷新）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点）；那把 key 仍未轮换。
