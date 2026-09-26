/**
 * ORD-0332 的前端两向读数件（③ 要件那"一枚"）。
 *
 * 为什么不用浏览器、也不碰 :8000：这枚件判的是"屏幕拿到什么才许说它是编号"，那是纯函数层的事；
 * 手机链那条路按裁是不提供的，把判据建在活后端上等于把单子建在拿不到的东西上。
 *
 * 三件必做的事：
 *  1. 用仓库自带那把 TypeScript 把真源文件转译后**在 node 里跑**，不是我照抄一遍逻辑；
 *  2. 另一头用同一个解释器经真 ASGI 栈取**服务器真发的那一枚号**与 `contracts/openapi.yaml` 的 pattern，
 *     两边互验（前端形状收下服务器那枚；TS 正则与契约 pattern 逐字相等）；
 *  3. 双向自测：坏形状（`code`、空串、uuid、截断大写人话）必须全部 `NOT-EMITTED`；再把正则**故意放松**
 *     重跑一次，那一枚 counterfeit 必须变成"被收下"，否则说明拒它的是我这句话的写法，不是那道形状检查。
 *
 * 用法：node frontend/tools/ord0332_receipt_readings.mjs --out <file> [--tslib <dir>] [--python <exe>]
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND = path.resolve(HERE, "..");
const TREE = path.resolve(FRONTEND, "..");
const arg = (name, dflt) => {
  const i = process.argv.indexOf("--" + name);
  return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : dflt;
};
const TSLIB = arg("tslib", "D:/moodle/CityNexus/frontend/node_modules/typescript");
const PY = arg("python", "D:/moodle/CityNexus/.venv/Scripts/python.exe");
const OUT = arg("out", path.join(TREE, "ord0332_receipt_readings_r1.json"));
const SRC = path.join(FRONTEND, "src/lib/errorReceipt.ts");

const require = createRequire(import.meta.url);
const TS_ENTRY = path.join(TSLIB, "lib", "typescript.js");
if (!fs.existsSync(TS_ENTRY)) throw new Error(`没有那把 TypeScript：${TS_ENTRY}（用 --tslib 指过去）`);
const ts = require(TS_ENTRY);

function loadModule(relaxShape) {
  let src = fs.readFileSync(SRC, "utf-8");
  if (relaxShape) {
    // 只动这一处：把形状检查放成"什么收"，用来证明那把尺有牙
    const before = src;
    src = src.replace(/const RECEIPT_SHAPE = [^\n]+/, "const RECEIPT_SHAPE = /.*/;");
    if (src === before) throw new Error("放松失败：源里找不到那行正则");
  }
  src = src.replace(/export const/g, "const").replace(/export function/g, "function")
    + "\nreturn { RECEIPT_FIELD, RECEIPT_SHAPE, RECEIPT_MISSING, readErrorReceipt, receiptLabel };\n";
  const js = ts.transpileModule(src, {
    compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS },
  }).outputText;
  return new Function("exports", "require", "module", js)(
    {}, require, { exports: {} });
}

const mod = loadModule(false);
const FIELD = mod.RECEIPT_FIELD;
const MISSING = mod.RECEIPT_MISSING;

// —— 服务器那一侧：真 ASGI 一发 422 的正文 + 契约 pattern + 无上下文那一形
const PY_SNIPPET = `
import json, re, sys
import yaml
sys.path.insert(0, r"${TREE.replace(/\\/g, "/")}/backend")
from fastapi.testclient import TestClient
from app.main import app, error
from app.db.session import ensure_schema
from sqlalchemy import select, func
from app.db.models import Journey
from app.db.session import SessionLocal
from app.services import seed_demo
ensure_schema()
with SessionLocal() as s:
    if not s.scalar(select(func.count()).select_from(Journey)):
        seed_demo(s)
    jid = str(s.scalars(select(Journey.id)).first())
client = TestClient(app, raise_server_exceptions=False)
r = client.post("/api/v1/journeys/" + jid + "/outcomes", json={"event_type": "NOT_A_TYPE"})
env = r.json()["error"]
spec = yaml.safe_load(open(r"${(path.join(TREE, "contracts", "openapi.yaml")).replace(/\\/g, "/")}", encoding="utf-8"))
pattern = spec["components"]["schemas"]["ErrorEnvelope"]["properties"]["error"]["properties"]["error_receipt_id"]["pattern"]
noctx = json.loads(error("ORD0332_NO_CONTEXT", "x", status=503).body)["error"]
print(json.dumps({"status": r.status_code, "receipt": env.get("error_receipt_id"),
                  "trace_id": env.get("trace_id"), "pattern": pattern,
                  "noctx_has_key": "error_receipt_id" in noctx}))
`;
const server = JSON.parse(execFileSync(PY, ["-X", "utf8", "-c", PY_SNIPPET], {
  cwd: path.join(TREE, "backend"), encoding: "utf-8", timeout: 600000, maxBuffer: 32 * 1024 * 1024,
}));

const COUNTERFEIT = [
  ["absent-key", {}],
  ["empty", { [FIELD]: "" }],
  ["whitespace", { [FIELD]: "   " }],
  ["a code", { [FIELD]: "SERVER_BUSY" }],
  ["a uuid (that is trace_id's job)", { [FIELD]: server.trace_id }],
  ["truncated uppercase prose", { [FIELD]: "NETWORK WRITE FAILED BECAUS" }],
  ["nested error absent", { error: { code: "X", message: "TypeError: Failed to fetch" } }],
];
const SENTINEL = "TypeError: Failed to fetch at Object.<anonymous>";
const views = COUNTERFEIT.map(([name, payload]) => [name, mod.readErrorReceipt(payload)]);
const accepted = views.filter(([, v]) => v.present).map(([name]) => name);

// —— Q71：异常原文不得进 data-*；把所有形状下会写进 attrs 的值全数出来验
const attrValues = [];
for (const [, v] of views) attrValues.push(...Object.values(v.attrs));
attrValues.push(...Object.values(mod.readErrorReceipt({ [FIELD]: server.receipt }).attrs));
const leak = attrValues.filter((v) => /fetch|TypeError|at Object/.test(v));
const anchorOk = views.every(([, v]) => v.attrs["data-cnx-field"] === FIELD);

// —— 放松正则后，同一批 counterfeit 必须被收下（证明拒它的是形状检查）
const loose = loadModule(true);
const looseAccepted = COUNTERFEIT.filter(([, p]) => loose.readErrorReceipt(p).present).length;

const rows = views.map(([name, v]) => ({ input: name, present: v.present, text: v.text, observed: v.observed }));
const selftest = (
  typeof server.receipt === "string" && mod.RECEIPT_SHAPE.test(server.receipt)
  && mod.RECEIPT_SHAPE.source === server.pattern
  && accepted.length === 0 && views.length === COUNTERFEIT.length
  && server.noctx_has_key === false && leak.length === 0 && anchorOk
  && looseAccepted >= 3
) ? "SELFTEST_PASS" : "SELFTEST_FAIL";

const report = {
  schema: "CNX_ORD0332_FRONTEND_RECEIPT_READINGS_V1", lane: "F 8ccd71d8",
  source_file: path.relative(TREE, SRC).replace(/\\/g, "/"),
  source_bytes: fs.statSync(SRC).size,
  toolchain: { typescript: ts.version, tslib_path: TSLIB, node: process.version, python: PY },
  field_name: FIELD, missing_token: MISSING, receipt_shape_source: String(mod.RECEIPT_SHAPE),
  contract_pattern: server.pattern,
  server_side: { http_status: server.status, receipt: server.receipt, trace_id: server.trace_id,
                 no_context_key_present: server.noctx_has_key,
                 how: "同一棵导出树里 TestClient 走真 ASGI 一发 422（不依赖 :8000）" },
  shapes: rows,
  counterfeit_accepted_by_strict_shape: accepted,
  counterfeit_accepted_after_relaxing: looseAccepted,
  q71_attribute_leaks: leak, q70_anchor_present_on_every_view: anchorOk,
  counts: { shapes_tested: rows.length, rejected: rows.length - accepted.length,
            attrs_inspected: attrValues.length },
  selftest,
  claimed_result: selftest === "SELFTEST_PASS"
    ? `服务器那枚号被收下、${rows.length} 形 counterfeit 全部 ${MISSING}；放松正则后 ${looseAccepted} 形反而被收 ⇒ 形状检查有牙`
    : "自测未过：见上面各栏",
  derived_result: null,
};
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(report, null, 1) + "\n", "utf-8");
console.log(selftest, "| 服务器号", server.receipt, "| counterfeit 收进", accepted.length, "/", rows.length,
  "| 放松后被收", looseAccepted, "| 泄漏", leak.length, "| 件", OUT);
