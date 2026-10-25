# Issue #51 第二刀：容器执行入口与宿主密钥代理

基于已推首轮 `3d783049fa2da1232fbd545bf09298f9fcf49f51`，按 Issue #51 外审评论 `6397975375` 推进。本刀只改 `tools/developer_companion/` 和本次结果文件，产品后端、Qoder 手机页面、课堂启动器保持原提交。

## 已交付代码

- `run` 和 `demo_fix` 默认选择容器模式。未配置镜像/代理、引擎不可用、探针失败时返回 `BLOCKED_EXTERNAL_AGENT` 与具体错误码，不自动转宿主模式。原本机 DSH 实验需显式 `--execution-mode local`，继续限主人本机 CLI。
- 新增 Docker 运行器和显式构建定义：非 root UID 10001、无外部网络、只读根目录、移除 capabilities、禁止提权。只挂任务 checkout、只读任务 Git/指针和通信目录。镜像必须是已存在的不可变 `sha256` ID，任务不会拉镜像。
- 容器内部 HTTP → 文件通信 → 宿主固定模型代理。上游 key 文件不挂载、不传到 Docker 参数或容器环境；宿主代理只允许本机网关的 `/v1/chat/completions` 和一个指定模型，拒绝任意 URL、请求头覆盖、模型切换和重定向。初版镜像登记 `cn:deepseek-v4.1-flash`。
- 读取探针尝试宿主 canary 的原路径/宿主映射路径、凭据与 Docker socket 路径，并检查 UID、根目录写入和外部网络。源码 reparse point 在挂载前拒收，通信文件读取拒绝链接并限制大小。探针失败不启动模型。
- 容器内 Git 为只读，源码提交仍由可信控制面完成。停止时要求确认容器已退出，否则标记 `CONTAINER_STOP_NOT_CONFIRMED`，不能报成功。
- 修复停止链路：取消会中止进行中的上游 HTTP 请求；SDK 初始化阶段收到取消时，不进入第一轮模型请求。

使用方法和镜像构建命令在 [README](../../tools/developer_companion/README.md)。代理复用宿主已有 `httpx` 依赖，不需要模型获得任何宿主凭据访问权限。

## 实测结果

```text
py -3.13 -m unittest discover -s tools/developer_companion/tests -v
Ran 25 tests; OK (skipped=1); exit 0
```

即 **24 项通过、1 项跳过**。跳过的是宿主符号链接创建测试，因为当前 OS 账号不允许创建链接；不能把它算通过。

本轮实际运行了 Node HTTP → 共享文件通信 → Python 宿主代理 → 本机测试上游，验证请求、SSE 内容、固定模型、密钥不进入通信文件及拒绝重定向。测试中真实阻塞上游响应体，然后执行取消，确认请求线程结束。上游是 `TEST_UPSTREAM`，不是实际供应商模型。本轮真实模型请求数为 0，未重复首轮 DSH 请求。

两个 `.mjs` 的 `node --check`、profile YAML 解析、Git diff-check 均通过。产品后端文件未改，没有重复首轮 9 项产品测试或浏览器案例。

## 容器实跑的当前阻塞

实际调用容器预检得到 `CONTAINER_ENGINE_UNAVAILABLE`，没有启动 worker，也没有读取真实代理 key。

本机已安装 Docker Desktop，但引擎命名管道不可用。尝试正常启动、正常重启，重启报告后台进程退出超时；限定当前用户 Docker 进程退出后重新启动，引擎仍不可用。Docker 日志明确报告 `sailor-ingest.sock` 的 AF_UNIX bind 地址冲突。检查该套接字时文件并不存在，因此没有删除或改名。另发现 Docker 本地目录为迁移到其他磁盘的 junction；它是否造成此错误尚未确认，没有改变迁移布局，也没有重置 Docker、清除镜像/卷或触碰数据库。

因此 **镜像未构建、容器内 DSH 未运行、容器恶意读取/逃逸未实测**。当前代码不能作为“已经证明读不到宿主”的验收结果。引擎恢复后，需要显式构建镜像、运行真实读取探针与 DSH，再补模型内部浏览器操作和任务截图资产。PR #52 保持 Draft，不开放 Traveler API、共享 Web UI 或局域网接口。

日志与机器回执：[测试日志](developer-companion-container-20261025/control-plane-tests.log)、[真实引擎预检](developer-companion-container-20261025/engine-preflight.json)、[源码哈希与证据分级](developer-companion-container-20261025/receipt.json)。首轮真实 DSH 源码修改、9/9 产品回归和回滚证据继续保留在前一份报告，本轮没有升级其证据等级。
