"""CityNexus Visio diagram specs - the four coursework system-design drawings.

Every node carries `src`, a real `file:line` anchor into D:\\moodle\\CityNexus at
the reviewed tip, so nothing in the picture is a guess. State colours:
  verified  = implemented AND backed by a passing test / published commit
  built     = code exists but is not proven usable on the authoritative line
  planned   = documented intent with no implementation on this line
Numbers quoted in labels were counted in the same run that wrote this file
(see Evidence/AUTOMATION_VERIFICATION.md).
"""
PAGE_W, PAGE_H = 16.54, 11.69
X0, XW = 0.46, 12.02          # content column (legend lives to the right)


def row(y, w, h, n, gap=0.16, x0=X0, xw=XW):
    """Evenly spaced single-row layout; returns (x, y, w, h) dicts."""
    bw = (xw - gap * (n - 1)) / float(n)
    return [{"x": round(x0 + i * (bw + gap), 3), "y": y, "w": round(bw, 3), "h": h}
            for i in range(n)]


def band(x, y, w, h, label, state="band", **kw):
    d = {"x": x, "y": y, "w": w, "h": h, "label": label, "state": state,
         "labelSide": "top", "labelSize": 9.0}
    d.update(kw)
    return d


def node(id_, kind, state, text, src, geom, size=None):
    d = {"id": id_, "kind": kind, "state": state, "text": text, "src": src}
    d.update(geom)
    if size:
        d["size"] = size
    return d


def edge(a, b, label="", state="verified", **kw):
    d = {"from": a, "to": b, "label": label, "state": state}
    d.update(kw)
    return d


REVISION = ("Rev A - generated 2026-10-22 - source tree CityNexus @ "
            "review/boli-party-occupancy-scope-r1, "
            "github.com/Canshu-King/CityNexus")

STATE_LEGEND = [
    {"state": "verified", "text": "Implemented + evidence (test / published commit)"},
    {"state": "built", "text": "Implemented, not yet proven on the line"},
    {"state": "planned", "text": "Documented intent - no implementation here"},
    {"state": "external", "text": "External provider / third-party boundary"},
    {"state": "data", "text": "Persistence, audit and operational state"},
]

# ==========================================================================  01
CW = 2.62            # six-column grid
GX = 0.42


def slot(c, span=1, gap=0.14):
    x = GX + c * CW + gap / 2.0
    return {"x": round(x, 3), "w": round(CW * span - gap, 3)}


def spec_architecture():
    nodes, edges, bands = [], [], []

    R1Y, R1H = 0.90, 1.00
    R2Y, R2H = 2.00, 1.22
    R3Y, R3H = 3.30, 1.10
    R4Y, R4H = 4.48, 1.42
    R5Y, R5H = 6.00, 1.52
    LW, RX = 7.86, 8.28          # left half width, right half x

    bands = [
        band(GX - 0.06, R1Y, 16.14, R1H, "1   USERS & CLIENT SURFACE", "band", labelSize=9.0),
        band(GX - 0.06, R2Y, 16.14, R2H, "2   FRONTEND   React 19 + TypeScript 5.8 + Vite 7 + PWA   (frontend/src)", "band", labelSize=9.0),
        band(GX - 0.06, R3Y, 16.14, R3H, "3   BACKEND HTTP SURFACE   one FastAPI monolith, 175 endpoints under /api/v1   (backend/app/main.py, 14,569 lines)", "band", labelSize=9.0),
        band(GX - 0.06, R4Y, LW, R4H, "4a   AI AGENT & HERMES PLANE   the agent owns no domain truth   (backend/app/agent)", "agent", labelSize=9.0),
        band(RX, R4Y, LW, R4H, "4b   DOMAIN SERVICES   deterministic solver, business facts, journey state machine", "band", labelSize=9.0),
        band(GX - 0.06, R5Y, LW, R5H, "5a   PROVIDERS & INTEGRATIONS   9 clients; the deterministic mocks are the shipped default", "band", labelSize=9.0),
        band(RX, R5Y, LW, R5H, "5b   PERSISTENCE, AUDIT & OPERATIONAL STATE   SQLAlchemy + SQLite (WAL), 60 tables", "band", labelSize=9.0),
    ]

    def put(id_, kind, state, text, src, c, span, y, h):
        g = slot(c, span)
        g["y"], g["h"] = y, h
        nodes.append(node(id_, kind, state, text, src, g))

    # 1 users
    put("cli_traveler", "rect", "user",
        "Traveler" + chr(10) + "phone, tablet landscape, desktop browser",
        "frontend/src/main.tsx:38", 0, 2, R1Y + 0.32, 0.56)
    put("cli_admin", "rect", "user",
        "Administrator" + chr(10) + "platform and provider console",
        "use-cases/use-cases.yaml:17", 2, 2, R1Y + 0.32, 0.56)

    # 2 frontend
    FE = [("fe_copilot", "CopilotDock + AgentComposer", "features/agent/CopilotDock.tsx:1",
           "the natural-language input box"),
          ("fe_rail", "AgentRunRail + feed", "features/agent/AgentRunRail.tsx:1",
           "shows the agent working state"),
          ("fe_shell", "V8Experience shell", "app/V8Experience.tsx:1",
           "offline snapshot, execution clock, wallet"),
          ("fe_plan", "Plan comparison + Trip Studio", "features/planning/PlanComparison.tsx:1",
           "accept or reject what the agent proposes"),
          ("fe_map", "JourneyMap", "components/JourneyMap.tsx:1",
           "MapLibre 5.24, OpenFreeMap style, provenance badges"),
          ("fe_routes", "15 routed panels", "routes/v8Routes.ts:1-33",
           "hub, live, map, studio, stay, discover, agent, twin, footprints, access")]
    for i, (id_, t, src, sub) in enumerate(FE):
        put(id_, "roundrect", "verified", t + chr(10) + sub, src, i, 1, R2Y + 0.38, 0.74)

    # 3 backend http surface
    put("api_agent", "roundrect", "verified",
        "Agent surface" + chr(10) + "/copilot/messages, /agent/commands, /agent/tools/{name}, /approvals/{id}/approve, /agent-feed; the MCP V1 and V2 surfaces reach the same gateway",
        "main.py:14169, 1367, 1246, 2081, 10125", 0, 2, R3Y + 0.34, 0.66)
    put("api_shared", "roundrect", "verified",
        "Shared transport" + chr(10) + "journeys, plans, places, replans, check-ins, collections, share, bookings - 175 endpoints",
        "main.py:3136, 7369, 7328, 10923, 4296, 14404", 2, 2, R3Y + 0.34, 0.66)
    put("api_data", "roundrect", "verified",
        "Data & ops surface" + chr(10) + "/experience, /twin, /route-evidence, SSE /operations/stream, OpenAPI, server-owned agent identity",
        "main.py:5473, 9846, 10525, 1982 ; contracts/openapi.yaml", 4, 2, R3Y + 0.34, 0.66)

    # 4a agent plane
    put("ag_entry", "process", "verified",
        "Entry: intent + context" + chr(10) + "8 intents over a server-built context; semantic envelope decides what the model may conclude",
        "main.py:14190-14228, 13593 ; semantic_compiler.py:123,229", 0, 1, R4Y + 0.40, 0.90)
    put("ag_loop", "subprocess", "verified",
        "Mission, plan, tool loop" + chr(10) + "compile_mission, build_mission_plan, run(max_steps=12)",
        "agent/mission.py:231,384 ; runtime.py:62,336", 1, 1, R4Y + 0.40, 0.90)
    put("ag_gw", "process", "verified",
        "Tool gateway" + chr(10) + "allowlist of 11 tools, audit write, idempotency, then ALLOW_AUTO / REQUIRE_CONFIRMATION / DENY",
        "agent/gateway.py:357-398, 59, 71, 338-347", 2, 1, R4Y + 0.40, 0.90)

    # 4b domain services
    put("ds_journey", "process", "verified",
        "Journeys, plans, replans" + chr(10) + "lifecycle, deterministic seeded solver, proposal-only replanning, accept / reject",
        "main.py:3136, 7369, 7790, 10923, 13097 ; app/replanning", 3, 1, R4Y + 0.40, 0.90)
    put("ds_twin", "process", "verified",
        "Twin, capability, preference" + chr(10) + "three preference scopes; declared-not-invented budget and party size",
        "main.py:9846, 2761, 2568 ; models.py:95,121,824", 4, 1, R4Y + 0.40, 0.90)
    put("ds_place", "process", "verified",
        "Places, city services, commerce, guardian" + chr(10) + "real-city discovery, catalog hydration, bookings and commitments, autopilot",
        "main.py:7328, 5558, 5572, 14404, 1599 ; discovery/real_city.py", 5, 1, R4Y + 0.40, 0.90)

    # 5a providers
    put("pv_ai", "extdata", "external",
        "DeepSeek Responses API" + chr(10) + "chat, vision, web search; ai_enabled defaults to false",
        "integrations/ai/responses.py:244 ; config.py:14-30", 0, 1, R5Y + 0.44, 0.90)
    put("pv_mock", "data", "verified",
        "Shipped default provider set" + chr(10) + "mock city / mobility / booking / payment; real-city mode=replay",
        ".env.example:18-31 ; config.py:79-81 ; integrations/mock/providers.py:13", 1, 1, R5Y + 0.44, 0.90)
    put("pv_geo", "extdata", "external",
        "Photon, Nominatim, Overpass" + chr(10) + "geocode, POI, weather; Valhalla live URL not set",
        "photon.py:20 ; real_city.py:617 ; BLOCKERS.md:13", 2, 1, R5Y + 0.44, 0.90)

    # 5b persistence
    put("db_core", "database", "data",
        "SQLite citynexus.db" + chr(10) + "WAL, foreign keys ON, write deadline and busy timeout",
        "db/session.py:70-88 ; config.py:10, 96-98", 3, 1, R5Y + 0.44, 0.90)
    put("db_state", "database", "data",
        "Journey truth" + chr(10) + "journeys, plan_versions, activities, commitments",
        "models.py:175, 511, 535, 578, 712", 4, 1, R5Y + 0.44, 0.90)
    put("db_agent", "database", "data",
        "Agent state and audit" + chr(10) + "agent_runs, agent_run_steps, approvals, audit_logs",
        "models.py:254, 271, 562, 677", 5, 1, R5Y + 0.44, 0.90)

    edges = [
        edge("cli_traveler", "fe_copilot", "", "verified"),
        edge("cli_traveler", "fe_rail", "", "verified"),
        edge("cli_admin", "fe_shell", "HTTPS + PWA", "verified"),
        edge("cli_admin", "fe_plan", "console panels", "built"),
        edge("fe_copilot", "api_agent", "POST /copilot/messages", "verified"),
        edge("fe_rail", "api_agent", "", "verified"),
        edge("fe_shell", "api_shared", "journey CRUD", "verified"),
        edge("fe_plan", "api_shared", "accept / reject", "verified"),
        edge("fe_map", "api_data", "route evidence", "verified"),
        edge("fe_routes", "api_data", "experience + twin", "verified"),
        edge("api_agent", "ag_entry", "", "verified"),
        edge("api_shared", "ag_loop", "", "verified"),
        edge("api_shared", "ds_journey", "", "verified"),
        edge("api_data", "ds_twin", "", "verified"),
        edge("api_data", "ds_place", "", "verified"),
        edge("ag_entry", "ag_loop", "", "verified"),
        edge("ag_loop", "ag_gw", "tool call", "verified"),
        edge("ag_gw", "ds_journey", "request_replan / accept_replan", "verified"),
        edge("ag_entry", "pv_ai", "model turn", "verified"),
        edge("ag_loop", "pv_mock", "", "verified"),
        edge("ag_gw", "pv_geo", "", "verified"),
        edge("ds_journey", "db_core", "ORM", "verified"),
        edge("ds_twin", "db_state", "twin + versions", "verified"),
        edge("ds_place", "db_agent", "", "built"),
    ]

    return {
        "file": "01_CityNexus_System_Architecture.vsdx",
        "pageName": "System Architecture",
        "title": "CityNexus - Smart City Traveler System   |   System Architecture",
        "subtitle": ("How the product actually runs. A traveler request enters the React shell, is served by one FastAPI "
                     "monolith, and may be reasoned about by an AI agent that owns no domain truth: every agent mutation "
                     "passes an allowlist, an audit write and an authorization decision before a deterministic solver "
                     "touches journey state."),
        "docid": "CNX-SE-VIS-01   System architecture (layered)",
        "revline": REVISION,
        "bodySize": 7.4,
        "subSize": 5.6,
        "bands": bands,
        "nodes": nodes,
        "edges": edges,
        "legend": STATE_LEGEND + [{"state": "user", "text": "Human actor / client surface"},
                                  {"state": "agent", "text": "Agent control plane"}],
        "legendOrigin": (0.46, 7.86),
        "notes": [
            "THE 11 TOOLS THE GATEWAY ACTUALLY EXPOSES  (backend/app/agent/tool_catalog.py:26-59)",
            "read-only:  inspect_journey, inspect_twin, list_replans, search_city_services",
            "plan-shaping:  request_replan, accept_replan",
            "typed actions:  replace_activity, reschedule_activity, create_booking, cancel_refundable_booking, request_commitment_change",
            "NOT AN AUTOMATION CLOSURE:  native Hermes binary absent and runtime identity still DIRECT (BLOCKERS.md:9-12); live Valhalla URL not configured (BLOCKERS.md:13); no real payment instrument registered (AGENT_TOOL_CATALOG.md:16-18); impact resolver default disabled (config.py:33); physical phone / PWA shadow trial not performed (CURRENT_STATUS.md:4).",
            "COUNTS, taken from this tree on 2026-10-22:  175 = @app.get|post|patch|put|delete decorators in backend/app/main.py;  60 = __tablename__ declarations in backend/app/db/models.py;  14,569 = lines of main.py;  242 backend test modules, 184 frontend e2e specs.",
            "DEFAULTS:  CITYNEXUS_AI_ENABLED=false, CITYNEXUS_REAL_CITY_ENABLED=false, real-city mode=replay, impact provider=disabled (core/config.py:14, 79-81, 33) - the picture describes wiring present in code, not a claim that every provider is live in a given deployment.",
            "AUDIT:  every shape carries its code anchor as a small second line and stores the same anchor in the custom property SourceRef, so the drawing can be checked shape by shape inside Visio.",
        ],
        "notesOrigin": (7.10, 7.86),
        "notesWidth": 9.0,
        "notesSize": 6.4,
    }

# ==========================================================================  02
JCOLS = 8
JCW = 11.88 / JCOLS


def spec_user_journey():
    lanes = [("L1", "TRAVELER", 1.00, 1.34),
             ("L2", "FRONTEND   React / V8Experience", 2.44, 1.34),
             ("L3", "BACKEND API   FastAPI /api/v1", 3.88, 1.34),
             ("L4", "AI AGENT   mission, tool loop, approval", 5.32, 1.34),
             ("L5", "DATA & PROVIDERS", 6.76, 1.34)]
    bands = [band(0.40, y, 12.10, h, "%s   %s" % (k, t), "laneband", dash="2", labelSize=8.0)
             for k, t, y, h in lanes]
    ly = dict((k, (y, h)) for k, t, y, h in lanes)

    nodes, edges = [], []

    def put(id_, kind, state, text, src, lane, col, role=None):
        y, lh = ly[lane]
        bw = JCW - 0.13
        bh = 0.82
        geom = {"x": round(0.46 + col * JCW + (JCW - bw) / 2.0, 3),
                "y": round(y + 0.34 + (lh - 0.34 - bh) / 2.0, 3),
                "w": round(bw, 3), "h": bh}
        d = node(id_, kind, state, text, src, geom)
        if role:
            d["role"] = role
        nodes.append(d)

    put("start", "terminator", "user", "Open CityNexus", "frontend/src/main.tsx:38",
        "L1", 0, role="start")
    put("j1", "rect", "user", "Destination, dates, needs",
        "main.py:3136 POST /journeys", "L1", 1)
    put("d_city", "decision", "user", "City OK?",
        "main.py:5558 /destinations/capability", "L1", 2)
    put("j2", "rect", "user", "Read the plan and the map",
        "features/planning/PlanComparison.tsx:1", "L1", 4)
    put("d_ok", "decision", "user", "Happy with it?",
        "features/agent/CopilotDock.tsx:1", "L1", 5)
    put("d_exec", "decision", "user", "Travelling?",
        "main.py:9294 POST /journeys/{id}/start", "L1", 7)
    put("end", "terminator", "user", "Trip recorded",
        "main.py:10019 GET /journeys/{id}/history", "L1", 8, role="end")

    put("f_wiz", "process", "verified", "Three-step wizard",
        "routes/v8Routes.ts:1-33", "L2", 1)
    put("f_map", "process", "verified", "Map and plan cards",
        "components/JourneyMap.tsx:1", "L2", 4)
    put("f_cop", "process", "verified", "Copilot box sends the ask",
        "citynexus.ts:935 POST /copilot/messages", "L2", 5)
    put("f_rail", "process", "verified", "Agent rail shows progress",
        "main.py:10125 GET /agent-feed", "L2", 6)
    put("f_today", "process", "verified", "Today screen, server clock",
        "main.py:5473, 6723", "L2", 7)
    put("f_hist", "process", "verified", "History and footprints",
        "features/checkin/checkins.ts:148", "L2", 8)

    put("b_create", "process", "verified", "Create the journey row",
        "main.py:3136", "L3", 1)
    put("b_cap", "process", "verified", "What can this city do?",
        "main.py:5558", "L3", 2)
    put("b_gen", "process", "verified", "Store plan versions",
        "main.py:7369, 7759", "L3", 3)
    put("b_appr", "process", "verified", "Approve / reject a proposal",
        "main.py:13097, 13569, 2081", "L3", 6)
    put("b_start", "process", "verified", "Start the journey",
        "main.py:9294", "L3", 7)
    put("b_evt", "process", "built", "Activity events depart, arrive, begin, complete, skip",
        "main.py:9424-9519", "L3", 8)

    put("a_prop", "process", "verified", "Replan proposal only",
        "main.py:10923 POST /replans", "L4", 4)
    put("a_int", "process", "verified", "Classify intent, build context",
        "main.py:14190-14228, 13593", "L4", 5)
    put("a_loop", "subprocess", "verified", "Mission, plan, loop of 12",
        "agent/mission.py:384 ; runtime.py:336", "L4", 6)
    put("a_gate", "decision", "verified", "Truth, money, C4?",
        "agent/gateway.py:338-347", "L4", 7)

    put("p_mock", "extdata", "verified", "Mock providers (default)",
        ".env.example:18-31 ; config.py:79-81", "L5", 2)
    put("p_geo", "extdata", "external", "Photon / Nominatim / Overpass",
        "discovery/photon.py:20 ; real_city.py:617", "L5", 3)
    put("d_rep", "database", "data", "replan_proposals + version",
        "models.py:782, 511", "L5", 4)
    put("d_db", "database", "data", "journeys, events, check-ins",
        "models.py:175, 712, 1324, 562", "L5", 6)
    put("d_aud", "database", "data", "agent_runs and agent_run_steps",
        "models.py:254, 271", "L5", 7)

    edges = [
        edge("start", "j1", "", "user"),
        edge("j1", "f_wiz", "submits", "verified"),
        edge("f_wiz", "b_create", "HTTP", "verified"),
        edge("b_create", "b_cap", "", "verified"),
        edge("b_cap", "d_city", "answers", "verified"),
        edge("d_city", "b_gen", "YES", "verified"),
        edge("d_city", "j1", "NO, another city", "verified"),
        edge("b_gen", "p_geo", "place lookup", "verified"),
        edge("b_gen", "p_mock", "fallback data", "verified"),
        edge("p_geo", "f_map", "geometry", "verified"),
        edge("b_gen", "f_map", "plans", "verified"),
        edge("f_map", "j2", "shown", "verified"),
        edge("j2", "d_ok", "", "user"),
        edge("d_ok", "f_cop", "NO, ask for a change", "verified"),
        edge("d_ok", "d_exec", "YES", "verified"),
        edge("f_cop", "a_int", "message", "verified"),
        edge("a_int", "a_loop", "", "verified"),
        edge("a_loop", "a_gate", "", "verified"),
        edge("a_gate", "a_prop", "YES", "verified"),
        edge("a_gate", "f_rail", "NO, read-only answer", "verified"),
        edge("a_prop", "d_rep", "persisted", "verified"),
        edge("a_prop", "f_map", "new version to review", "verified"),
        edge("f_rail", "j2", "updated result", "verified"),
        edge("a_loop", "d_aud", "each step recorded", "verified"),
        edge("d_rep", "b_appr", "awaits you", "verified"),
        edge("b_appr", "d_exec", "decided", "verified"),
        edge("d_exec", "b_start", "YES", "verified"),
        edge("d_exec", "f_hist", "NO, review only", "verified"),
        edge("b_start", "f_today", "live screen", "verified"),
        edge("f_today", "b_evt", "on the ground", "built"),
        edge("b_evt", "d_db", "events written", "built"),
        edge("b_evt", "a_int", "disruption reported", "built"),
        edge("b_evt", "end", "trip finished", "built"),
        edge("f_hist", "end", "", "verified"),
    ]

    return {
        "file": "02_CityNexus_User_Journey.vsdx",
        "pageName": "User Journey",
        "edgeRule": "none",
        "title": "CityNexus   |   End-to-end User Journey",
        "subtitle": ("Five swim lanes follow the real call path, from opening the app to the footprint after the trip. "
                     "The traveler never loses control: an agent may answer a question silently, but anything that changes "
                     "the plan is written as a proposal and waits for an explicit approval."),
        "docid": "CNX-SE-VIS-02   User journey (cross-functional flowchart)",
        "revline": REVISION,
        "bodySize": 7.0,
        "subSize": 5.2,
        "bands": bands,
        "nodes": nodes,
        "edges": edges,
        "legend": STATE_LEGEND + [{"state": "user", "text": "The traveler's own step"}],
        "legendOrigin": (12.62, 9.46),
        "notes": [
            "HOW TO READ THIS: follow one column at a time. A step in the traveler lane is what you see; the lanes below it are what the product does while you wait.",
            "EVERY BRANCH CLOSES. The two diamonds in the traveler lane and the one in the agent lane each have a labelled YES and NO, and both outcomes lead somewhere; the only terminal shape is the one on the right.",
            "PARTY SIZE AND STAY BUDGET ARE DELIBERATELY LEFT BLANK at first: the journey record keeps three states instead of inventing a value, and a plan that needs a budget you never declared says so (models.py:824 stay_budget_declared; ORD-0355).",
            "ACTIVITY EVENTS (depart, arrive, begin, complete, skip) are wired and reachable, but their real-world timestamps are still recorded as non-blocking debt, which is why that shape is amber (KNOWN_NONBLOCKING_DEBT.md).",
            "The loop back from the agent lane to the map is the point of the product: a change you approve becomes a new plan version, not an edited-over screen.",
        ],
        "notesOrigin": (0.46, 9.42),
        "notesWidth": 11.7,
        "notesSize": 6.8,
    }


# ==========================================================================  03
# Redrawn against gateway.py as measured on 2026-10-22:
#   dispatch()  :358 allowlist test -> :359 raise HTTPException(404)
#                 -> :377 record_audit -> :397 commit -> :398 handler
#   so an unknown tool name is refused BEFORE any audit row is written.
#   request_replan() :559 evaluate_action -> :576 _read_idempotent -> :626
#                 record_audit -> :645 _write_idempotent   (policy first)
#   accept_replan()  :680 evaluate_action -> :695 _read_idempotent -> :799
#                 record_audit -> :824 _write_idempotent
#   read handlers  :421 / :437 / :482 / :497 return ALLOW_AUTO with no policy call
#   typed handlers :1041-1053, :1178, :1238, :1286 raise domain guards
#                 (409 / 422 / 404); request_commitment_change audits at :1363
# There is therefore no single universal door order and the drawing says so.
def spec_agent_workflow():
    lanes = [("A", "REQUEST AND MODEL BOUNDARY", 1.00, 1.34),
             ("B", "AGENT RUNTIME (backend/app/agent/runtime.py)", 2.44, 1.34),
             ("C", "GATEWAY ENTRY (gateway.py dispatch)", 3.88, 1.34),
             ("D", "HANDLER-SPECIFIC DOORS", 5.32, 1.34),
             ("E", "DOMAIN SERVICES AND PERSISTED STATE", 6.76, 1.34),
             ("F", "TRAVELER SEES AND DECIDES", 8.20, 1.34)]
    bands = [band(0.40, y, 12.10, h, "%s   %s" % (k, t), "laneband", dash="2", labelSize=8.0)
             for k, t, y, h in lanes]
    ly = dict((k, (y, h)) for k, t, y, h in lanes)
    nodes, edges = [], []
    LC = 7
    cw = 11.88 / LC

    def put(id_, kind, state, text, src, lane, col, role=None, h=0.82):
        y, lh = ly[lane]
        bw = cw - 0.13
        geom = {"x": round(0.46 + col * cw + (cw - bw) / 2.0, 3),
                "y": round(y + 0.34 + (lh - 0.34 - h) / 2.0, 3), "w": round(bw, 3), "h": h}
        d = node(id_, kind, state, text, src, geom)
        if role:
            d["role"] = role
        nodes.append(d)

    put("a_start", "terminator", "agent", "A request arrives",
        "main.py:14169, 1367", "A", 0, role="start")
    put("a_ctx", "process", "verified", "Trusted context built server-side",
        "main.py:13593", "A", 1)
    put("a_avail", "decision", "verified", "AI up?", "config.py:14 ; ai_availability.py",
        "A", 2)
    put("a_int", "process", "verified", "Classify into one of 8 intents",
        "main.py:14190-14228", "A", 3)
    put("a_env", "process", "verified", "Semantic envelope and policy",
        "semantic_compiler.py:123, 229", "A", 4)
    put("a_fall", "process", "built", "Deterministic fallback, no model turn",
        "main.py:13722 ; ai_availability.py", "A", 2, h=0.0)
    nodes.pop()  # fallback belongs one row lower, redrawn below
    put("a_fall", "rect", "built", "Deterministic fallback, no model turn, availability worded NOT_CONFIGURED or DISABLED_BY_OPS",
        "main.py:13722 ; ai_availability.py", "A", 5, h=0.82)
    put("pv_ai", "extdata", "external", "DeepSeek Responses API",
        "responses.py:244 ; config.py:14-30", "A", 6)

    put("a_mis", "process", "verified", "Mission and plan compiled",
        "mission.py:231,384 ; mission_plan.py:74", "B", 0)
    put("a_run", "process", "verified", "AgentRun opened",
        "runtime.py:238 ; models.py:254", "B", 1)
    put("a_budget", "decision", "verified", "Step < 12?", "runtime.py:336", "B", 2)
    put("a_offer", "process", "verified", "Tool catalogue offered to the model",
        "runtime.py:62", "B", 3)
    put("a_choice", "decision", "verified", "Model wants a tool?", "runtime.py:395-420", "B", 4)
    put("a_result", "process", "verified", "Result analysed, run payload persisted",
        "runtime.py:238", "B", 5)
    put("a_fail", "decision", "verified", "Provider failed?", "runtime.py:660", "B", 6)

    put("a_gw", "process", "verified", "dispatch(tool_name, request)",
        "gateway.py:357", "C", 1)
    put("a_allow", "decision", "verified", "On the allowlist?", "gateway.py:358", "C", 2)
    put("a_404", "rect", "verified", "HTTP 404 raised at gateway.py:359, which is BEFORE record_audit at :377 - an unknown tool name leaves no audit row from this door",
        "gateway.py:358-359 vs :377", "C", 3, h=1.04)
    put("a_audit", "process", "verified", "Only now: audit the request and commit",
        "gateway.py:377-397", "C", 4)
    put("a_family", "decision", "verified", "Which handler family?",
        "gateway.py:360-372", "C", 5)
    put("a_more", "decision", "verified", "More work?", "runtime.py:336", "C", 6)

    put("a_read", "process", "verified", "Read handlers answer ALLOW_AUTO with no policy call",
        "gateway.py:421, 437, 482, 497", "D", 0, h=0.9)
    put("a_auth", "process", "verified", "Replan pair: evaluate_action policy FIRST",
        "gateway.py:559, 680", "D", 1, h=0.9)
    put("a_idem", "process", "verified", "then the idempotency replay check",
        "gateway.py:576, 695", "D", 2, h=0.9)
    put("a_guard", "process", "built", "Typed actions: per-handler domain guards 409 / 422 / 404",
        "gateway.py:1041-1053, 1178, 1238, 1286", "D", 3, h=0.9)
    put("a_confirm", "process", "built", "REQUIRE_CONFIRMATION: approval held, not applied yet",
        "gateway.py:341-347, 720, 748 ; main.py:2081", "D", 4, h=0.9)
    put("a_write", "process", "verified", "effect, then audit, then the idempotent receipt",
        "gateway.py:626, 645, 799, 824, 1363", "D", 5, h=0.9)
    put("a_note", "rect", "planned", "There is no single door order to claim: policy precedes idempotency in the replan pair, reads skip both, typed actions use their own guards",
        "measured per handler 2026-10-22", "D", 6, h=1.04)
    nodes[-1]["role"] = "note"

    put("a_exec", "process", "verified", "Domain service performs it",
        "main.py:10923, 13097 ; app/replanning", "E", 1)
    put("d_runs", "database", "data", "agent_runs and agent_run_steps",
        "models.py:254, 271", "E", 2)
    put("d_audit", "database", "data", "audit_logs, actor_type AI_AGENT",
        "models.py:562 ; gateway.py:377", "E", 3)
    put("d_idem", "database", "data", "idempotency_keys", "models.py:677", "E", 4)
    put("a_prop", "process", "verified", "Replan proposal produced, never applied silently",
        "main.py:10923 ; models.py:782", "E", 5)
    put("a_degrade", "process", "verified", "Degraded or skipped run recorded; journey truth unchanged",
        "runtime.py:660 ; AGENT_RUNTIME_ARCHITECTURE.md:12-15", "E", 6, h=0.9)

    put("a_show", "process", "verified", "Feed, timeline and rail show it",
        "main.py:10125, 1099, 2032", "F", 2)
    put("a_fb", "rect", "user", "You accept, reject, or keep talking",
        "main.py:13097, 13569", "F", 4)
    put("a_stop", "terminator", "agent", "Run closed and readable",
        "main.py:929, 1099", "F", 6, role="end")

    edges = [
        edge("a_start", "a_ctx", "", "agent"),
        edge("a_ctx", "a_avail", "", "verified"),
        edge("a_avail", "a_int", "YES", "verified"),
        edge("a_avail", "a_fall", "NO", "built"),
        edge("a_fall", "a_show", "plain answer", "built"),
        edge("a_int", "a_env", "", "verified"),
        edge("a_int", "pv_ai", "model turn", "verified"),
        edge("a_env", "a_mis", "", "verified"),
        edge("a_mis", "a_run", "", "verified"),
        edge("a_run", "a_budget", "", "verified"),
        edge("a_budget", "a_offer", "YES", "verified"),
        edge("a_offer", "a_choice", "", "verified"),
        edge("a_choice", "a_gw", "YES", "verified"),
        edge("a_choice", "a_result", "NO, final answer", "verified"),
        edge("a_gw", "a_allow", "", "verified"),
        edge("a_allow", "a_404", "NO", "verified"),
        edge("a_allow", "a_audit", "YES", "verified"),
        edge("a_audit", "a_family", "", "verified"),
        edge("a_family", "a_read", "read", "verified"),
        edge("a_family", "a_auth", "replan pair", "verified"),
        edge("a_family", "a_guard", "typed action", "built"),
        edge("a_auth", "a_idem", "policy first", "verified"),
        edge("a_idem", "a_confirm", "", "verified"),
        edge("a_confirm", "a_write", "allowed or approved", "built"),
        edge("a_guard", "a_write", "guards passed", "built"),
        edge("a_read", "a_result", "ALLOW_AUTO", "verified"),
        edge("a_write", "a_exec", "", "verified"),
        edge("a_exec", "d_runs", "steps recorded", "verified"),
        edge("a_exec", "a_prop", "if it changes the plan", "verified"),
        edge("a_write", "d_audit", "audit row", "verified"),
        edge("a_write", "d_idem", "receipt", "verified"),
        edge("a_exec", "a_result", "", "verified"),
        edge("a_result", "a_fail", "", "verified"),
        edge("a_fail", "a_degrade", "YES", "verified"),
        edge("a_fail", "a_prop", "NO", "verified"),
        edge("a_degrade", "a_show", "truth untouched", "verified"),
        edge("a_prop", "a_show", "", "verified"),
        edge("a_show", "a_fb", "", "verified"),
        edge("a_fb", "a_more", "", "verified"),
        edge("a_more", "a_ctx", "keep going", "verified"),
        edge("a_more", "a_stop", "NO", "verified"),
        edge("a_budget", "a_degrade", "NO, spent", "verified"),
        edge("a_404", "a_fail", "call failed", "verified"),
    ]

    panels = [
        band(12.44, 1.00, 3.78, 3.10, "PROVEN CAPABILITY", "band", labelSize=8.0),
        band(12.44, 4.28, 3.78, 3.10, "HONEST GAP LIST", "planned", labelSize=8.0),
    ]
    nodes.append(node("t_list", "rect", "verified",
                      "THE 11 TOOLS THIS BUILD EXPOSES   tool_catalog.py:26-59" + chr(10)
                      + "read-only: inspect_journey, inspect_twin, list_replans, search_city_services" + chr(10)
                      + "plan-shaping: request_replan, accept_replan" + chr(10)
                      + "typed: replace_activity, reschedule_activity, create_booking, cancel_refundable_booking, request_commitment_change" + chr(10)
                      + "MCP: V1 six tools server.py:157-207, V2 eleven server.py:404-549",
                      "tool_catalog.py:26-59",
                      {"x": 12.52, "y": 1.34, "w": 3.62, "h": 2.62}, size=6.4))
    nodes[-1]["role"] = "note"
    nodes.append(node("not_list", "rect", "planned",
                      "WHAT IS STILL MISSING" + chr(10)
                      + "native Hermes binary absent, runtime identity still DIRECT (BLOCKERS.md:9-12)" + chr(10)
                      + "live Valhalla URL not configured, travel matrix stays mocked (BLOCKERS.md:13-14)" + chr(10)
                      + "no real payment or refund instrument registered (AGENT_TOOL_CATALOG.md:16-18)" + chr(10)
                      + "impact resolver default disabled (config.py:33)" + chr(10)
                      + "physical phone and PWA shadow trial not performed (CURRENT_STATUS.md:4)",
                      "BLOCKERS.md:9-16 ; AGENT_TOOL_CATALOG.md:16-18",
                      {"x": 12.52, "y": 4.62, "w": 3.62, "h": 2.62}, size=6.4))
    nodes[-1]["role"] = "note"

    return {
        "file": "03_CityNexus_Agent_Workflow.vsdx",
        "pageName": "Agent Workflow",
        "edgeRule": "none",
        "title": "CityNexus   |   AI Agent Autonomy and Tool-Calling Workflow",
        "subtitle": ("Six lanes, drawn against gateway.py as measured on 2026-10-22. The point is not that the agent is "
                     "smart but that it is bounded: an unknown tool is refused before anything is written, reads answer "
                     "without a policy call, the replan pair runs policy then idempotency, and typed actions carry their "
                     "own domain guards. A failed provider becomes a recorded degraded run, never a quiet rewrite."),
        "docid": "CNX-SE-VIS-03   Agent workflow (measured handler paths)",
        "revline": REVISION,
        "bodySize": 6.8,
        "subSize": 5.0,
        "bands": bands + panels,
        "nodes": nodes,
        "edges": edges,
        "legend": [
            {"state": "verified", "text": "Read in the source and cited line by line"},
            {"state": "built", "text": "Present but not proven on the current line"},
            {"state": "planned", "text": "Missing or future work"},
            {"state": "agent", "text": "Agent-owned step"},
            {"state": "user", "text": "Human in the loop"},
            {"state": "external", "text": "Model boundary"},
            {"state": "data", "text": "Persisted state"},
        ],
        "legendOrigin": (0.46, 9.66),
        "notes": [
            "CORRECTION MADE IN THIS VERSION: an earlier draft drew one universal door order (allowlist, then idempotency, then authorization) and said an unknown tool was still audited. Neither is what the code does. dispatch() raises the 404 at gateway.py:359 and only reaches record_audit at :377 for a tool that passed the allowlist; and in request_replan the policy decision at :559 comes BEFORE the idempotency lookup at :576.",
            "So the diagram now separates the three handler families, because they genuinely differ: read handlers return ALLOW_AUTO with no policy call (:421, :437, :482, :497); the replan pair runs policy then idempotency then effect then audit then receipt (:559, :576, :626, :645 and :680, :695, :799, :824); the typed actions raise their own domain guards (:1041-1053, :1178, :1238, :1286) and request_commitment_change audits at :1363.",
            "max_steps=12 is a real bound at runtime.py:336; spending it is reported as a degraded run rather than retried invisibly.",
            "The right-hand panels belong in the model. The coursework asks to separate what the code does today from what is planned, and claiming a closed automation loop here would be false.",
        ],
        "notesOrigin": (4.98, 9.70),
        "notesWidth": 11.0,
        "notesSize": 6.4,
    }


# ==========================================================================  04
# Split into two pages of the SAME .vsdx: a readable overview for the marker,
# and the included-detail page that carries all 14 «include» relationships.
def spec_use_case():
    common = dict(
        file="04_CityNexus_Use_Case.vsdx",
        title="CityNexus   |   UML Use Case Model",
        docid="CNX-SE-VIS-04   UML use case diagram (2 pages)",
        revline=REVISION,
        bodySize=7.4,
        subSize=5.4,
    )

    UC = [("UC-01", "Manage Account and Preferences", "verified"),
          ("UC-02", "Create and Configure Journey", "verified"),
          ("UC-03", "Manage Journey Commitments", "verified"),
          ("UC-04", "Generate and Select Journey Plan", "verified"),
          ("UC-05", "Discover and Recommend City Services", "verified"),
          ("UC-06", "Book and Order City Services", "built"),
          ("UC-07", "Make Secure Payment", "planned"),
          ("UC-08", "Execute Journey", "verified"),
          ("UC-09", "Detect and Assess Journey Events", "built"),
          ("UC-10", "Replan Disrupted Journey", "verified"),
          ("UC-11", "Use AI Journey Copilot", "verified"),
          ("UC-12", "Review Journey History and Changes", "verified"),
          ("UC-13", "Administer Platform and Providers", "built")]
    state = dict((k, v) for k, _t, v in UC)

    # ---------------- page 1: overview
    boundary = band(2.30, 0.96, 8.30, 6.30,
                    "CITYNEXUS   -   Smart City Traveler System   (system boundary)",
                    "band", labelSize=8.6)
    p1_nodes, p1_edges = [], []
    xs = [2.46, 4.58, 6.70, 8.82]
    ys = [1.42, 2.66, 3.90, 5.14]
    pos = {}
    for i, (id_, t, st) in enumerate(UC):
        r, c = divmod(i, 4)
        if id_ == "UC-13":
            r, c = 3, 1
        pos[id_] = (xs[c] + 1.00, ys[r] + 0.44)
        p1_nodes.append(node(id_, "usecase", st, "%s  %s" % (id_, t),
                             "use-cases/use-cases.yaml  %s" % id_,
                             {"x": xs[c], "y": ys[r], "w": 2.00, "h": 0.88}))
    p1_nodes.append(node("A Traveler", "actor", "user", "Traveler",
                         "use-cases.yaml:13 ACT-TRAVELER",
                         {"x": 0.56, "y": 2.70, "w": 1.30, "h": 1.14}))
    p1_nodes.append(node("A Admin", "actor", "user", "Administrator",
                         "use-cases.yaml:17 ACTOR-ADMIN",
                         {"x": 0.56, "y": 5.10, "w": 1.30, "h": 1.14}))
    p1_nodes.append(node("A Ctx", "actor", "built", "Context Event Provider",
                         "use-cases.yaml:45 ACT-CONTEXT",
                         {"x": 11.06, "y": 3.60, "w": 1.30, "h": 1.14}))
    EXT = [("A Auth", "Authentication Service", 1.02), ("A AI", "AI Provider", 1.98),
           ("A City", "City Data Provider", 2.94), ("A Mob", "Mobility Provider", 3.90),
           ("A Book", "Booking Provider", 4.86), ("A Pay", "Payment Gateway", 5.82)]
    for id_, t, y in EXT:
        p1_nodes.append(node(id_, "rect", "external", t, "use-cases.yaml:21-41",
                             {"x": 12.74, "y": y, "w": 1.60, "h": 0.78}))
    assoc = {
        "A Traveler": ["UC-01", "UC-02", "UC-03", "UC-04", "UC-05", "UC-06", "UC-07",
                       "UC-08", "UC-10", "UC-11", "UC-12"],
        "A Admin": ["UC-13"],
        "A Ctx": ["UC-09"],
        "A Auth": ["UC-01", "UC-07"],
        "A AI": ["UC-01", "UC-02", "UC-05", "UC-10", "UC-11"],
        "A City": ["UC-04", "UC-05", "UC-10"],
        "A Mob": ["UC-04", "UC-08", "UC-10"],
        "A Book": ["UC-03", "UC-06"],
        "A Pay": ["UC-03", "UC-07"],
    }
    for a, targets in assoc.items():
        for t in targets:
            p1_edges.append(edge(a, t, "", state[t], kind="assoc", endArrow="0",
                                 arrowSize="0",
                                 src="use-cases.yaml primaryActor / supportingActors"))
    for src_, dst_, cond in (("UC-07", "UC-06", "extend [payment required]"),
                             ("UC-09", "UC-08", "extend [event detected]"),
                             ("UC-10", "UC-09", "extend [replan required]")):
        p1_edges.append(edge(src_, dst_, cond, "planned" if src_ == "UC-07" else "built",
                             kind="extend", labelSize=6.0,
                             src="use-cases.yaml:17 relationships type=extend"))

    sheet1 = {
        "name": "Use Case Overview",
        "subtitle": ("Page 1 of 2 - the scope in one readable picture: 13 business use cases and the nine actors the "
                     "specification names. The «include» decomposition is on page 2 so this page stays legible."),
        "nodes": p1_nodes, "edges": p1_edges, "bands": [boundary],
        "legend": [
            {"state": "verified", "text": "Implemented + evidence"},
            {"state": "built", "text": "Implemented, not proven on the line"},
            {"state": "planned", "text": "Specified, no real implementation"},
            {"state": "user", "text": "Human actor"},
            {"state": "external", "text": "<<external system>>"},
        ],
        "legendOrigin": (0.46, 7.44),
        "notes": [
            "Source: use-cases/use-cases.yaml v0.1.0, status baseline-candidate. 13 top-level use cases, 9 actors, 17 relationships (14 include, 3 extend). Every arrow on this page is one of those relationships or a primary/supporting actor link listed against a use case.",
            "UC-07 Make Secure Payment is dashed because no real payment instrument is registered: the code ships mock-payment only and AGENT_TOOL_CATALOG.md:16-18 says capture and refund are not registered.",
            "The internal planning solver is deliberately not an actor (use-cases.yaml modelNotes), and the AI provider may suggest or explain but never owns feasibility or persistence authority.",
            "All requirements are still status proposed: the customer agreement the coursework asks for is separate, so this is a baseline candidate, not approved scope.",
        ],
        "notesOrigin": (0.46, 9.30),
        "notesWidth": 11.9,
        "notesSize": 6.6,
    }

    # ---------------- page 2: included detail
    p2_nodes, p2_edges = [], []
    clusters = [
        ("UC-04", "Generate and Select Journey Plan",
         [("UC-04.1", "Retrieve City Data"), ("UC-04.2", "Build Planning Constraints"),
          ("UC-04.3", "Generate Candidate Plans"), ("UC-04.4", "Validate and Score Plans")]),
        ("UC-05", "Discover and Recommend City Services",
         [("UC-05.1", "Retrieve Real Places"), ("UC-05.2", "Apply Context Constraints"),
          ("UC-05.3", "Rank Candidates"), ("UC-05.4", "Explain Recommendation")]),
        ("UC-10", "Replan Disrupted Journey",
         [("UC-10.1", "Analyse Impact"), ("UC-10.2", "Determine Replan Scope"),
          ("UC-10.3", "Generate Legal Plans"), ("UC-10.4", "Score Candidate Plans"),
          ("UC-10.5", "Compare Plan Versions"), ("UC-10.6", "Explain Replanning")]),
    ]
    for ci, (parent, ptitle, items) in enumerate(clusters):
        cx = 0.50 + ci * 5.32
        p2_nodes.append(band(cx - 0.08, 1.06, 5.10, 6.10,
                             "%s  %s   -   included capability" % (parent, ptitle),
                             "band", labelSize=8.0) | {"isBand": True})
        p2_nodes.append(node(parent, "usecase", state[parent], "%s  %s" % (parent, ptitle),
                             "use-cases.yaml %s" % parent,
                             {"x": cx + 1.05, "y": 1.52, "w": 2.90, "h": 0.86}))
        for k, (sid, name) in enumerate(items):
            col, rr = k % 2, k // 2
            p2_nodes.append(node("sub_" + sid, "usecase", "built",
                                 "%s  %s" % (sid, name),
                                 "use-cases.yaml detailUseCases of %s" % parent,
                                 {"x": round(cx + 0.10 + col * 2.50, 3),
                                  "y": round(2.86 + rr * 1.06, 3), "w": 2.36, "h": 0.86}))
            p2_edges.append(edge(parent, "sub_" + sid, "include", "built", kind="include",
                                 labelSize=6.0,
                                 src="use-cases.yaml:17 relationships type=include"))
    # bands must go in the bands list, not the node list
    p2_bands = [x for x in p2_nodes if x.get("isBand")]
    for x in p2_bands:
        x.pop("isBand", None)
    p2_nodes = [x for x in p2_nodes if "label" not in x]

    sheet2 = {
        "name": "Included Detail",
        "subtitle": ("Page 2 of 2 - the fourteen «include» relationships from use-cases.yaml, grouped under the three "
                     "use cases whose decomposition is part of the Part 2 documentation scope. Keeping them off page 1 "
                     "is what makes page 1 readable."),
        "nodes": p2_nodes, "edges": p2_edges, "bands": p2_bands,
        "legend": [{"state": "verified", "text": "Parent use case, implemented"},
                   {"state": "built", "text": "Included sub-use case"}],
        "legendOrigin": (0.46, 7.40),
        "notes": [
            "These fourteen are documentation-scope detail, not extra business scope: use-cases.yaml modelNotes says UC-04.x, UC-05.x and UC-10.x are focused Part 2 detail use cases used for UML detail.",
            "Each arrow is one of the 14 include entries in the relationships block of the same file, so the count on this page is checkable against the YAML.",
        ],
        "notesOrigin": (0.46, 8.60),
        "notesWidth": 15.6,
        "notesSize": 6.6,
    }

    common["sheets"] = [sheet1, sheet2]
    common["edgeRule"] = "none"
    return common


ALL = [spec_architecture, spec_user_journey, spec_agent_workflow, spec_use_case]

if __name__ == "__main__":
    import json
    import os
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "specs"),
                exist_ok=True)
    for f in ALL:
        s = f()
        print(s["file"], "nodes=%d edges=%d bands=%d" % (len(s["nodes"]), len(s["edges"]),
                                                        len(s["bands"])))
        json.dump(s, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "specs",
                                       os.path.splitext(s["file"])[0] + ".json"),
                          "w", encoding="utf-8"), indent=1, ensure_ascii=False)
