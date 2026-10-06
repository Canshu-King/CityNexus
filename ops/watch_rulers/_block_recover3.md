## commander 恢复 @2026-09-22T22:52+08 —— 预览链第四次重建（**新地址，请用户用这个**）；仲裁两笔产品决定落账

### ① 预览链（用户手机用新地址）

```text
新地址   https://sullivan-trail-gregory-postage.trycloudflare.com    ← 用这个
链条     cloudflared -> :4782 (auth_proxy) -> :4781 (vite preview) -> :8693 (uvicorn, _live.db, demo_mode=true, ai=enabled)
端到端   鉴权 health 200 {status:ok, database:ok, ai:enabled}
         鉴权 / 200 bundle = assets/index-BCF4ptyk.js（= 56d20ec 构建，线上包代次不变）
         匿名 scene 401｜匿名 / 401｜鉴权 POST demo/reset 403
用户库   重启后只读复查 journeys 3 / travelers 3 / plan_versions 19 / commitments 1 / bookings 1 —— 逐项未变
死链     前三条（fonts-facilities… / buyer-festivals… / brochure-humor…）都已写进 dead 文件
```

### ② 仲裁两笔产品决定（总线 `5778314066`，已落 ORD-0219 的 amend）

1. **写入端校验：要，分两层**（`UNKNOWN_RULE_CODE` / `HARD_RULE_NOT_EXECUTABLE` 必须分开、SOFT 按 soft 契约、hard-executable 落库后由 feasibility 按证据求值）——已照录四格边界，并注明与四个 SOFT 码的可行性层工作**不混成一笔**。
2. **"演示库要不要补无障碍证据生产者"仍未答**——这是 HARNESS 0/16 那条引出的范围问题（B 的两个码修完后能不能端到端演示），我在第七十三次敲门里又问了一遍，等它。

### ③ 工作尖

`bce7269`（20:56）——D 在 20:55/20:56 交了 ORD-0222 ② follow-up（创建成功后继续跟随播报）与其代次绑定。**我还没验收**（运行层归车道/GPT），只确认 tip 前进。
车道 22:5x 读数：多条在跑；F 交了三修与二审包（我 20:1x 已发布其 delta）；HARNESS 交了 0/16 证据发现。

### ④ 我的工具状态

`gate_streak.py` v2-2（佐证层，blob `4931d6526eb0a3ea`）、`publish_evidence.py` v3（blob `d0b1bb1eeb3d87f2`）、`bus_new.py` cursor 版——三者都已发布可读。等仲裁对 publisher v3 的第四次源审与 bus cursor 的源审计。
