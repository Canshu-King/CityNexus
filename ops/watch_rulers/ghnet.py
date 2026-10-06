"""一条 HTTP 出去、先按环境代理、代理死了就直连重试（09-26 17:07 加的）。

当时的读数：`HKCU\Environment\HTTPS_PROXY = http://127.0.0.1:7892`，但 netstat 里 **7892 没有任何进程在听**，
mihomo 实际听在 7897（pid 35752）⇒ 凡照环境代理走 HTTPS 的工具全部 `WinError 10061 由于目标计算机积极拒绝`，
而绕开代理直连 api.github.com 回 200。所以判"GitHub 不可达"之前必须先分清是哪一条链路死了。
"""
import urllib.error
import urllib.request


def urlopen(req_or_url, timeout=60, data=None, headers=None):
    """返回 (status, bytes)。先按环境（代理），失败再直连；两条都失败才抛。"""
    req = req_or_url
    if isinstance(req_or_url, str):
        req = urllib.request.Request(req_or_url, data=data)
    for a, b in (headers or {}).items():
        req.add_header(a, b)
    errs = []
    for label, opener in (("env", urllib.request.build_opener()),
                          ("direct", urllib.request.build_opener(urllib.request.ProxyHandler({})))):
        try:
            with opener.open(req, timeout=timeout) as x:
                return x.status, x.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()          # HTTP 层错误：不是链路问题，原样交给调用方判
        except Exception as e:
            errs.append("%s=%s:%s" % (label, type(e).__name__, str(e)[:80]))
            # 重试必须带着原来所有请求头。17:10 踩过一次：只重发 URL 会丢掉 Authorization，
            # 私有仓库于是回 404（GitHub 对无权访问的私有库就是装"不存在"），
            # 我差点把"鉴权头没带上"读成"仓库或分支没了"。
            retry = urllib.request.Request(req.full_url, data=req.data, method=req.get_method())
            for a, b in req.header_items():
                retry.add_header(a, b)
            req = retry
    raise RuntimeError("两条链路都失败: " + " | ".join(errs))
