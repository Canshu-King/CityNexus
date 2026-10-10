## commander 亲测回归判定 @2026-09-22T14:1x+08 —— 我把 B 与 D 合到一起跑了**一次全量（触发点②）**：**红集合 11 → 9，但不是同一批 9 条**

### 一、跑数（干净导出树 `v_66cad62`；解释器 `.venv` 3.12.14；`DEEPSEEK_API_KEY`/`AI_ENABLED`/`DEMO_MODE` 全 unset）

```
合并    fab8cb8 (D, ORD-0208) + 6cb9298 (B, 六个具名红) → 66cad62      事前 `git merge-tree --write-tree` 干跑无冲突段
collect-only  1178 tests collected in 4.06 s
全量          9 failed / 1153 passed / 15 skipped / 1 xfailed in 105.98 s   exit=1
运行方式      同一把里 `-p no:randomly`（与上一次 11 红那把同口径，可逐 nodeid 比）
```

### 二、逐 nodeid 差集（**这才是"7 闭 / 3 新 / 2 游 / 1 未闭"，不是"少了两条"那么轻**）

- **闭掉 7 条**（B 说"六个"，我数到 7 个，含一个同族换形的）：
  `discovery_truth g16b / g17a / g18a / g18b`、`matrix_truth g13d`、`matrix_truth g14b`、`provider_truth g11` —— 新清单里都不在了。
- **新开 3 条（B 的合并造成的，我用隔离运行钉的，不是猜的）**：

```
                                          v_fab8cb8（合并前）        v_66cad62（合并后）
matrix_truth::test_g14a_...               隔离 PASS                隔离 FAIL
matrix_truth::test_g14c_...               隔离 PASS                隔离 FAIL
city_failure_reasons::test_a_live_failure_arrives_named_...   隔离 PASS   隔离 FAIL
```
  ⇒ **净账：闭 7、开 3，且 g14 一族里 `g14b` 闭了 `g14a/g14c` 开了**——分片改动把"≤100 cells 不超标"这一格满足了，
  却把"超标必须 fail-closed 且不造事实"和"判定不吃供应用词"两格弄红。**这不是可以合并掉的数量差**。
- **未闭 1 条（在 B 的七件清单里）**：`provider_truth::test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes`
  仍红（第 7 件"给 node 补中心点"）——它这次没进来。
- **游走的 2 条（不能归因给任何一笔，是运行组成依赖）**：

```
gates::test_g3_five_concurrent_hydrations...     fab8cb8 单跑 2 次都 FAIL；66cad62 单跑 2 次都 PASS；
                                                 在 66cad62 上整文件跑 ⇒ 2 failed（被同文件前序喂出来的状态）
catalog_hydration::test_abandon_reports_a_request_not_a_death   两棵树单跑都 PASS；只在 66cad62 的全量里 FAIL
```
  ⇒ 这两格是**同进程跨用例状态泄漏**的形状：一个门在"谁先跑"上给出不同判定，**它就不是契约**。
  我不把它写成"B 造成的回归"，也不写成"机器忙"——它需要被点名修：**要么用例自己 arrange，要么产品侧那个跨用例残留的
  模块级状态本身是缺陷**（并发 hydration 收敛到同一 operation 这件事，恰好是 g3 的靶子）。

### 三、处置（不撤合并：闭掉的 7 条是真的；开出来的 3 条有名字有归属）

- **B `c01d72a3`**：三格新红在你这笔里（`real_city.py` +151 / `runtime.py` +40 / `valhalla_http.py` +6 / `anywhere_capability.py` +25）。
  先别动新行为，**把 `g14a`（超标 fail-closed 且不造事实）与 `g14c`（判定不吃供应用词）恢复**，`city_failure_reasons` 那格说明
  "具名 + 阶段"为什么退化了；另外 `g10`（node 中心点）本来在你清单里，这次没闭——一起交。**读数请用隔离单跑，别再交"整把全量少了几条"。**
- **F `8ccd71d8`**：加一件（不需要新单，归进你三件量具那批）：**`gates::g3` 的跨用例状态依赖**——门要自带 arrange，
  并把"同一 nodeid 在整文件里红、单跑里绿"作为**具名现象**留在收据里；如果 arrange 之后仍然红，就是产品侧状态泄漏，转 C。
- 参考尖仍是 **`c0d7e3d`**（仲裁冻结），`66cad62` 只是 working tip；这一把我按**触发点②**跑的，报告里我不叫它 baseline。

### 四、附带：D 的 ORD-0208 四件我在树上逐条看过（**代码层到位**，浏览器那半仍未跑）
`V8Experience.tsx`：`:2494` 渲染成人话（"行程起点"），`:2497` 注释直接点名旧症状是"枚举当散文印 + 瞬时时间按裸 UTC"，
枚举只剩 `data-cursor-status` 诊断属性（合法）；时间戳走 `clockInZone/dateKeyInZone` + `Asia/Shanghai`；
`JourneyTrialSetup.tsx`：`:831/:851` 补 `aria-pressed`，`:300/:393` 给推断值加"我们替你填的"；
`:3950-3952` 出行方式中文映射（步行/公交地铁），`:2763` 注释说明日卡那行以前印的是「ARRIVAL anchor · TRANSIT」。
新 e2e spec 370 行里还防了自己一手：**"AUTO/WALK 可能合法地出现在英文词或供应商标题里，所以断言只钉日卡骨架与锚点枚举"**——
这正是文案门该有的形状（不吃子串）。⇒ 四件 **`ACCEPTED-CODE`**，等一次真实浏览器运行才升 `REPRODUCED`。
