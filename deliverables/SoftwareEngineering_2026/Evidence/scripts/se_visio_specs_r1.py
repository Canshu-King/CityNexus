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


REVISION = "Rev A · generated 2026-10-22 · source tree D:\\moodle\\CityNexus @ review/boli-party-occupancy-scope-r1"

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
        "Mission, plan, tool loop" + chr(10) + "compile_mission, build_mission_plan, run(max_steps=12); DeepSeekJourneyAgent",
        "agent/mission.py:231,384 ; mission_plan.py:74 ; runtime.py:62,336", 1, 1, R4Y + 0.40, 0.90)
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
        "Journey truth" + chr(10) + "journeys, plan_versions, activities, commitments, events, journey_twins, replan_proposals",
        "models.py:175, 511, 535, 578, 712, 761, 782", 4, 1, R5Y + 0.44, 0.90)
    put("db_agent", "database", "data",
        "Agent state and audit" + chr(10) + "journey_missions, agent_runs, agent_run_steps, action_approvals, audit_logs, idempotency_keys",
        "models.py:212, 254, 271, 692, 562, 677", 5, 1, R5Y + 0.44, 0.90)

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
        "agent/gateway.py:338-347 ; tool_catalog.py:20-22", "L4", 7)

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
        "legendOrigin": (12.62, 1.02),
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
ACOLS = 9
ACW = 11.88 / ACOLS
AROWS = [1.02, 1.96, 2.90, 3.84, 4.78, 5.72]


def spec_agent_workflow():
    nodes, edges = [], []

    def put(id_, kind, state, text, src, col, row, role=None, h=0.82):
        bw = ACW - 0.13
        geom = {"x": round(0.46 + col * ACW + (ACW - bw) / 2.0, 3),
                "y": round(AROWS[row] + 0.30, 3), "w": round(bw, 3), "h": h}
        d = node(id_, kind, state, text, src, geom)
        if role:
            d["role"] = role
        nodes.append(d)

    put("a_start", "terminator", "agent", "A request arrives",
        "main.py:14169, 1367", 0, 0, role="start")
    put("a_ctx", "process", "verified", "Trusted context assembled",
        "main.py:13593 _copilot_context()", 1, 0)
    put("a_avail", "decision", "verified", "AI up?",
        "config.py:14 ai_enabled ; agent/ai_availability.py", 2, 0)
    put("a_int", "process", "verified", "Classify into one of 8 intents",
        "main.py:14190-14228", 3, 0)
    put("a_env", "process", "verified", "Semantic envelope and policy",
        "ai/semantic_compiler.py:123, 229", 4, 0)
    put("a_mis", "process", "verified", "JourneyMission persisted",
        "agent/mission.py:231, 384", 5, 0)
    put("a_step", "process", "verified", "AgentRun opened",
        "agent/runtime.py:238 ; models.py:254", 6, 0)
    put("a_budget", "decision", "verified", "Step < 12?",
        "agent/runtime.py:336 run(max_steps=12)", 7, 0)
    put("a_def", "process", "verified", "Tool catalogue offered",
        "agent/runtime.py:62", 8, 0)

    put("a_choice", "decision", "verified", "Model wants a tool?",
        "agent/runtime.py:395-420", 8, 1)
    put("a_gw", "process", "verified", "gateway.dispatch(name, request)",
        "agent/gateway.py:357", 7, 1)
    put("a_allow", "decision", "verified", "On allowlist?",
        "agent/gateway.py:358", 6, 1)
    put("a_deny", "process", "verified", "Refused 404, still audited",
        "gateway.py:359, 377-393", 5, 1)
    put("a_idem", "process", "verified", "Idempotent: repeat the receipt",
        "gateway.py:59, 71 ; models.py:677", 4, 1)
    put("a_auth", "decision", "verified", "Authorization",
        "gateway.py:338-347", 3, 1)
    put("a_kind", "decision", "verified", "Read / plan / money / C4?",
        "tool_catalog.py:20-22", 2, 1)
    put("a_fall", "process", "built", "Deterministic fallback, no model turn",
        "main.py:13722 ; ai_availability.py", 1, 1)

    put("a_result", "process", "verified", "Result analysed and stored",
        "agent/runtime.py:238", 5, 2)
    put("a_exec", "process", "verified", "Handler runs against domain services",
        "agent/gateway.py:400+", 4, 2)
    put("a_confirm", "process", "built", "Held for your confirmation",
        "gateway.py:343 ; main.py:2081", 3, 2)
    put("a_fail", "decision", "verified", "Provider failed?",
        "agent/runtime.py:660", 6, 2)
    put("a_degrade", "process", "verified", "Degraded run recorded",
        "runtime.py:660 ; AGENT_RUNTIME_ARCHITECTURE.md:12-15", 7, 2)

    put("a_prop", "process", "verified", "Replan proposal produced",
        "main.py:10923 ; models.py:782", 5, 3)
    put("a_show", "process", "verified", "Shown in the feed and the rail",
        "main.py:10125, 1099, 2032", 4, 3)
    put("a_fb", "rect", "user", "You accept, reject, or keep talking",
        "main.py:13097, 13569", 3, 3)
    put("a_more", "decision", "verified", "More work?",
        "agent/runtime.py:336", 2, 3)
    put("a_stop", "terminator", "agent", "Run closed and readable",
        "main.py:929, 1099", 1, 3, role="end")

    nodes.append(node("t_list", "rect", "verified",
                      "THE 11 TOOLS THIS BUILD EXPOSES   tool_catalog.py:26-59" + chr(10)
                      + "read-only: inspect_journey, inspect_twin, list_replans, search_city_services" + chr(10)
                      + "plan-shaping: request_replan, accept_replan" + chr(10)
                      + "typed actions: replace_activity, reschedule_activity, create_booking, cancel_refundable_booking, request_commitment_change" + chr(10)
                      + "MCP surfaces: V1 six tools (server.py:157-207), V2 eleven (server.py:404-549)",
                      "tool_catalog.py:26-59",
                      {"x": 12.52, "y": 1.32, "w": 3.62, "h": 2.60}, size=6.4))
    nodes[-1]["role"] = "note"
    nodes.append(node("not_list", "rect", "planned",
                      "WHAT IS STILL MISSING" + chr(10)
                      + "native Hermes binary absent, runtime identity still DIRECT (BLOCKERS.md:9-12)" + chr(10)
                      + "live Valhalla URL not configured, so the travel matrix stays mocked (BLOCKERS.md:13-14)" + chr(10)
                      + "no real payment or refund instrument registered (AGENT_TOOL_CATALOG.md:16-18)" + chr(10)
                      + "impact resolver default disabled (config.py:33)" + chr(10)
                      + "physical phone and PWA shadow trial not performed (CURRENT_STATUS.md:4)",
                      "BLOCKERS.md:9-16 ; AGENT_TOOL_CATALOG.md:16-18",
                      {"x": 12.52, "y": 4.10, "w": 3.62, "h": 2.60}, size=6.4))
    nodes[-1]["role"] = "note"

    edges = [
        edge("a_start", "a_ctx", "", "agent"),
        edge("a_ctx", "a_avail", "", "verified"),
        edge("a_avail", "a_int", "YES", "verified"),
        edge("a_avail", "a_fall", "NO", "built"),
        edge("a_fall", "a_show", "plain answer", "built"),
        edge("a_int", "a_env", "", "verified"),
        edge("a_env", "a_mis", "", "verified"),
        edge("a_mis", "a_step", "", "verified"),
        edge("a_step", "a_budget", "", "verified"),
        edge("a_budget", "a_def", "YES", "verified"),
        edge("a_budget", "a_degrade", "NO, budget spent", "verified"),
        edge("a_def", "a_choice", "", "verified"),
        edge("a_choice", "a_gw", "YES", "verified"),
        edge("a_choice", "a_result", "NO, final answer", "verified"),
        edge("a_gw", "a_allow", "", "verified"),
        edge("a_allow", "a_idem", "YES", "verified"),
        edge("a_allow", "a_deny", "NO", "verified"),
        edge("a_deny", "a_result", "refusal recorded", "verified"),
        edge("a_idem", "a_auth", "", "verified"),
        edge("a_auth", "a_kind", "ALLOW_AUTO", "verified"),
        edge("a_auth", "a_confirm", "REQUIRE_CONFIRMATION", "built"),
        edge("a_auth", "a_deny", "DENY", "verified"),
        edge("a_kind", "a_exec", "read or plan", "verified"),
        edge("a_kind", "a_confirm", "money or C4", "built"),
        edge("a_confirm", "a_exec", "after you approve", "built"),
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
    ]

    bands = [band(0.40, 0.94, 12.10, 1.02, "REQUEST, INTENT AND THE STEP BUDGET", "laneband",
                  dash="2", labelSize=8.0),
             band(0.40, 1.88, 12.10, 1.02, "THE GATEWAY DECIDES WHAT AN AGENT MAY DO", "laneband",
                  dash="2", labelSize=8.0),
             band(0.40, 2.82, 12.10, 1.02, "EXECUTION, CONFIRMATION AND FAILURE HANDLING", "laneband",
                  dash="2", labelSize=8.0),
             band(0.40, 3.76, 12.10, 1.02, "WHAT COMES BACK TO YOU", "laneband", dash="2",
                  labelSize=8.0),
             band(12.44, 1.24, 3.78, 2.76, "PROVEN CAPABILITY", "band", labelSize=8.0),
             band(12.44, 4.02, 3.78, 2.76, "HONEST GAP LIST", "planned", labelSize=8.0)]

    return {
        "file": "03_CityNexus_Agent_Workflow.vsdx",
        "pageName": "Agent Workflow",
        "edgeRule": "none",
        "title": "CityNexus   |   AI Agent Autonomy and Tool-Calling Workflow",
        "subtitle": ("The path from a sentence to an action, and the three places where the system is allowed to say no. "
                     "Reads are free; plan changes become proposals; anything touching money or a protected commitment "
                     "waits for the traveler. A failed provider is recorded as a degraded run instead of quietly rewriting "
                     "the journey."),
        "docid": "CNX-SE-VIS-03   Agent workflow (tool loop and authorization gates)",
        "revline": REVISION,
        "bodySize": 6.8,
        "subSize": 5.0,
        "bands": bands,
        "nodes": nodes,
        "edges": edges,
        "legend": [
            {"state": "verified", "text": "Implemented + evidence"},
            {"state": "built", "text": "Implemented, not proven on the line"},
            {"state": "planned", "text": "Missing or future work"},
            {"state": "agent", "text": "Agent-owned step"},
            {"state": "user", "text": "Human in the loop"},
        ],
        "legendOrigin": (0.46, 6.90),
        "notes": [
            "WHY THIS IS THE DIAGRAM TO PRESENT: an information page answers a question; this loop is what makes CityNexus an agent application. The model never writes journey state itself - agent/runtime.py:336 asks, agent/gateway.py:357 decides, and a domain service performs.",
            "THREE DOORS, NOT ONE. allowlist (gateway.py:358) then idempotency (gateway.py:59, 71) then authorization (gateway.py:338-347). The PLAN_ONLY boundary is enforced server-side, so a request body claiming to be Hermes cannot widen it.",
            "max_steps=12 is a real bound in runtime.py:336; a run that spends it is reported as degraded, not retried invisibly.",
            "The two panels on the right are part of the model, not decoration: the coursework asks to separate what the code does today from what is planned, and claiming a closed automation loop here would be false.",
        ],
        "notesOrigin": (0.46, 6.20),
        "notesWidth": 11.7,
        "notesSize": 6.8,
    }


# ==========================================================================  04
def spec_use_case():
    nodes, edges, bands = [], [], [
        band(2.24, 0.98, 8.44, 8.14,
             "CITYNEXUS   -   Smart City Traveler System   (system boundary)", "band",
             labelSize=8.6),
    ]

    UC = [("UC-01", "UC-01 Manage Account and Preferences", "verified"),
          ("UC-02", "UC-02 Create and Configure Journey", "verified"),
          ("UC-03", "UC-03 Manage Journey Commitments", "verified"),
          ("UC-04", "UC-04 Generate and Select Journey Plan", "verified"),
          ("UC-05", "UC-05 Discover and Recommend City Services", "verified"),
          ("UC-06", "UC-06 Book and Order City Services", "built"),
          ("UC-07", "UC-07 Make Secure Payment", "planned"),
          ("UC-08", "UC-08 Execute Journey", "verified"),
          ("UC-09", "UC-09 Detect and Assess Journey Events", "built"),
          ("UC-10", "UC-10 Replan Disrupted Journey", "verified"),
          ("UC-11", "UC-11 Use AI Journey Copilot", "verified"),
          ("UC-12", "UC-12 Review Journey History and Changes", "verified"),
          ("UC-13", "UC-13 Administer Platform and Providers", "built")]
    xs = [2.40, 4.52, 6.64, 8.76]
    ys = [1.40, 2.52, 3.64, 4.76]
    for i, (id_, t, st) in enumerate(UC):
        r, c = divmod(i, 4)
        if id_ == "UC-13":
            r, c = 3, 1
        nodes.append(node(id_, "usecase", st, t,
                          "use-cases/use-cases.yaml  %s" % id_,
                          {"x": xs[c], "y": ys[r], "w": 2.00, "h": 0.86}))

    clusters = [("UC-04", [("UC-04.1", "Retrieve City Data"), ("UC-04.2", "Build Planning Constraints"),
                           ("UC-04.3", "Generate Candidate Plans"), ("UC-04.4", "Validate and Score Plans")], 2.40),
                ("UC-05", [("UC-05.1", "Retrieve Real Places"), ("UC-05.2", "Apply Context Constraints"),
                           ("UC-05.3", "Rank Candidates"), ("UC-05.4", "Explain Recommendation")], 4.52),
                ("UC-10", [("UC-10.1", "Analyse Impact"), ("UC-10.2", "Determine Replan Scope"),
                           ("UC-10.3", "Generate Legal Plans"), ("UC-10.4", "Score Candidate Plans"),
                           ("UC-10.5", "Compare Plan Versions"), ("UC-10.6", "Explain Replanning")], 6.64)]
    for parent, items, cx in clusters:
        for k, (sid, name) in enumerate(items):
            col, rr = k % 2, k // 2
            nodes.append(node("sub_" + sid, "usecase", "built",
                              "%s %s" % (sid.replace("UC-", ""), name),
                              "use-cases.yaml detailUseCases of %s" % parent,
                              {"x": round(cx + col * 1.04, 3),
                               "y": round(5.90 + rr * 0.94, 3), "w": 1.02, "h": 0.88}))
            edges.append(edge(parent, "sub_" + sid, "include", "built", kind="include",
                              labelSize=5.6,
                              src="use-cases.yaml:17 relationships type=include"))

    nodes.append(node("A Traveler", "actor", "user", "Traveler",
                      "use-cases.yaml:13 ACT-TRAVELER",
                      {"x": 0.52, "y": 2.40, "w": 1.30, "h": 1.10}))
    nodes.append(node("A Admin", "actor", "user", "Administrator",
                      "use-cases.yaml:17 ACT-ADMIN",
                      {"x": 0.52, "y": 6.80, "w": 1.30, "h": 1.10}))
    nodes.append(node("A Ctx", "actor", "built", "Context Event Provider",
                      "use-cases.yaml:45 ACT-CONTEXT, primary of UC-09",
                      {"x": 11.02, "y": 6.80, "w": 1.30, "h": 1.10}))

    ext = [("A Auth", "Authentication Service", 1.06), ("A AI", "AI Provider", 1.92),
           ("A City", "City Data Provider", 2.78), ("A Mob", "Mobility Provider", 3.64),
           ("A Book", "Booking Provider", 4.46), ("A Pay", "Payment Gateway", 5.32)]
    for id_, t, y in ext:
        nodes.append(node(id_, "rect", "external", t, "use-cases.yaml:21-41",
                          {"x": 12.72, "y": y, "w": 1.62, "h": 0.72}))

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
            st = "verified"
            for id_, _tt, s2 in UC:
                if id_ == t:
                    st = s2
            edges.append(edge(a, t, "", st, kind="assoc", endArrow="0", arrowSize="0",
                              src="use-cases.yaml primaryActor / supportingActors"))
    for src_, dst_, cond in (("UC-07", "UC-06", "extend [payment required]"),
                             ("UC-09", "UC-08", "extend [event detected]"),
                             ("UC-10", "UC-09", "extend [replan required]")):
        edges.append(edge(src_, dst_, cond, "planned" if src_ == "UC-07" else "built",
                          kind="extend", labelSize=5.8,
                          src="use-cases.yaml:17 relationships type=extend"))

    return {
        "file": "04_CityNexus_Use_Case.vsdx",
        "pageName": "Use Case Diagram",
        "edgeRule": "none",
        "title": "CityNexus   |   UML Use Case Model",
        "subtitle": ("Thirteen top-level business use cases with exactly the actors the specification names: one traveler, "
                     "one administrator, one event source and six external systems. Included detail is drawn for the three "
                     "use cases whose decomposition is part of the Part 2 documentation scope; extend arrows point at the "
                     "base use case, as UML requires."),
        "docid": "CNX-SE-VIS-04   UML use case diagram",
        "revline": REVISION,
        "bodySize": 6.8,
        "subSize": 5.0,
        "bands": bands,
        "nodes": nodes,
        "edges": edges,
        "legend": [
            {"state": "verified", "text": "Use case implemented + evidence"},
            {"state": "built", "text": "Implemented, not proven on the line"},
            {"state": "planned", "text": "Specified, no real implementation"},
            {"state": "user", "text": "Human actor"},
            {"state": "external", "text": "<<external system>>"},
        ],
        "legendOrigin": (12.62, 1.02),
        "notes": [
            "SOURCE OF EVERY NAME AND ARROW: use-cases/use-cases.yaml version 0.1.0, status baseline-candidate - 13 top-level use cases, 14 detail use cases, 9 actors, 17 relationships (14 include and 3 extend). Nothing here is invented for the picture.",
            "UC-07 Make Secure Payment is drawn dashed on purpose. The requirement baseline contains it, but no real payment instrument is registered: the code ships mock-payment only and AGENT_TOOL_CATALOG.md:16-18 states that payment capture and refund are not registered.",
            "The internal planning solver is deliberately not an actor (use-cases.yaml modelNotes), and the AI provider may suggest, extract or explain but never owns feasibility or persistence authority.",
            "All requirements are still status proposed: the customer agreement the coursework asks for is a separate deliverable, so this model is a baseline candidate rather than an approved scope.",
        ],
        "notesOrigin": (0.46, 8.62),
        "notesWidth": 11.7,
        "notesSize": 6.8,
    }


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
