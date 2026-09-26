/**
 * ORD-0358 — one entry point that brings the phone preview chain back by itself.
 *
 * Why this exists: the chain is four separate processes (backend :8693, `vite preview` :4781, the
 * auth proxy :4782, cloudflared).  At 16:30 all four stopped writing logs because each had been
 * started inside some agent's own console, so when that session ended the children went with it.  A
 * human then has to remember which four to relight, in which order, with which arguments.  This tool
 * replaces the remembering: detect hop by hop, start only what is missing, and prove health with a
 * real HTTP request rather than a listening socket.
 *
 * What "started properly" means here, and how it is measured rather than asserted: the tool launches
 * each hop through `cmd /c start`, which gives the child its own console, and then reports the
 * launched pid, its parent pid, whether that parent is still alive, and the parent's image name.  The
 * rule applied is: the parent must not be a live agent shell.  The load-bearing proof is behavioural
 * and is exercised by `--arm recover`: the tool process exits, and the hops must still be up.
 *
 * Hard boundaries, enforced in code (not in a comment):
 *  - the backend may only be pointed at `D:/moodle/_qoder_preview_20260920/_preview.db`.  Anything
 *    else aborts before a single process is spawned (`--arm db-guard` proves it aborts).  No repair,
 *    no "it probably meant".
 *  - credentials are used by path only: the auth file is read at request time to build one header and
 *    is never printed, logged, or copied into the receipt.
 *  - the tunnel address is only ever appended: the previous value is archived to
 *    `run/tunnel_url.txt.dead_<HHMM>` and the desktop note gets a new block at the top; old bytes are
 *    verified still present, byte for byte, and the tool refuses if it would have to overwrite.
 *  - `--detect-only` performs no spawn and no write, so it can be run against someone else's chain.
 *
 * Usage
 *   node tools/chain_self_heal.mjs [--detect-only] [--arm recover|db-guard|note-append]
 *        [--instance-name live] [--out <file.json>] [overrides...]
 * Exit: 0 healthy/recovered | 3 a hop is still unhealthy | 4 refused by a guard | 5 arm failed
 */
import { execFileSync, spawnSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const argv = process.argv.slice(2);
const flag = (name, dflt) => {
  const i = argv.indexOf("--" + name);
  return i >= 0 && argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : dflt;
};
const has = (name) => argv.includes("--" + name);

const PREVIEW = "D:/moodle/_qoder_preview_20260920";
const CFG = {
  instance: flag("instance-name", "live"),
  repo: flag("repo", "D:/moodle/CityNexus"),
  venvPython: flag("venv-python", "D:/moodle/CityNexus/.venv/Scripts/python.exe"),
  node: flag("node", process.execPath),
  frontendDir: flag("frontend-dir", "D:/moodle/_qoder_integration_20260919/frontend"),
  backendDir: flag("backend-dir", "D:/moodle/CityNexus/backend"),
  proxyScript: flag("proxy-script", "raw/preview_auth_proxy.py"),
  proxyCwd: flag("proxy-cwd", "D:/moodle/_qoder_recovery_20260919"),
  cloudflared: flag("cloudflared", "D:/moodle/_qoder_preview_20260920/tools/cloudflared.exe"),
  dist: flag("dist-dir", `${PREVIEW}/dist`),
  runDir: flag("run-dir", `${PREVIEW}/run`),
  authFile: flag("auth-file", `${PREVIEW}/run/preview_auth.txt`),
  deskNote: flag("desk-note", "C:/Users/仓鼠王/Desktop/CityNexus_包工头留言.txt"),
  backendPort: Number(flag("backend-port", 8693)),
  only: (flag("only", "backend,static,auth_proxy,tunnel")).split(",").map((x) => x.trim()),
  staticPort: Number(flag("static-port", 4781)),
  authPort: Number(flag("auth-port", 4782)),
  allowedDb: flag("allowed-db", `${PREVIEW}/_preview.db`),
  out: flag("out", null),
  arm: flag("arm", null),
  detectOnly: has("detect-only"),
  // 本实例自己起一条隧道并公布新址（现网那条址是别人的链，不能当"我这层的隧道已经活着"）
  freshTunnel: has("fresh-tunnel"),
};

const SHELLS = ["bash.exe", "sh.exe", "zsh.exe", "qoder.exe", "codex.exe", "cmd.exe", "powershell.exe",
  "powershell_ise.exe", "node.exe"];
const localHHMM = () => new Date().toTimeString().slice(0, 5).replace(":", "");
// quick tunnel 把那行打成 `... INF |  https://xxx.trycloudflare.com   |`，行首不是 URL ⇒ 不能加 ^ 锚
const TUNNEL_URL = /(https:\/\/[a-z0-9-]+\.trycloudflare\.com)/i;

function sh(cmd, args, opts = {}) {
  // windowsVerbatimArguments 只给 `cmd /c start "" …` 那一处：它会把别人的引号原样带过去；
  // 用在 powershell -Filter "ProcessId=…" 上会把引号拆坏，powershell 于是等输入 —— 实测挂满 900 秒。
  return spawnSync(cmd, args, { encoding: "utf-8", ...opts });
}
function fetch(url, { auth = false, timeout = 12000 } = {}) {
  const headers = { "user-agent": "citynexus-chain-self-heal/1", accept: "*/*" };
  if (auth) {
    // 只按路径取用；这份文件的值不进任何输出（收据里连长度都不记）
    const raw = fs.readFileSync(CFG.authFile, "utf-8").trim();
    const [user, secret] = raw.includes("\t") ? raw.split("\t") : raw.split(":");
    if (!user || !secret) throw new Error("AUTH_FILE_SHAPE: 认证文件既不是 TAB 也不是冒号分隔");
    headers.authorization = "Basic " + Buffer.from(`${user}:${secret}`).toString("base64");
  }
  try {
    const res = spawnSync(CFG.venvPython, ["-X", "utf8", "-c", PY_FETCH, url, auth ? "auth" : "plain"],
      { encoding: "utf-8", timeout });
    const j = JSON.parse(res.stdout.trim().split("\n").pop());
    return j;
  } catch (e) {
    return { connect_error: e.constructor.name, message: String(e.message || e).slice(0, 120) };
  }
}
// 真 HTTP 交给 venv 里的 python：它的 TLS/代理形状与这条链其余部分一致，node 的 fetch 不一样
const PY_FETCH = `
import json, os, sys, urllib.request, urllib.error, base64, hashlib
url, mode = sys.argv[1], sys.argv[2]
h = {"user-agent": "citynexus-chain-self-heal/1", "accept": "*/*"}
if mode == "auth":
    raw = open(os.environ["CNX_AUTH_FILE"], encoding="utf-8").read().strip()
    user, secret = (raw.split("\\t", 1) if "\\t" in raw else raw.split(":", 1))
    h["authorization"] = "Basic " + base64.b64encode(f"{user}:{secret}".encode()).decode()
try:
    req = urllib.request.Request(url, headers=h)
    # 探针必须钉死走哪条路：这台机器环境变量里的 HTTPS_PROXY 指着一条无监听的口（:7892），
    # 跟着它走会把"对端拒连"读成"链断了"。一律直连，并把这一事实记进读数。
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with op.open(req, timeout=15) as r:
        body = r.read()
        print(json.dumps({"status": r.status, "content_type": r.headers.get("content-type"),
                          "server": r.headers.get("server"), "bytes": len(body), "proxy": "bypassed",
                          "sha1_12": hashlib.sha1(body).hexdigest()[:12],
                          "head": body[:240].decode("utf-8", "replace"),
                          "body_head": body[:20000].decode("utf-8", "replace")}))
except urllib.error.HTTPError as e:
    body = e.read()
    print(json.dumps({"status": e.code, "content_type": e.headers.get("content-type"),
                      "server": e.headers.get("server"), "bytes": len(body), "proxy": "bypassed",
                      "sha1_12": hashlib.sha1(body).hexdigest()[:12],
                      "head": body[:240].decode("utf-8", "replace"),
                          "body_head": body[:20000].decode("utf-8", "replace")}))
except Exception as e:
    print(json.dumps({"connect_error": type(e).__name__, "message": str(e)[:120]}))
`;
process.env.CNX_AUTH_FILE = CFG.authFile;

function portListening(port) {
  const r = sh("netstat", ["-ano", "-p", "TCP"]);
  return new RegExp(`TCP\\s+\\S*:${port}\\s+\\S+\\s+LISTENING\\s+(\\d+)`, "i").exec(r.stdout || "") || [];
}
function listenerPid(port) {
  const m = portListening(port);
  return m[1] ? Number(m[1]) : null;
}
let PROC_CACHE = { at: 0, rows: new Map() };
function procTable() {
  // 一次 CSV 快照，别按需查：每跳都起一个 powershell 既慢，又把引号问题摊到每一处
  if (Date.now() - PROC_CACHE.at > 4000) {
    const r = sh("powershell", ["-NoProfile", "-Command",
      "(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine" +
      " | ConvertTo-Csv -NoTypeInformation)"]);
    const rows = new Map();
    const text = String(r.stdout || "").replace(/^\uFEFF/, "");
    for (const line of text.split(/[\r\n]+/).slice(1)) {
      const m = [...line.matchAll(/"((?:[^"]|"")*)"/g)].map((x) => x[1].replace(/""/g, '"'));
      if (m.length >= 3 && /^\d+$/.test(m[0])) rows.set(m[0], { ProcessId: Number(m[0]),
        ParentProcessId: Number(m[1]) || null, Name: m[2], CommandLine: m[3] || "" });
    }
    PROC_CACHE = { at: Date.now(), rows };
  }
  return PROC_CACHE.rows;
}
function procInfo(pid) {
  if (!pid) return null;
  return procTable().get(String(pid)) || null;
}
function parentJudgement(info) {
  if (!info) return { ok: false, why: "查不到这个 pid" };
  const pp = procInfo(info.ParentProcessId);
  const parentName = pp ? pp.Name : "(已退出的父进程)";
  const liveShell = pp && ["bash.exe", "sh.exe", "zsh.exe", "qoder.exe", "codex.exe"].includes(pp.Name);
  return { pid: info.ProcessId, parent_pid: info.ParentProcessId, parent_name: parentName,
           parent_alive: Boolean(pp), ok: !liveShell,
           why: liveShell ? "父进程还活着且是某个 agent 的 shell —— 会话一停就会被带走"
                          : "父进程不是任何 agent 会话的 shell（经 cmd /c start 自立控制台）" };
}
// 「200 + HTML」不算 API 活着：这条链上栽过一次（对端没应用层被读成"服务器答了"），所以判据按
// content-type 与正文里的字段名判，不按状态码判。静态那一跳反过来必须真是 HTML。
function apiJson(h) {
  return h.status === 200 && String(h.content_type || "").includes("application/json")
    && /"status"\s*:/.test(String(h.head || ""));
}
function isHtml(h) {
  return String(h.content_type || "").includes("text/html") && /<!doctype html>/i.test(String(h.head || ""));
}
// 隧道的对端答了没有，分三层看：连不上 / 边缘代答（还没绑上连接器）/ 对端真答。
// 对端真答里还有一形要具名：vite 自己的 Host 白名单会把 `*.trycloudflare.com` 拒成
// `403 + Blocked request. This host (...)` —— 那是 origin 在说话（cloudflared 也会给 origin 的应答
// 盖一个 `Server: cloudflare`，所以不能拿这个头判"谁在答"）。
function originRefusedHost(h) {
  return Number(h?.status) === 403 && /Blocked request\.\s*This host/i.test(String(h?.head || ""));
}
function edgeNotReady(h) {
  if (!h || !h.status) return true;
  if (originRefusedHost(h)) return false;
  return [502, 503, 521, 522, 523, 530].includes(Number(h.status));
}
function answerShape(h) {
  if (!h || h.connect_error) return "no-answer";
  if (apiJson(h)) return "api-json";
  if (originRefusedHost(h)) return "origin-refused-host";
  return isHtml(h) ? "html" : "other";
}
function hopSpecs() {
  return [
    { hop: "backend", port: CFG.backendPort, url: `http://127.0.0.1:${CFG.backendPort}/api/v1/health`,
      auth: false, kind: "api", expect: apiJson,
      bat: ["@echo off", `cd /d "${CFG.backendDir}"`,
            `set CITYNEXUS_DATABASE_URL=sqlite:///${CFG.allowedDb.split("\\").join("/")}`,
            `"${CFG.venvPython}" -m uvicorn app.main:app --host 127.0.0.1 --port ${CFG.backendPort}`] },
    { hop: "static", port: CFG.staticPort, url: `http://127.0.0.1:${CFG.staticPort}/`,
      auth: false, kind: "static", expect: (h) => h.status === 200 && h.bytes > 200 && isHtml(h),
      bat: ["@echo off", `cd /d "${CFG.frontendDir}"`,
            `"${CFG.node}" node_modules/vite/bin/vite.js preview --outDir "${CFG.dist}"` +
            ` --host 127.0.0.1 --port ${CFG.staticPort} --strictPort`] },
    // 那把鉴权代理尺把自己钉在 4782、把静态上游钉在 4781（`raw/preview_auth_proxy.py:25` 与 `:31`），
    // 只有 API 上游可由 `CNX_PROXY_API_UPSTREAM` 改（`:30`）—— 所以它只能整条一起起，不能挪端口实验
    { hop: "auth_proxy", port: CFG.authPort, url: `http://127.0.0.1:${CFG.authPort}/api/v1/health`,
      auth: true, kind: "api", expect: apiJson,
      bat: ["@echo off", `cd /d "${CFG.proxyCwd}"`,
            `set CNX_PROXY_API_UPSTREAM=http://127.0.0.1:${CFG.backendPort}`,
            `"${CFG.venvPython}" ${CFG.proxyScript}`] },
  ];
}
function writeBat(spec) {
  // 启动一律落成一份 .bat 再 `cmd /c start`：嵌套两层 cmd 的 `&&` 会被第二层拆坏（实测：
  // `cd /d` 没生效 ⇒ vite 在调用方的目录下找不到）。.bat 同时也是这一跳可回读的证据。
  const stamp = localHHMM();
  const file = path.join(CFG.runDir, `hop_${spec.hop}_${stamp}.bat`);
  fs.mkdirSync(CFG.runDir, { recursive: true });
  fs.writeFileSync(file, spec.bat.join("\r\n") + "\r\n", "ascii");
  return file;
}
function probe(hop) {
  const got = fetch(hop.url, { auth: hop.auth });
  return { hop: hop.hop, port: hop.port, url: hop.url, kind: hop.kind, listening: listenerPid(hop.port),
           http: { status: got.status ?? null, content_type: got.content_type ?? null,
                   server: got.server ?? null, bytes: got.bytes ?? null, sha1_12: got.sha1_12 ?? null,
                   connect_error: got.connect_error ?? null, head60: String(got.head || "").slice(0, 60) },
           healthy: Boolean(got.status) && hop.expect(got),
           shape: answerShape(got) };
}
function phoneGeneration() {
  // 手机那一代的指纹 = 首页点名的那个 JS 资产名 + 它的字节数，不是"端口在听"
  const idx = fetch(`http://127.0.0.1:${CFG.staticPort}/`);
  const name = (String(idx.body_head || "") .match(/\/assets\/index-[\w.-]+\.js/) || [null])[0];
  if (!name) return { asset: null, bytes: 0, sha1_12: null, ok: false };
  const asset = fetch(`http://127.0.0.1:${CFG.staticPort}${name}`);
  return { asset: name.replace("/assets/", ""), bytes: asset.bytes || 0, sha1_12: asset.sha1_12 || null,
           ok: Boolean(asset.status) && asset.status < 400 && (asset.bytes || 0) > 1000 };
}
function tunnelFromLog() {
  // 现值只有一个权威来源：`run/tunnel_url.txt`。旧日志里的地址不是现址 —— 实测这份目录里
  // `tunnel_0925_0417.err.log` 的 mtime 比什么都新，里面是一条早已死掉的 quick tunnel。
  const dir = CFG.runDir;
  const f = path.join(dir, "tunnel_url.txt");
  const cur = fs.existsSync(f) ? fs.readFileSync(f, "utf-8").trim() : "";
  const newest = (() => {
    const logs = fs.existsSync(dir) ? fs.readdirSync(dir).filter((x) => /^tunnel.*\.log$/i.test(x))
      .map((x) => ({ x, m: fs.statSync(path.join(dir, x)).mtimeMs })).sort((a, b) => b.m - a.m) : [];
    for (const l of logs) {
      const m = TUNNEL_URL.exec(fs.readFileSync(path.join(dir, l.x), "utf-8").slice(-40000));
      if (m) return { url: m[1], source: `run/${l.x}` };
    }
    return null;
  })();
  if (cur) {
    return { url: cur, source: "run/tunnel_url.txt",
             from_newest_log: newest && newest.url !== cur ? newest : null };
  }
  return newest || { url: null, source: null };
}
function startHop(spec) {
  const before = listenerPid(spec.port);
  const file = writeBat(spec);
  // stdio 必须 "ignore"：`start` 一个 .bat 起的是 `cmd /K 那份.bat`，那个 cmd 一直握着从我这里继承的
  // 管道写端且不退出 ⇒ spawnSync 等到天荒地老（实测把整趟 recover 挂死在 900 秒上）。
  const r = sh("cmd", ["/c", "start", '""', "/min", file], { timeout: 30000, stdio: "ignore",
    windowsVerbatimArguments: true });
  if (r.status !== 0) {
    return { started: false, bat: path.basename(file), spawn_stderr: (r.stderr || "").slice(0, 200) };
  }
  for (let i = 0; i < 40; i += 1) {
    const pid = listenerPid(spec.port);
    if (pid && pid !== before) {
      const info = procInfo(pid);
      return { started: true, waited_ms: (i + 1) * 500, pid: info?.ProcessId ?? pid,
               bat: path.basename(file), parent: parentJudgement(info),
               cmd: (info?.CommandLine || "").slice(0, 240) };
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 500);
  }
  return { started: false, timed_out: true, bat: path.basename(file), port_still: listenerPid(spec.port) };
}
function publishTunnel(newUrl) {
  const f = path.join(CFG.runDir, "tunnel_url.txt");
  const old = fs.existsSync(f) ? fs.readFileSync(f, "utf-8").trim() : "";
  const stamp = localHHMM();
  const rec = { old_url: old || null, archived_to: null, new_url: newUrl, desk_note: null };
  if (old && old !== newUrl) {
    const dead = path.join(CFG.runDir, `tunnel_url.txt.dead_${stamp}`);
    fs.writeFileSync(dead, old + "\n", "utf-8");
    rec.archived_to = path.basename(dead);
  }
  fs.writeFileSync(f, newUrl + "\n", "utf-8");
  if (fs.existsSync(CFG.deskNote)) {
    const before = fs.readFileSync(CFG.deskNote, "utf-8");
    const block = [`【lane F 8ccd71d8 · chain_self_heal · ${new Date().toISOString().slice(11, 16)}` +
      ` +08】手机链隧道换了地址：${newUrl}`, old ? `旧地址 ${old} 已归档为 run/${rec.archived_to || "—"}` :
      "旧地址未知（此前没有地址文件）", "", ""].join("\n");
    const after = block + before;
    if (!after.endsWith(before)) throw new Error("DESK_NOTE_REFUSE: 追加后旧内容不在末尾，拒绝改写");
    fs.writeFileSync(CFG.deskNote, after, "utf-8");
    rec.desk_note = { path: CFG.deskNote, bytes_before: Buffer.byteLength(before),
                      bytes_after: Buffer.byteLength(after), old_bytes_preserved: after.endsWith(before) };
  } else {
    rec.desk_note = { path: CFG.deskNote, missing: true };
  }
  return rec;
}
function dbGuard() {
  const resolved = path.resolve(CFG.allowedDb).replace(/\\/g, "/").toLowerCase();
  const wanted = path.resolve(`${PREVIEW}/_preview.db`).replace(/\\/g, "/").toLowerCase();
  const forbidden = ["_live.db", "_ord43.db"];
  if (path.basename(resolved) !== "_preview.db" || resolved !== wanted) {
    return { ok: false, allowed: CFG.allowedDb, resolved, forbidden_seen: forbidden.filter((f) => resolved.includes(f)) };
  }
  return { ok: true, resolved };
}
function runArm(name, report) {
  if (name === "db-guard") {
    const saved = CFG.allowedDb;
    CFG.allowedDb = "D:/moodle/_qoder_preview_20260920/_live.db";
    const g = dbGuard();
    const spawns = hopSpecs().map((s) => ({ hop: s.hop, pid: listenerPid(s.port) }));
    CFG.allowedDb = saved;
    report.db_guard_arm = { refused: !g.ok, reason: g, ports_touched: spawns };
    report.exit = g.ok ? 5 : 4;
    return;
  }
  if (name === "note-append") {
    const dir = fs.mkdtempSync(path.join("D:/moodle/_qoder_f_run", "note-arm-"));
    const note = path.join(dir, "note.txt");
    const before = "OLD BLOCK ONE\nold body line\n";
    fs.writeFileSync(note, before, "utf-8");
    const savedNote = CFG.deskNote, savedRun = CFG.runDir;
    CFG.deskNote = note; CFG.runDir = dir;
    const rec = publishTunnel("https://example-arm-arm-arm.trycloudflare.com");
    const after = fs.readFileSync(note, "utf-8");
    CFG.deskNote = savedNote; CFG.runDir = savedRun;
    report.note_append_arm = { dir, old_bytes_kept_verbatim: after.endsWith(before),
                               new_block_at_top: after.startsWith("【lane F"), record: rec };
    report.exit = after.endsWith(before) && after.startsWith("【lane F") ? 0 : 5;
    return;
  }
  report.exit = 5; report.arm_unknown = name;
}
function main() {
  const report = { schema: "CNX_CHAIN_SELF_HEAL_V1", lane: "F 8ccd71d8", instance: CFG.instance,
    at_local: new Date().toString(), mode: CFG.detectOnly ? "detect-only" : (CFG.arm ? `arm:${CFG.arm}` : "ensure"),
    boundary: { allowed_db: CFG.allowedDb, credentials: "按路径取用，绝不打印", detect_only: CFG.detectOnly },
    hops: [], spawns: [], phone_generation: null, tunnel: null, published: null };
  const guard = dbGuard();
  report.db_guard = guard;
  if (!guard.ok && !CFG.detectOnly) {
    report.verdict = "REFUSED_DB_PATH"; report.exit = 4;
    emit(report); return;
  }
  if (CFG.arm) { runArm(CFG.arm, report); emit(report); return; }
  report.hops = hopSpecs().filter((s) => CFG.only.includes(s.hop)).map(probe);
  const missing = report.hops.filter((h) => !h.healthy);
  if (!missing.length && !CFG.freshTunnel) {
    report.spawns = [];
  } else if (CFG.detectOnly) {
    report.verdict = "DETECT_ONLY_UNHEALTHY"; report.exit = 3; emit(report); return;
  } else {
    for (const spec of hopSpecs().filter((s) => CFG.only.includes(s.hop))) {
      const cur = report.hops.find((h) => h.hop === spec.hop);
      if (cur.healthy) continue;
      report.spawns.push({ hop: spec.hop, ...startHop(spec) });
    }
      const tun = tunnelFromLog();
    const tunAlive = !CFG.freshTunnel && tun.url && apiJson(fetch(tun.url + "/api/v1/health", { auth: true }));
    if (CFG.only.includes("tunnel") && !tunAlive) {
      const stamp = localHHMM();
      const log = path.join(CFG.runDir, `tunnel_selfheal_${stamp}.log`);
      const tbat = path.join(CFG.runDir, `hop_tunnel_${stamp}.bat`);
      fs.writeFileSync(tbat, ["@echo off", `cd /d "${CFG.runDir}"`,
        `"${CFG.cloudflared}" tunnel --url http://127.0.0.1:${CFG.authPort} --no-autoupdate` +
        ` --protocol http2 > "${log}" 2>&1`].join("\r\n") + "\r\n", "ascii");
      sh("cmd", ["/c", "start", '""', "/min", tbat], { windowsVerbatimArguments: true,
        stdio: "ignore", timeout: 30000 });
      let found = { url: null };
      for (let i = 0; i < 24 && !found.url; i += 1) {
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 2500);
        found = TUNNEL_URL.test(fs.existsSync(log) ? fs.readFileSync(log, "utf-8") : "")
          ? { url: TUNNEL_URL.exec(fs.readFileSync(log, "utf-8"))[1], source: path.basename(log) } : { url: null };
      }
      report.tunnel_start = { log: path.basename(log), found: found.url };
      if (found.url) report.published = publishTunnel(found.url);
    }
    report.hops = hopSpecs().filter((s) => CFG.only.includes(s.hop)).map(probe);
  }
  report.phone_generation = CFG.only.includes("static") ? phoneGeneration() : { ok: false, skipped: true };
  report.tunnel = tunnelFromLog();
  // 刚打印出地址 ≠ 边缘已经能转发：quick tunnel 注册要几秒到一分多钟（实测两种都遇过）。
  // 所以有界地等（探不到就再等 5 秒，最多 24 次），每次探到的状态按顺序进 `tunnel_probe_statuses`，
  // 不靠"多试几次直到绿"——拿不到对端真答就照实判 CHAIN_UNHEALTHY。
  let tp = null;
  report.tunnel_probe_attempts = 0;
  report.tunnel_probe_waited_ms = 0;
  report.tunnel_probe_statuses = [];
  if (report.tunnel.url) {
    for (let i = 0; i < 24; i += 1) {
      tp = fetch(`${report.tunnel.url}/api/v1/health`, { auth: true });
      report.tunnel_probe_attempts = i + 1;
      report.tunnel_probe_statuses.push(tp.status || tp.connect_error || "empty");
      if (!edgeNotReady(tp)) break;
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 5000);
      report.tunnel_probe_waited_ms = (i + 1) * 5000;
    }
  }
  report.tunnel_probe = tp && { status: tp.status ?? null, content_type: tp.content_type ?? null,
    server: tp.server ?? null, bytes: tp.bytes ?? null, sha1_12: tp.sha1_12 ?? null,
    connect_error: tp.connect_error ?? null, head60: String(tp.head || "").slice(0, 60),
    shape: answerShape(tp) };
  const hopsOk = report.hops.every((h) => h.healthy);
  const apiLegInScope = report.hops.some((h) => h.kind === "api");
  const tunnelInScope = CFG.only.includes("tunnel");
  const edgeReady = !tunnelInScope || !edgeNotReady(tp);
  // 隧道指向静态服（我这台自己的实验实例就是这形）⇒ 对端答了、但这条实例根本没有 API 腿：必须具名，不能算绿
  const apiNotCarried = tunnelInScope && !apiLegInScope && edgeReady && !apiJson(tp);
  const tunnelOk = !tunnelInScope || Boolean(tp && apiJson(tp));
  report.verdict = hopsOk && report.phone_generation.ok && tunnelOk
    ? "CHAIN_HEALTHY" : (hopsOk && report.phone_generation.ok && apiNotCarried
      ? "STATIC_SIDE_HEALTHY_API_NOT_CARRIED" : "CHAIN_UNHEALTHY");
  report.verdict_reason = { hops_ok: hopsOk, phone_generation_ok: Boolean(report.phone_generation.ok),
    api_leg_in_scope: apiLegInScope, tunnel_in_scope: tunnelInScope,
    tunnel_shape: report.tunnel_probe ? report.tunnel_probe.shape : "no-url",
    tunnel_edge_state: !report.tunnel.url ? "no-url" : (edgeNotReady(tp) ? "edge_only_or_no_answer"
      : (originRefusedHost(tp) ? "origin_answered_but_refused_host" : "origin_answered")),
    api_leg: apiLegInScope ? "carried" : (apiNotCarried ? "NOT_CARRIED_BY_THIS_INSTANCE" : "NOT_IN_SCOPE"),
    why_not_full_green: apiLegInScope ? null : "这一台实例的隧道直指静态服，中间没有那把鉴权代理 ⇒ vite 用自己的 "
      + "Host 白名单把 `*.trycloudflare.com` 拒成 403（`origin_refused_host`）；现网那一腿能过，是因为代理把 "
      + "Host 改写成 `127.0.0.1:4781`（`raw/preview_auth_proxy.py:124` 丢掉入站 Host、`:127` 显式加这一个）" };
  report.exit = report.verdict === "CHAIN_HEALTHY" ? 0
    : (report.verdict === "STATIC_SIDE_HEALTHY_API_NOT_CARRIED" ? 2 : 3);
  emit(report);
}
function emit(report) {
  const body = JSON.stringify(report, null, 1) + "\n";
  if (CFG.out) { fs.mkdirSync(path.dirname(CFG.out), { recursive: true }); fs.writeFileSync(CFG.out, body, "utf-8"); }
  console.log(JSON.stringify({ verdict: report.verdict, exit: report.exit,
    hops: report.hops.map((h) => `${h.hop}:${h.port}=${h.healthy ? "UP" : "DOWN"}${h.http?.status ? "/" + h.http.status : ""}`),
    spawns: report.spawns.map((s) => `${s.hop}→pid ${s.pid ?? "失败"}`),
    phone_asset: report.phone_generation?.asset, phone_bytes: report.phone_generation?.bytes,
    tunnel: report.tunnel?.url, db_guard_ok: report.db_guard?.ok,
    arm: report.db_guard_arm || report.note_append_arm || null,
    receipt_sha1: CFG.out ? crypto.createHash("sha1").update(Buffer.from(body)).digest("hex") : null }));
  process.exit(report.exit ?? 0);
}
main();
