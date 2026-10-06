"""ORD-0326 attachment: field-arrival table for the two landed agent paths.

Scope is the three POST legs those two components actually call:
  POST /api/v1/journeys/{id}/copilot/messages
  POST /api/v1/journeys/{id}/agent/hermes/runs/{runId}/stop
  POST /api/v1/journeys/{id}/agent/approvals/{approvalId}/approve

Every `path:line` citation below is checked against the tip export by reading that
line from disk and requiring the named substring; a line that moved or does not
contain the text aborts the run.  Counts are computed from the tree in the same
process, never written as literals here.

Usage:
  python -X utf8 _ord0326_fields_r2.py --export <dir> --out <file>
  python -X utf8 _ord0326_fields_r2.py --export <dir> --selftest
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = "D:/moodle/CityNexus"
TIP = "5d7335721106c20092dd4d90181bb99accd0a32b"

# The two files ORD-0326 landed, blob-pinned by the commander's landing receipt.
BLOBS = {
    "frontend/src/features/agent/AgentComposer.tsx":
        "3a0d06533a416b4a6c4390cf0e411092038131b4",
    "frontend/src/features/agent/CopilotDock.tsx":
        "3a73aa9e4c2e9fa220d6ff09d1a9ba1c05bbc355",
}

MAIN = "backend/app/main.py"
API = "frontend/src/api/citynexus.ts"
ATTR = "frontend/src/lib/failureAttribution.ts"
WD = "backend/app/db/write_deadline.py"
RW = "frontend/src/lib/readDeadline.ts"
WW = "frontend/src/lib/writeDeadline.ts"
AC = "frontend/src/features/agent/AgentComposer.tsx"
CD = "frontend/src/features/agent/CopilotDock.tsx"

# layer: server | transport | client_read | attribution | dom
CITES: list[dict[str, str]] = [
    # ---------------- http_status ----------------
    dict(field="http_status", layer="server", path=MAIN, line=496,
         must="JSONResponse(status_code=status",
         note="the refusal's status is the transport status of the one envelope; "
              "no route in this scope sets status_code, so a success answers 200"),
    dict(field="http_status", layer="client_read", path=API, line=681,
         must="response.status",
         note="requestJsonInner throws CityNexusApiError carrying it"),
    dict(field="http_status", layer="client_read", path=API, line=689,
         must="response.status",
         note="OriginResponseUnusableError carries it for a 2xx whose body is unusable"),
    dict(field="http_status", layer="attribution", path=ATTR, line=151,
         must='server?.status ?? (error instanceof Error && "status" in error',
         note="the only read site that turns a thrown error back into a status"),
    dict(field="http_status", layer="attribution", path=ATTR, line=57,
         must="http_status: number | null",
         note="Attribution key"),
    dict(field="http_status", layer="attribution", path=ATTR, line=133,
         must="`http_status=${http_status ?? \"none\"}`",
         note="telemetry token"),
    dict(field="http_status", layer="dom", path=ATTR, line=365,
         must="HTTP ${attribution.http_status}",
         note="zh SERVER_ERROR body arm -- reachable from all three legs"),
    dict(field="http_status", layer="dom", path=ATTR, line=422,
         must="HTTP ${attribution.http_status}",
         note="zh FORBIDDEN body arm"),
    dict(field="http_status", layer="dom", path=AC, line=193,
         must="data-attribution={failureFacts ?? \"\"}",
         note="render sink, AgentComposer"),
    dict(field="http_status", layer="dom", path=CD, line=785,
         must="data-attribution={sendFacts ?? \"\"}",
         note="render sink, CopilotDock send"),
    dict(field="http_status", layer="dom", path=CD, line=459,
         must="data-attribution={actionFacts ?? \"\"}",
         note="render sink, CopilotDock stop/approve"),

    # ---------------- content_type ----------------
    dict(field="content_type", layer="server", path=MAIN, line=496,
         must="JSONResponse(status_code=status",
         note="the refusal body's media type is whatever this response class sends -- "
              "`content_type` as a *name* has 0 hits under backend/app/ (see census)"),
    dict(field="content_type", layer="client_read", path=API, line=687,
         must='response.headers.get("content-type")',
         note="inside the parseFailed/empty guard only -- a non-2xx throws at :680 first"),
    dict(field="content_type", layer="attribution", path=ATTR, line=91,
         must="readonly content_type: string | null",
         note="OriginResponseUnusableError"),
    dict(field="content_type", layer="attribution", path=ATTR, line=160,
         must="error.content_type ?? `empty ${error.body_kind} body`",
         note="the one classify branch that can fill it"),
    dict(field="content_type", layer="dom", path=ATTR, line=378,
         must="Content-Type: ${attribution.content_type",
         note="zh ORIGIN_INVALID_RESPONSE body arm"),

    # ---------------- body_bytes ----------------
    dict(field="body_bytes", layer="client_read", path=API, line=663,
         must="await response.text()",
         note="the bytes are read as text and the length is never kept"),

    # ---------------- response_received ----------------
    dict(field="response_received", layer="attribution", path=ATTR, line=42,
         must='export type EvidenceKind = "HTTP_RESPONSE" | "TRANSPORT" | "HEALTH_PROBE"',
         note="the fact exists under this name, not as a boolean field"),
    dict(field="response_received", layer="attribution", path=ATTR, line=132,
         must="`evidence_kind=${evidence_kind}`",
         note="telemetry token"),

    # ---------------- elapsed_ms ----------------
    dict(field="elapsed_ms", layer="server", path=WD, line=164,
         must='"elapsed_ms": self.elapsed_ms',
         note="WriteDeadlineExceeded.details() -- the only allowed field a body carries here"),
    dict(field="elapsed_ms", layer="server", path=MAIN, line=618,
         must="status=503, details=exc.details()",
         note="the 503 handler puts those details into the envelope"),
    dict(field="elapsed_ms", layer="server", path=MAIN, line=634,
         must="arm_request_budget(SCENARIO_DEFAULT_WRITE)",
         note="the http middleware arms a write clock for every request, so a POST in this "
              "scope can reach that 503"),
    dict(field="elapsed_ms", layer="server", path=MAIN, line=492,
         must='"details": details',
         note="where it sits in the body: error.details.elapsed_ms"),
    dict(field="elapsed_ms", layer="client_read", path=AC, line=103,
         must="classifyReadFailure(cause)",
         note="one argument, no `server` -- so error.body (and its details) is never read"),
    dict(field="elapsed_ms", layer="client_read", path=CD, line=348,
         must="classifyReadFailure(cause)",
         note="stop leg, same shape"),
    dict(field="elapsed_ms", layer="client_read", path=CD, line=368,
         must="classifyReadFailure(cause)",
         note="approve leg, same shape"),
    dict(field="elapsed_ms", layer="client_read", path=CD, line=628,
         must="classifyReadFailure(cause)",
         note="send leg, same shape"),

    # ---------------- request_id ----------------
    dict(field="request_id", layer="server", path=MAIN, line=491,
         must='"trace_id": trace_id()',
         note="what a refusal actually carries in place of a request id"),
    dict(field="request_id", layer="server", path=MAIN, line=460,
         must="def trace_id() -> str:",
         note="a uuid4 minted per response, not a caller-replayable id"),
    dict(field="request_id", layer="server", path="backend/app/schemas.py", line=130,
         must="request_id: str = Field(min_length=8, max_length=128)",
         note="inbound only, on AgentToolCall (:128 extra=forbid)"),
    dict(field="request_id", layer="client_read", path=API, line=558,
         must="request_id?: string",
         note="AgentToolResponse type -- this backend never fills it on these legs"),
    dict(field="request_id", layer="client_read", path=API, line=1089,
         must="request_id: string;",
         note="the caller-supplied id on callAgentTool, i.e. a request field"),

    # ---------------- deadline reachability (why elapsed can never be client-side) ----------
    dict(field="__reach__", layer="transport", path=RW, line=51,
         must="return fetchWithWriteDeadline(input, init)",
         note="a non-GET leaves the read wrapper, so ReadDeadlineMissed cannot fire here"),
    dict(field="__reach__", layer="transport", path=WW, line=128,
         must="return fetch(input, init)",
         note="keyless writes pass through unbounded -- none of these three legs sends a key"),
    dict(field="__reach__", layer="transport", path=API, line=909,
         must='method: "POST",',
         note="sendCopilotMessage"),
    dict(field="__reach__", layer="transport", path=API, line=945,
         must='{ method: "POST" }',
         note="stopNativeHermesRun"),
    dict(field="__reach__", layer="transport", path=API, line=1113,
         must='method: "POST",',
         note="approveAgentAction"),
    dict(field="__reach__", layer="server", path=MAIN, line=11090,
         must='@app.post("/api/v1/journeys/{journey_id}/copilot/messages")',
         note="the route is plural `messages`"),
    dict(field="__reach__", layer="server", path=MAIN, line=1076,
         must="/agent/hermes/runs/{run_id}/stop",
         note="stop handler"),
    dict(field="__reach__", layer="server", path=MAIN, line=1861,
         must="/agent/approvals/{approval_id}/approve",
         note="approve handler"),
    dict(field="__reach__", layer="server", path=MAIN, line=10664,
         must="return fallback",
         note="an AI failure on the copilot path is swallowed into the deterministic "
              "fallback, so the answer is a 200 with nothing to attribute"),
]

# (field, layer, line) of the citation the killer arm reads one frame too low.
KILLER = ("http_status", "attribution", 133)

VERDICTS = {
    "http_status": "EMITTED_AND_ON_SCREEN",
    "content_type": "EMITTED_BY_FRAMEWORK_READ_IN_ONE_STATE_ONLY",
    "body_bytes": "NOT-EMITTED",
    "response_received": "NOT-EMITTED-BY-THAT-NAME",
    "elapsed_ms": "SERVER_EMITTS_CLIENT_DROPS",
    "request_id": "NOT-EMITTED",
}

KEYS = {
    "http_status": {
        "wire": "HTTP status line (no body key)",
        "client": "CityNexusApiError.status / OriginResponseUnusableError.status",
        "attribution": "http_status",
        "dom": "interpolated inside copyFor body + data-attribution=\"http_status=<n>\"",
    },
    "content_type": {
        "wire": "response header content-type",
        "client": "local at api/citynexus.ts:687, then the error's content_type",
        "attribution": "content_type (optional key)",
        "dom": "copyFor ORIGIN_INVALID_RESPONSE arms",
    },
    "body_bytes": {
        "wire": "content-length header, framework-level, not named in backend/app",
        "client": "absent",
        "attribution": "absent",
        "dom": "absent",
    },
    "response_received": {
        "wire": "n/a",
        "client": "absent",
        "attribution": "evidence_kind (HTTP_RESPONSE | TRANSPORT | HEALTH_PROBE)",
        "dom": "telemetry token evidence_kind=",
    },
    "elapsed_ms": {
        "wire": "error.details.elapsed_ms (503 SERVER_WRITE_DEADLINE_EXCEEDED only)",
        "client": "absent -- body never read on these legs",
        "attribution": "absent",
        "dom": "absent",
    },
    "request_id": {
        "wire": "absent; error.trace_id is what a refusal carries",
        "client": "type-only (AgentToolResponse.request_id?)",
        "attribution": "absent (server_code is the nearest slot, unfilled here)",
        "dom": "absent",
    },
}


def sha1_blob(path: Path) -> str:
    raw = b"blob %d\x00" % path.stat().st_size + path.read_bytes()
    return hashlib.sha1(raw).hexdigest()


def line_of(export: Path, rel: str, n: int) -> str:
    lines = (export / rel).read_text(encoding="utf-8").splitlines()
    if not 1 <= n <= len(lines):
        raise SystemExit(f"ABORT cite out of range {rel}:{n} (file has {len(lines)} lines)")
    return lines[n - 1]


def count_lines(export: Path, rel: str) -> int:
    return len((export / rel).read_text(encoding="utf-8").splitlines())


def grep_count(export: Path, needle: str, root: str, globs: list[str]) -> int:
    cmd = ["grep", "-rn", needle, root]
    for g in globs:
        cmd += ["--include", g]
    r = subprocess.run(cmd, cwd=export, capture_output=True, text=True, encoding="utf-8")
    return len([ln for ln in r.stdout.splitlines() if ln.strip()])


def grep_hits(export: Path, needle: str, rel: str) -> list[int]:
    out = []
    for i, ln in enumerate((export / rel).read_text(encoding="utf-8").splitlines(), 1):
        if needle in ln:
            out.append(i)
    return out


def build(export: Path, bad: bool = False) -> dict:
    for rel, want in BLOBS.items():
        got = sha1_blob(export / rel)
        if got != want:
            raise SystemExit(f"ABORT blob mismatch {rel}: export {got} != tip {want}")

    cites = []
    for spec in CITES:
        rel = spec["path"]
        want_line = spec["line"]
        if bad and (spec["field"], spec["layer"], spec["line"]) == KILLER:
            # Killer: read the telemetry line one frame too low.  The next line really exists,
            # so this only aborts if the check is a per-line substring check and not a
            # "does this string appear somewhere in the file" check.
            want_line += 1
        text = line_of(export, rel, want_line)
        if spec["must"] not in text:
            raise SystemExit(
                f"ABORT cite {rel}:{want_line} does not contain {spec['must']!r}\n"
                f"      actual: {text.strip()[:160]}"
            )
        cites.append(dict(
            field=spec["field"], layer=spec["layer"], path=rel, line=want_line,
            text=text.strip(), checked_substring=spec["must"], note=spec["note"],
        ))

    fields = {}
    for f, verdict in VERDICTS.items():
        mine = [c for c in cites if c["field"] == f]
        fields[f] = dict(
            verdict=verdict,
            keys=KEYS[f],
            layer_count=len({c["layer"] for c in mine}),
            cite_count=len(mine),
            cites=mine,
        )

    reach = [c for c in cites if c["field"] == "__reach__"]
    now = datetime.now(timezone.utc)
    return {
        "schema": "CNX_FIELD_ARRIVAL_V1",
        "order": "ORD-0326 attachment (input to ORD-0332)",
        "lane": "S1-q64sweep",
        "generation": TIP,
        "measured_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "measured_at_lane_local": (now + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M +08"),
        "ruling_basis": ["Q64=1 UI_EVIDENCE_EXPOSURE_GATE_V1", "Q68", "Q69", "CMDR 05:44 item 2"],
        "scope": {
            "components_landed": sorted(BLOBS),
            "legs": [
                "POST /api/v1/journeys/{id}/copilot/messages",
                "POST /api/v1/journeys/{id}/agent/hermes/runs/{runId}/stop",
                "POST /api/v1/journeys/{id}/agent/approvals/{approvalId}/approve",
            ],
            "client_methods": ["sendCopilotMessage", "stopNativeHermesRun", "approveAgentAction"],
            "note": "the commander's route name /copilot/message is singular; the real route is "
                    "plural `messages`, cited at backend/app/main.py:11090",
        },
        "allowed_fields": fields,
        "reachability_cites": reach,
        "reachability_count": len(reach),
        "census": {
            "main_py_lines": count_lines(export, MAIN),
            "request_id_hits_in_main_py": len(grep_hits(export, "request_id", MAIN)),
            "trace_id_hits_in_main_py": len(grep_hits(export, "trace_id", MAIN)),
            "elapsed_ms_hits_in_failureAttribution":
                grep_count(export, "elapsed_ms", "frontend/src/lib/failureAttribution.ts", ["*.ts"]),
            "backend_app_hits_body_bytes": grep_count(export, "body_bytes", "backend/app", ["*.py"]),
            "backend_app_hits_response_received":
                grep_count(export, "response_received", "backend/app", ["*.py"]),
            "backend_app_hits_content_type":
                grep_count(export, "content_type", "backend/app", ["*.py"]),
            "frontend_src_hits_body_bytes": grep_count(export, "body_bytes", "frontend/src",
                                                       ["*.ts", "*.tsx"]),
            "frontend_src_hits_response_received": grep_count(export, "response_received",
                                                              "frontend/src", ["*.ts", "*.tsx"]),
            "frontend_src_hits_text_length": grep_count(export, "text.length",
                                                        "frontend/src", ["*.ts", "*.tsx"]),
            "frontend_src_hits_content_length_header": grep_count(export, "content-length",
                                                                  "frontend/src", ["*.ts", "*.tsx"]),
            "http_status_plain_interpolation_lines_in_failureAttribution":
                len(grep_hits(export, "${attribution.http_status}", ATTR)),
            "http_status_mention_lines_in_failureAttribution":
                len(grep_hits(export, "http_status", ATTR)),
            "idempotency_key_sites_in_api_layer": len(grep_hits(export, "Idempotency-Key", API)),
        },
        "not_emitted": sorted(f for f, v in VERDICTS.items() if v.startswith("NOT-EMITTED")),
        "self_declared": "measurement for ORD-0332 input; no gate, no CLOSED claim",
    }


def selftest(export: Path) -> int:
    good = build(export)
    n = good["allowed_fields"]["http_status"]["cite_count"]
    try:
        build(export, bad=True)
        print("SELFTEST_FAILED corrupting a cited line still produced a document")
        return 4
    except SystemExit as exc:
        print("selftest killer: " + str(exc).splitlines()[0][:120])
    rebuilt = build(export)
    if rebuilt["allowed_fields"]["http_status"]["cite_count"] != n:
        print("SELFTEST_FAILED count moved between runs")
        return 5
    print(f"SELFTEST_OK fields={len(rebuilt['allowed_fields'])} cites={n} "
          f"total_cites={len(CITES)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    export = Path(a.export)
    if a.selftest:
        return selftest(export)
    doc = build(export)
    out = Path(a.out)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", out, "bytes", out.stat().st_size)
    for f, v in doc["allowed_fields"].items():
        print(f"  {f}: {v['verdict']} cites={v['cite_count']} layers={v['layer_count']}")
    print("  not_emitted:", ",".join(doc["not_emitted"]))
    print("  citation total:", len(CITES), " reachability cites:", doc["reachability_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
