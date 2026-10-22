"""Rewrite spec_architecture() in se_visio_specs_r1.py with the corrected
six-band layout where every connector joins vertically-adjacent or
horizontally-adjacent shapes, so no line has to cross a box.
"""
import ast
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "se_visio_specs_r1.py")

NEW = '''# ==========================================================================  01
CW = 2.62            # six-column grid across the full content width
GX = 0.42


def slot(c, span=1, gap=0.14):
    """Geometry of column c, optionally spanning several columns."""
    x = GX + c * CW + gap / 2.0
    w = CW * span - gap
    return {"x": round(x, 3), "w": round(w, 3)}


def spec_architecture():
    nodes, edges, bands = [], [], []

    R1Y, R1H = 0.92, 1.04
    R2Y, R2H = 2.06, 1.30
    R3Y, R3H = 3.46, 1.16
    R4Y, R4H = 4.72, 1.30
    R5Y, R5H = 6.12, 1.30
    R6Y, R6H = 7.52, 2.02

    bands = [
        band(GX - 0.06, R1Y, 16.14, R1H, "1   USERS & CLIENT SURFACE", "band", labelSize=9.0),
        band(GX - 0.06, R2Y, 16.14, R2H, "2   FRONTEND APPLICATION   React 19 + TypeScript 5.8 + Vite 7 + PWA   (frontend/src)", "band", labelSize=9.0),
        band(GX - 0.06, R3Y, 16.14, R3H, "3   BACKEND TRANSPORT   one FastAPI monolith, 175 endpoints under /api/v1   (backend/app/main.py, 14,569 lines)", "band", labelSize=9.0),
        band(GX - 0.06, R4Y, 16.14, R4H, "4   AI AGENT & HERMES CONTROL PLANE   the agent owns no domain truth: every mutation is decided by a gateway   (backend/app/agent)", "band", labelSize=9.0),
        band(GX - 0.06, R5Y, 16.14, R5H, "5   DOMAIN SERVICES   deterministic solver, business facts and the journey state machine", "band", labelSize=9.0),
        band(GX - 0.06, R6Y, 7.86, R6H, "6a   PERSISTENCE, AUDIT & OPERATIONAL STATE   SQLAlchemy + SQLite (WAL), 60 tables", "band", labelSize=9.0),
        band(8.28, R6Y, 7.86, R6H, "6b   PROVIDERS & INTEGRATIONS   9 clients; the deterministic mocks are the shipped default", "band", labelSize=9.0),
    ]

    g = slot(0, 3); g["y"], g["h"] = R1Y + 0.34, 0.58
    nodes.append(node("cli_traveler", "rect", "user",
                      "Traveler - phone, tablet landscape, desktop browser; installable PWA",
                      "frontend/src/main.tsx:38", g))
    g = slot(3, 3); g["y"], g["h"] = R1Y + 0.34, 0.58
    nodes.append(node("cli_admin", "rect", "user",
                      "Administrator - platform, provider health and policy console",
                      "use-cases/use-cases.yaml:17", g))

    FE = [("fe_shell", "V8Experience shell", "app/V8Experience.tsx:1", "offline snapshot, execution clock, wallet"),
          ("fe_routes", "15 routed panels", "routes/v8Routes.ts:1-33", "hub, live, map, studio, stay, discover, agent, twin, footprints, access"),
          ("fe_map", "JourneyMap", "components/JourneyMap.tsx:1", "MapLibre 5.24 + OpenFreeMap style, provenance badges"),
          ("fe_copilot", "CopilotDock + AgentComposer", "features/agent/CopilotDock.tsx:1", "the natural-language input box"),
          ("fe_rail", "AgentRunRail + feed", "features/agent/AgentRunRail.tsx:1", "shows the agent working state"),
          ("fe_plan", "Plan comparison, Trip Studio", "features/planning/PlanComparison.tsx:1", "check-ins and collections too")]
    for i, (id_, t, src, sub) in enumerate(FE):
        g = slot(i); g["y"], g["h"] = R2Y + 0.38, 0.82
        nodes.append(node(id_, "roundrect", "verified", t + chr(10) + sub, src, g))

    API = [("api_rest", "REST /api/v1 surface", "main.py:882, 3136, 4016, 7139", "journeys, plans, places, check-ins, collections, share, bookings"),
           ("api_agent", "Agent and copilot endpoints", "main.py:14169, 1367, 1246, 2081", "copilot messages, agent commands, tool calls, approvals, runs, feed"),
           ("api_ops", "Contract, stream, identity", "main.py:1982 ; contracts/openapi.yaml", "OpenAPI, SSE /operations/stream, server-owned agent token principal")]
    for i, (id_, t, src, sub) in enumerate(API):
        g = slot(i * 2, 2); g["y"], g["h"] = R3Y + 0.34, 0.70
        nodes.append(node(id_, "roundrect", "verified", t + chr(10) + sub, src, g))

    AG = [("pv_ai", "extdata", "external", "DeepSeek Responses API" + chr(10) + "model boundary: chat, vision, web search",
           "integrations/ai/responses.py:244 ; config.py:14-30"),
          ("ag_intent", "process", "verified", "Intent and context" + chr(10) + "8 intents over a server-built context",
           "main.py:14190-14228 ; main.py:13593"),
          ("ag_mission", "process", "verified", "Mission, plan, tool loop" + chr(10) + "compile_mission; at most 12 steps",
           "agent/mission.py:231,384 ; runtime.py:336"),
          ("ag_gw", "decision", "verified", "Tool gateway" + chr(10) + "allowlist, audit, idempotency, authorization",
           "agent/gateway.py:357-398, 59, 71"),
          ("ag_tools", "rect", "verified", "11 tools" + chr(10) + "6 V1 + 5 typed V2 actions",
           "agent/tool_catalog.py:26-59"),
          ("ag_surface", "rect", "built", "MCP V1/V2 + Hermes client" + chr(10) + "native binary absent, identity DIRECT",
           "agent-mcp/server.py:128,378 ; native_client.py:34")]
    for i, (id_, kind, st, txt, src) in enumerate(AG):
        g = slot(i); g["y"], g["h"] = R4Y + 0.38, 0.82
        nodes.append(node(id_, kind, st, txt, src, g))

    DS = [("ds_journey", "Journey lifecycle" + chr(10) + "create, configure, start, soft delete, history", "main.py:3136, 7139, 9294, 3337, 10019"),
          ("ds_twin", "Twin, capability, preference" + chr(10) + "three scopes, declared not invented", "main.py:9846, 2761, 2568 ; models.py:95,121"),
          ("ds_plan", "Plan generation and selection" + chr(10) + "deterministic solver, seeded, scored", "main.py:7369, 7728, 7790 ; config.py:44"),
          ("ds_replan", "Replanning" + chr(10) + "proposal only, then accept or reject", "main.py:10923, 13097, 13569 ; app/replanning"),
          ("ds_place", "Places and city services" + chr(10) + "real-city discovery, catalog hydration", "main.py:7328, 7355, 5558, 5572 ; discovery/real_city.py"),
          ("ds_com_guard", "Commerce, guardian, autopilot" + chr(10) + "bookings, commitments, resilience", "main.py:14404, 1599, 1772 ; app/commerce")]
    for i, (id_, txt, src) in enumerate(DS):
        g = slot(i); g["y"], g["h"] = R5Y + 0.38, 0.82
        nodes.append(node(id_, "process", "verified" if i < 5 else "built", txt, src, g))

    DB = [("db_core", "SQLite citynexus.db" + chr(10) + "WAL, foreign keys ON, write deadline", "db/session.py:70-88 ; config.py:10, 96-98"),
          ("db_agent", "Agent state" + chr(10) + "journey_missions, agent_runs, agent_run_steps, action_approvals", "models.py:212, 254, 271, 692"),
          ("db_state", "Domain and audit" + chr(10) + "60 tables: journeys, plan_versions, replan_proposals, audit_logs, idempotency_keys", "models.py:175, 511, 782, 562, 677")]
    for i, (id_, txt, src) in enumerate(DB):
        g = {"x": round(0.50 + i * 2.56, 3), "y": R6Y + 0.46, "w": 2.42, "h": 1.30}
        nodes.append(node(id_, "database", "data", txt, src, g))

    PV = [("pv_photon", "extdata", "verified", "Photon geocoder" + chr(10) + "no key required", "discovery/photon.py:20-27"),
          ("pv_osm", "extdata", "verified", "Nominatim + Overpass" + chr(10) + "POI, three mirrors", "discovery/real_city.py:617, 684-688"),
          ("pv_weather", "extdata", "built", "Open-Meteo context" + chr(10) + "weather and time", "context/open_meteo.py:29-36"),
          ("pv_valhalla", "extdata", "planned", "Valhalla routing" + chr(10) + "live URL not configured", "mobility/valhalla_http.py:32 ; BLOCKERS.md:13"),
          ("pv_region", "extdata", "built", "Amap + SearXNG" + chr(10) + "China region, web research", "china/amap.py:10,47 ; web/searxng.py:29"),
          ("pv_mock", "data", "verified", "Shipped default" + chr(10) + "mock city / mobility / booking / payment, real-city mode=replay", ".env.example:18-31 ; config.py:79-81")]
    for i, (id_, kind, st, txt, src) in enumerate(PV):
        col, r = i % 3, i // 3
        g = {"x": round(8.36 + col * 2.56, 3), "y": R6Y + 0.42 + r * 0.78, "w": 2.42, "h": 0.70}
        nodes.append(node(id_, kind, st, txt, src, g))

    edges = [
        edge("cli_traveler", "fe_shell", "HTTPS + PWA", "verified"),
        edge("cli_traveler", "fe_copilot", "types a request", "verified"),
        edge("cli_admin", "fe_routes", "console panels", "built"),
        edge("fe_shell", "api_rest", "journey CRUD", "verified"),
        edge("fe_routes", "api_rest", "", "verified"),
        edge("fe_map", "api_rest", "route evidence", "verified"),
        edge("fe_copilot", "api_agent", "POST /copilot/messages", "verified"),
        edge("fe_rail", "api_agent", "GET /agent-feed", "verified"),
        edge("fe_plan", "api_agent", "accept / reject", "verified"),
        edge("api_rest", "ds_journey", "", "verified"),
        edge("api_agent", "ag_intent", "", "verified"),
        edge("api_ops", "ag_surface", "MCP + SSE", "verified"),
        edge("ag_intent", "pv_ai", "model turn", "verified"),
        edge("ag_intent", "ag_mission", "", "verified"),
        edge("ag_mission", "ag_gw", "tool call", "verified"),
        edge("ag_gw", "ag_tools", "allowlisted", "verified"),
        edge("ag_tools", "ag_surface", "same handlers", "verified"),
        edge("ag_gw", "ds_replan", "request_replan", "verified"),
        edge("ag_tools", "ds_place", "search_city_services", "verified"),
        edge("ag_surface", "ds_com_guard", "typed booking actions", "built"),
        edge("ds_journey", "db_core", "ORM", "verified"),
        edge("ds_twin", "db_agent", "runs + steps", "verified"),
        edge("ds_place", "db_state", "places + versions", "verified"),
        edge("ds_journey", "pv_photon", "geocode", "verified"),
        edge("ds_place", "pv_osm", "POI", "verified"),
        edge("ds_twin", "pv_weather", "context", "built"),
        edge("ds_plan", "pv_valhalla", "travel matrix", "planned"),
        edge("ds_com_guard", "pv_region", "region adapters", "built"),
        edge("ds_plan", "pv_mock", "deterministic fixtures", "verified"),
    ]

    return {
        "file": "01_CityNexus_System_Architecture.vsdx",
        "pageName": "System Architecture",
        "title": "CityNexus - Smart City Traveler System   |   System Architecture",
        "subtitle": ("How the product actually runs. A traveler request enters the React shell, is served by one FastAPI "
                     "monolith, is planned by a deterministic solver, and may be reasoned about by an AI agent that owns no "
                     "domain truth: every agent mutation passes an allowlist, an audit write and an authorization decision."),
        "docid": "CNX-SE-VIS-01   System architecture (layered)",
        "revline": REVISION,
        "bodySize": 7.6,
        "subSize": 5.6,
        "bands": bands,
        "nodes": nodes,
        "edges": edges,
        "legend": STATE_LEGEND + [{"state": "user", "text": "Human actor / client surface"}],
        "legendOrigin": (0.46, 9.74),
        "footnotes": [
            "Counts taken from this tree on 2026-10-22: 175 = @app.get|post|patch|put|delete decorators in backend/app/main.py; 60 = __tablename__ declarations in backend/app/db/models.py; 14,569 = lines of main.py.",
            "Deployment defaults keep the AI and real-city paths switched off (CITYNEXUS_AI_ENABLED=false, CITYNEXUS_REAL_CITY_ENABLED=false, real-city mode=replay, impact provider=disabled: core/config.py:14, 79-81, 33).",
            "The picture therefore describes wiring present in code, not a claim that every provider is live in a given deployment.",
            "Dashed outline = written but not proven on the authoritative line (BLOCKERS.md:9-14). Amber fill = implemented without a passing gate on the current tip.",
            "Each shape carries its code anchor as a small second line, and the same anchor is stored in the custom property SourceRef so the drawing can be audited shape by shape inside Visio.",
        ],
        "footnoteOrigin": (9.05, 9.74),
    }


'''

start_marker = "# ==========================================================================  01"
end_marker = "# ==========================================================================  02"

src = open(P, encoding="utf-8").read()
i = src.index(start_marker)
j = src.index(end_marker)
out = src[:i] + NEW + src[j:]
open(P, "w", encoding="utf-8").write(out)
ast.parse(out)
print("spec 01 replaced, AST OK")
