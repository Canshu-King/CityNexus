"""CityNexus coursework project plan, revision 2 - the data behind the .mpp.

Revision 1 was rejected by the independent review on dependency semantics, and
the rework in this file is what that criticism asks for. The three clocks are
now modelled with three different mechanisms instead of being smeared together:

  HISTORICAL FACT   a row's `pct` (only ever a number the evidence supports) plus
                    `obs`, the date the repository or a dated document actually
                    records. Project books the completed part itself once a
                    percentage is entered; nothing is typed into a date field.
  DEPENDENCY        the only thing that moves a date. Every row is auto scheduled
                    with ConstraintType "As Soon As Possible" and no start is
                    forced anywhere, so the schedule is a consequence of the
                    links rather than a transcription of the calendar.
  CONTRACT DATE     the `deadline` field, which Project displays but does not
                    obey. The two coursework deadlines and the system-test target
                    live here. A scheduled finish past a deadline is reported by
                    the checker as a breach, and the only breach in this plan is
                    the one that really happened: Part 1 on 2026-10-02.

Two clocks are visible on purpose. The repository has commits from 2026-09-05 and
from 2026-09-19 onward, and nothing in between, while several documents carry
author dates (2026-09-12, 09-13, 09-15, 09-23) that predate the commit that
contains them. `obs.basis` names which clock each observation comes from,
so a reader can see the difference instead of finding an unexplained mismatch.

Durations, hours and owners are estimates: `units` is the share of a person's time
the plan allocates, and Work in the .mpp is derived from duration x units x 8h by
Microsoft Project itself, so cost always corresponds to hours.
"""

# kind: "sum" summary | "task" leaf | "ms" milestone (zero duration)
# links: "KEY + FS|SS|FF";  assign: [(resource key, units)];  obs: observed date
# ev: the evidence line that goes into the task's Notes field.

PLAN = [
    # ------------------------------------------------------------ 1 initiation
    dict(kind="sum", name="1  Coursework initiation and project selection"),
    dict(kind="task", name="1.1  Read the assignment brief and fix the deliverable scope",
         dur="1d", pct=100, units=1.0, assign=[],
         links=[],
         obs=dict(date="2026-10-22", basis="this reading",
                  cite="Software Engineering - Assignment Coursework 2026.pdf read in "
                       "full: Part 1 50% (10 slides, no later than midnight Friday "
                       "2026-10-02), Part 2 50% (project plan + full SRS, no later than "
                       "midnight Friday 2026-11-06)"),
         ev="Brief PDF read in full on 2026-10-22; both weights, both dates and the "
            "ten-slide limit are quoted from it."),
    dict(kind="task", name="1.2  Select the project: smart city traveler system",
         dur="1d", pct=100, units=1.0, assign=[], links=["1.1FS"],
         obs=dict(date="2026-09-05", basis="commit",
                  cite="096d857a4f 2026-09-05T01:07:10+0800 chore(domain): freeze "
                       "CityNexus domain model v0.4.1 RC2 - first commit on any ref"),
         ev="Brief item 11 'A smart city traveler system'; use-cases.yaml metadata "
            "officialProject = Smart City Traveler System; the repository opens the "
            "same night with the domain model and requirements baseline."),
    dict(kind="task", name="1.3  Confirm the group of three and each member's responsibility",
         dur="2d", pct=100, units=1.5, links=["1.2SS"],
         assign=[],
         obs=dict(date="2026-10-22", basis="stated by the project owner",
                  cite="Yang Jianbin 0802240329, Wang Jiarui 0802240322, Wang Xinyue "
                       "0802240324 - named to this build on 2026-10-22"),
         ev="MEMBERSHIP IS EVIDENCED BY THE OWNER'S STATEMENT, NOT BY THE REPOSITORY: "
            "every commit on the reviewed branch is under one identity "
            "(Canshu-King / yjianbin419), because the automation lanes committed "
            "through the owner's account. The split below is the plan's proposal for "
            "the report, not a measured history."),

    dict(kind="ms", pct=100, name="M1  Topic and scope agreed", links=["1.2FS"],
         obs=dict(date="2026-09-05", basis="commit",
                  cite="first commit on any ref: 096d857a4f 2026-09-05T01:07:10+0800"),
         ev="Repository opens 2026-09-05 with the domain model release candidate and "
            "the requirements baseline, five commits that day."),

    # ------------------------------------------------------ 2 requirements
    dict(kind="sum", name="2  Requirements engineering"),
    dict(kind="task", name="2.1  Research the software needed, library and online",
         dur="4d", pct=100, units=1.0, assign=[], links=["M1FS"],
         ev="requirements.yaml sources field cites ARCH/LIB/WEB across 138 entries; "
            "the coursework reading pack sits in '02 Software Engineering/'."),
    dict(kind="task", name="2.2  Write the requirement baseline: 8 goals, 61 functional, 24 rules, 16 NFR, 14 security, 15 integration",
         dur="5d", pct=100, units=1.0, links=["2.1SS"], assign=[],
         obs=dict(date="2026-09-05", basis="commit",
                  cite="072e84f0bd 2026-09-05T02:02:39+0800 feat(requirements): "
                       "establish CityNexus requirements baseline v0.3"),
         ev="requirements/requirements.yaml v0.3.0 counted on 2026-10-22: 8 + 61 + 24 "
            "+ 16 + 14 + 15 = 138 entries, each with acceptance criteria and "
            "traceability. First committed 2026-09-05; the coursework gap analysis "
            "carrying the 2026-09-12 date is a document date, not a commit date."),
    dict(kind="task", name="2.3  Domain model and use case specification",
         dur="4d", pct=100, units=1.0, links=["2.2SS"], assign=[],
         obs=dict(date="2026-09-05", basis="commit", cite="d5236d9022 domain model "
                  "v0.4.2 RC3 2026-09-05T02:02:32+0800"),
         ev="domain-model/citynexus-core-domain-model-v0.4.2.yaml; use-cases/"
            "use-cases.yaml v0.1.0: 13 top-level use cases, 14 detail use cases, "
            "9 actors, 17 relationships."),
    dict(kind="ms", pct=100, name="M2  Requirements baseline drafted", links=["2.2FS", "2.3FS"],
         obs=dict(date="2026-09-12", basis="document",
                  cite="requirements baseline 0.3.0 and the coursework gap analysis "
                       "both carry 2026-09-12 in their own text; the commits that "
                       "contain them are dated 2026-09-19 or later"),
         ev="Two clocks: the documents say 2026-09-12, the repository first holds them "
            "on 2026-09-19. The baseline itself was committed 2026-09-05."),
    dict(kind="task", name="2.4  Get the requirement baseline agreed with the teacher as customer",
         dur="3d", pct=0, units=0.5, links=["M11FS"], assign=[],
         tentative=True,
         ev="NOT DONE AS OF THE STATUS DATE and re-planned into the remaining window: "
            "every requirement and use case still carries status baseline-candidate / "
            "proposed, and requirements/README.md states the teacher-customer has not "
            "approved the baseline. Left at 0% rather than back-dated."),

    # ------------------------------------------------------ 3 design
    dict(kind="sum", name="3  System design and architecture"),
    dict(kind="task", name="3.1  Layered architecture and agent runtime design",
         dur="5d", pct=100, units=1.0, links=["M2FS"], assign=[],
         obs=dict(date="2026-09-15", basis="document",
                  cite="CURRENT_STATUS.md dated 2026-09-15 closes the V19.2.1 design "
                       "round; AGENT_RUNTIME_ARCHITECTURE.md first appears in git on "
                       "2026-09-19 and is still changing on 2026-10-20"),
         ev="AGENT_RUNTIME_ARCHITECTURE.md (V3) and contracts/AGENT_RUNTIME_"
            "ARCHITECTURE.md; the file keeps being revised through the whole build, "
            "so this row is the first design round, not a one-off document."),
    dict(kind="task", name="3.2  Interface contracts: OpenAPI and tool catalogues",
         dur="4d", pct=100, units=1.0, links=["3.1SS"], assign=[],
         obs=dict(date="2026-09-19", basis="commit", cite="contracts/ first commit "
                  "2026-09-19, last 2026-10-21"),
         ev="contracts/openapi.yaml; AGENT_TOOL_CATALOG.md; backend/app/agent/"
            "tool_catalog.py:26-59."),
    dict(kind="task", name="3.3  Microsoft Visio system model for the report",
         dur="4d", pct=100, units=1.0, links=["3.2SS"],
         assign=[],
         obs=dict(date="2026-10-22", basis="this build",
                  cite="the four .vsdx in deliverables/SoftwareEngineering_2026/Visio, "
                       "generated and proved on 2026-10-22"),
         ev="visio/CityNexus_Visio_Model_Baseline_v1.0.4_RC5.vsdx in git (first commit "
            "2026-09-19) plus the four drawings and their proof run by this build on "
            "2026-10-22: 148 connectors glued, 579 shape-data values read back."),

    dict(kind="ms", pct=100, name="M3  Architecture design complete", links=["3.1FS", "3.2FS", "3.3FS"],
         obs=dict(date="2026-09-15", basis="document", cite="CURRENT_STATUS.md 2026-09-15"),
         ev="Design round closed by document date; contracts and drawings kept "
            "evolving afterwards, which this plan shows by leaving those rows open."),

    # ------------------------------------------------------ 4 backend
    dict(kind="sum", name="4  Backend platform and data layer"),
    dict(kind="task", name="4.1  FastAPI service and the /api/v1 surface",
         dur="10d", pct=100, units=1.0, links=["3.1SS"], assign=[],
         obs=dict(date="2026-09-19", basis="commit",
                  cite="backend/app/main.py 2026-09-19 .. 2026-10-22, 526 commits"),
         ev="backend/app/main.py: 175 @app decorators counted 2026-10-22, 14,569 lines."),
    dict(kind="task", name="4.2  SQLAlchemy schema, 60 tables, idempotency and audit",
         dur="8d", pct=100, units=1.0, links=["4.1SS"], assign=[],
         obs=dict(date="2026-09-19", basis="commit", cite="backend/app/db/models.py "
                  "2026-09-19 .. 2026-10-20, 116 commits"),
         ev="backend/app/db/models.py: 60 __tablename__ declarations; idempotency_keys "
            "models.py:677; audit_logs models.py:562."),
    dict(kind="task", name="4.3  Journey lifecycle, plan generation and replanning",
         dur="12d", pct=100, units=1.0, links=["4.1SS"], assign=[],
         obs=dict(date="2026-09-19", basis="commit", cite="backend/app/replanning "
                  "2026-09-19 .. 2026-10-22, 42 commits"),
         ev="main.py:3136, 7369, 7790, 10923, 13097, 13569; backend/app/replanning; "
            "tests under backend/tests."),
    dict(kind="task", name="4.4  Twin, capability and preference scopes",
         dur="6d", pct=100, units=1.0, links=["4.2FS"], assign=[],
         ev="main.py:9846, 2761, 2568; models.py:95, 121; ORD-0355 keeps stay budget "
            "declared rather than invented (models.py:824)."),
    dict(kind="task", name="4.5  Commerce, guardian and autopilot",
         dur="14d", pct=40, units=1.0, links=["4.4FS"], assign=[],
         ev="PARTIAL: endpoints exist (main.py:14404, 1599, 1772) but payment is "
            "mock-payment only and the impact resolver defaults to disabled "
            "(config.py:33); BUG_REPORT_20260913 still lists four P0 items."),
    dict(kind="ms", pct=100, name="M4  Core backend running end to end", links=["4.3FS", "4.4FS"],
         obs=dict(date="2026-09-13", basis="document",
                  cite="PROJECT_STATUS_SNAPSHOT_20260913.md: 344 passed / 2 skipped of "
                       "346 backend tests at that point; the file's first commit is "
                       "2026-09-19"),
         ev="The snapshot reports a green backend suite on 2026-09-13 by its own date. "
            "The repository cannot corroborate that date because no commit exists "
            "between 2026-09-05 and 2026-09-19, so this milestone is link-driven and "
            "the observation is recorded separately."),

    # ------------------------------------------------------ 5 providers
    dict(kind="sum", name="5  Map and place data integration"),
    dict(kind="task", name="5.1  Geocoding and POI: Photon, Nominatim, Overpass",
         dur="5d", pct=100, units=1.0, links=["4.1SS"], assign=[],
         ev="integrations/discovery/photon.py:20-27; discovery/real_city.py:617, "
            "684-688 with three Overpass mirrors."),
    dict(kind="task", name="5.2  Context providers: Open-Meteo weather and time",
         dur="3d", pct=70, units=1.0, links=["5.1SS"], assign=[],
         ev="integrations/context/open_meteo.py:29-36 wired; the provider is off "
            "unless opted in, so it is not counted as proven."),
    dict(kind="task", name="5.3  Mobility: Valhalla routing behind a live URL",
         dur="4d", pct=0, units=1.0, links=["5.2SS"], assign=[],
         tentative=True,
         ev="NOT WORKING: BLOCKERS.md:13-14 records live Valhalla as skipped because no "
            "URL is configured; the travel matrix stays mocked. Kept at 0% and inside "
            "the window it was planned for, so the lateness stays visible."),
    dict(kind="task", name="5.4  Deterministic mock provider set as the shipped default",
         dur="4d", pct=100, units=1.0, links=["5.1FS"], assign=[],
         ev=".env.example:18-31 and integrations/mock/providers.py:13; config.py:79-81 "
            "keeps real-city mode at replay."),
    dict(kind="ms", pct=100, name="M5  Provider mesh integrated behind one interface",
         links=["5.2FS", "5.4FS"],
         obs=dict(date="2026-09-21", basis="commit",
                  cite="discovery/provider_identity.py:34 records the 2026-09-21 "
                       "measured provider behaviour"),
         ev="Measured provider identities recorded in the tree on 2026-09-21."),

    # ------------------------------------------------------ 6 agent
    dict(kind="sum", name="6  AI agent and Hermes capability"),
    dict(kind="task", name="6.1  Intent classification and trusted context assembly",
         dur="5d", pct=100, units=1.0, links=["4.3SS"], assign=[],
         ev="main.py:14190-14228 (8 intents) and main.py:13593 _copilot_context()."),
    dict(kind="task", name="6.2  Mission compile, mission plan and the twelve-step tool loop",
         dur="6d", pct=100, units=1.0, links=["6.1FS"],
         assign=[("qoder", 1.0)],
         ev="agent/mission.py:231, 384; mission_plan.py:74; runtime.py:62, 336 "
            "run(max_steps=12)."),
    dict(kind="task", name="6.3  Tool gateway: allowlist, audit, idempotency, authorization",
         dur="5d", pct=100, units=1.0, links=["6.2SS"], assign=[],
         obs=dict(date="2026-09-19", basis="commit", cite="backend/app/agent/gateway.py "
                  "2026-09-19 .. 2026-10-20, 103 commits"),
         ev="agent/gateway.py:357-398, 59, 71, 338-347; approval boundary main.py:2081. "
            "The order the code actually runs is what diagram 03 now draws: allowlist "
            "test at :358, 404 raise at :359, record_audit at :377."),
    dict(kind="task", name="6.4  Eleven tools and the MCP V1 / V2 surfaces",
         dur="4d", pct=100, units=1.0, links=["6.3FS"], assign=[],
         ev="tool_catalog.py:26-59; agent-mcp/citynexus_mcp/server.py:128 (V1 six) and "
            ":378 (V2 eleven); agent-mcp/tests."),
    dict(kind="task", name="6.5  Native Hermes runtime",
         dur="6d", pct=20, units=1.0, links=["6.4SS"], assign=[("codex", 1.0)],
         ev="PARTIAL AND UNPROVEN: integrations/hermes/native_client.py:34, 71, 132, 158 "
            "exist and the protocol surface is complete, but BLOCKERS.md:9-12 states the "
            "Hermes binary is not installed here and runtime identity is still DIRECT."),
    dict(kind="ms", pct=100, name="M6  Agent surface proven against a live model", links=["6.4FS"],
         obs=dict(date="2026-09-23", basis="document",
                  cite="HERMES_INTEGRATION_STATUS.md and the Hermes R4/R5 packages dated "
                       "2026-09-23"),
         ev="The Hermes status documents carry 2026-09-23; the repository holds them "
            "from 2026-09-19 onward."),

    # ------------------------------------------------------ 7 frontend
    dict(kind="sum", name="7  Frontend UI and interaction"),
    dict(kind="task", name="7.1  V8Experience shell and the fifteen routed panels",
         dur="8d", pct=100, units=1.0, links=["4.1SS"], assign=[],
         obs=dict(date="2026-09-19", basis="commit",
                  cite="frontend/src/app/V8Experience.tsx 2026-09-19 .. 2026-10-22, "
                       "342 commits"),
         ev="frontend/src/app/V8Experience.tsx; routes/v8Routes.ts:1-33."),
    dict(kind="task", name="7.2  MapLibre map, plan comparison and Trip Studio",
         dur="6d", pct=100, units=1.0, links=["7.1SS"], assign=[],
         ev="components/JourneyMap.tsx; features/planning/PlanComparison.tsx; "
            "main.py:10525 route evidence."),
    dict(kind="task", name="7.3  Copilot dock, agent rail, check-ins and collections",
         dur="6d", pct=100, units=1.0, links=["7.2FS"],
         assign=[("qoder", 1.0)],
         ev="features/agent/CopilotDock.tsx, AgentRunRail.tsx; features/checkin/"
            "checkins.ts:14; features/collections/collections.ts:16."),
    dict(kind="ms", pct=100, name="M7  Frontend running against the real backend", links=["7.3FS"],
         obs=dict(date="2026-10-13", basis="document",
                  cite="CityNexus_进度汇报_2026-10-13.md: the demo path was walked on a "
                       "live local backend on 2026-10-13 with two screenshots attached"),
         ev="Progress report of 2026-10-13 with screenshots; the demo path was walked "
            "against a live local backend."),

    # ------------------------------------------------------ 8 integration
    dict(kind="sum", name="8  Integration and consolidation"),
    dict(kind="task", name="8.1  Authoritative integration line and landing gate",
         dur="6d", pct=100, units=1.0, links=["7.2SS"], assign=[],
         obs=dict(date="2026-10-08", basis="commit",
                  cite="the four-leg landing loop first full run 2026-10-08; 40 pending "
                       "branches cleared that day"),
         ev="_qoder_integration_20260919 line and the four-leg landing loop of "
            "2026-10-08; 90 commits landed on the authoritative line on 2026-10-13."),
    dict(kind="task", name="8.2  Backport the frontend onto the current capability contract",
         dur="6d", pct=50, units=1.0, links=["8.1SS"], assign=[("codex", 1.0)],
         ev="PARTIAL: ORD-0245 measured the payload growing from 16 to 26 keys; 11 of 25 "
            "frontend fixes cherry-pick cleanly, 12 sit in files that have diverged."),
    dict(kind="ms", pct=100, name="M8  Integration line stable", links=["8.1FS"],
         obs=dict(date="2026-10-08", basis="commit", cite="landing loop run 2026-10-08"),
         ev="Four-leg landing loop first full run 2026-10-08; 40 pending branches cleared."),

    # ------------------------------------------------------ 9 verification
    dict(kind="sum", name="9  Verification and defect management"),
    dict(kind="task", name="9.1  Backend regression suite",
         dur="20d", pct=85, units=1.0, links=["M8SS"],
         assign=[("qoder", 1.0)],
         ev="242 backend test modules counted 2026-10-22. The 2026-10-13 report measured "
            "1887 passed / 45 failed on the tip: not green, so not 100%."),
    dict(kind="task", name="9.2  Frontend end-to-end suite",
         dur="20d", pct=60, units=1.0, links=["9.1SS"],
         assign=[("qoder", 1.0)],
         ev="184 e2e specs counted 2026-10-22; the authoritative-mode gate needs a "
            "per-run database and a fresh journey seed, which is recorded as a known "
            "limit."),
    dict(kind="task", name="9.3  Close the four P0 defects from the bug report",
         dur="5d", pct=50, units=1.0, links=["9.2SS"], assign=[],
         ev="BUG_REPORT_20260913.md:4 lists P0 x4 and P1 x3; Bug-001 "
            "(MockMobilityProvider on by default) and Bug-002 (ICS all-day timezone) "
            "are still named there."),
    dict(kind="task", name="9.4  Physical phone and PWA shadow trial",
         dur="4d", pct=0, units=1.0, links=["9.3FS"], assign=[],
         tentative=True,
         ev="NOT PERFORMED: CURRENT_STATUS.md:4 says SHADOW_TRIAL_CODE_READY_PENDING_"
            "PHYSICAL_DEVICE and TEST_RESULTS.md:10 records it as not performed."),
    dict(kind="task", name="9.5  Verification evidence pack and defect triage report",
         dur="3d", pct=0, units=1.0, links=["9.1FF", "9.2FF"],
         assign=[],
         ev="PARTIAL AND OPEN: this build writes Evidence/AUTOMATION_VERIFICATION.md "
            "plus the proof-run result files, but the triage report for the four P0 "
            "items in BUG_REPORT_20260913.md is not assembled, so the row stays at 0%. "
            "It is joined Finish-to-Finish to both suites because the pack is complete "
            "when they are, not three days after them."),
    dict(kind="task", name="9.6  Final regression re-run and defect count for the report",
         dur="2d", pct=0, units=1.0, links=["9.4SS"],
         assign=[("qoder", 1.0)],
         tentative=True,
         ev="NOT RUN: the Part 2 report has to quote one final pass/fail count taken "
            "after the shadow trial, and no such run exists yet; the last measured "
            "figure is 1887 passed / 45 failed on the 2026-10-13 tip. It starts with "
            "the shadow trial rather than after it, because the same machine session "
            "covers both."),
    dict(kind="ms", name="M9  System test ready (plan target)", links=["9.4FS", "9.6FS"],
         deadline="2026-11-02", tentative=True,
         ev="PLANNED, not evidenced: the 2026-11-02 target is set so that the Part 2 "
            "deadline on 2026-11-06 still has working days of contingency. It is a "
            "Deadline, not a forced date: Project may schedule this later, and the "
            "checker reports that as a breach."),

    # ------------------------------------------------------ 10 coursework output
    dict(kind="sum", name="10  Coursework deliverables and reporting"),
    dict(kind="task", name="10.1  Part 1: ten-slide report with the Visio model and task allocation",
         dur="5d", pct=0, units=1.5, links=["M3FS"], breach_is_fact=True,
         assign=[],
         deadline="2026-10-02",
         statutory=True,
         ev="SUBMISSION STATE IS NOT VERIFIABLE FROM THIS REPOSITORY. The brief set the "
            "date at midnight Friday 2026-10-02 and no .pptx for it is in the tree this "
            "side of that date, which does not prove it was never uploaded to the "
            "course platform - it proves only that the repository cannot show it. To be "
            "confirmed against the Moodle/course record, then the percentage set. "
            "Recorded at 0% rather than back-dated."),
    dict(kind="task", name="10.2  Mid-term review pack: architecture, journey, agent loop, use cases",
         dur="11d", pct=70, units=1.5, links=["M7FS"],
         assign=[],
         ev="The four Visio drawings and this plan were produced on 2026-10-22 and each "
            "passed its own proof run; the slides themselves are still to be assembled."),
    dict(kind="task", name="10.3  Part 2: project plan with WBS, links, resources and costs",
         dur="4d", pct=80, units=1.0, links=["10.2FS"], assign=[],
         ev="this .mpp, its exported views and the Evidence/ folder, 2026-10-22."),
    dict(kind="task", name="10.4  Part 2: detailed requirement specification write-up",
         dur="5d", pct=40, units=1.5, links=["10.3SS"],
         assign=[],
         ev="138 requirements and 27 use cases exist as YAML with acceptance criteria; "
            "the prose document for submission is not assembled."),
    dict(kind="ms", name="M10  Part 1 course deadline (contract 2026-10-02, missed)", links=["10.1FS"],
         deadline="2026-10-02", breach_is_fact=True,
         statutory=True,
         ev="Brief page 1: no later than midnight Friday 2 October 2026. Kept in the "
            "plan as a missed statutory date, shown by Project's deadline arrow against "
            "a row that was never booked complete."),
    dict(kind="ms", pct=0, name="M11  Mid-term teacher review (scheduled 2026-10-23 noon)",
         links=["10.2FS"], deadline="2026-10-23",
         obs=dict(date="2026-10-23", basis="stated by the student",
                  cite="the team's own account of the meeting time; no course-platform "
                       "record was read for this date"),
         ev="SCHEDULED, NOT HELD. The review with the teacher takes place at noon on "
            "2026-10-23 (+08:00), after this pack was built, so the row is booked 0% "
            "and the package is what the review will look at. Nothing here claims the "
            "teacher has seen or accepted anything."),
    dict(kind="ms", name="M12  Part 2 course deadline (contract 2026-11-06)", links=["10.4FS"],
         deadline="2026-11-06",
         statutory=True,
         ev="Brief page 2: no later than midnight Friday 6 November 2026. A Deadline, so "
            "the plan shows whether the remaining chain can still make it."),

    # ------------------------------------------------------ 11 acceptance
    dict(kind="sum", name="11  Final acceptance, documentation and delivery"),
    dict(kind="task", name="11.1  Evidence pack: source mapping and automation verification",
         dur="1d", pct=100, units=1.0, links=["10.2FS"], assign=[],
         ev="deliverables/SoftwareEngineering_2026/Evidence/ written by this build, with "
            "the proof-run result files beside it."),
    dict(kind="task", name="11.2  Publish the deliverables to the repository",
         dur="1d", pct=50, units=1.0, links=["11.1FS"], assign=[],
         ev="Commit and push are attempted by this build and the result is read back "
            "from git, not assumed: the published SHA and the branch are recorded in "
            "AUTOMATION_VERIFICATION.md."),
    dict(kind="ms", name="M13  Coursework delivery (plan)", links=["11.2FS", "M12FS"],
         deadline="2026-11-06",
         statutory=True,
         ev="Same statutory date as M12, kept as its own acceptance gate: the work is "
            "delivered only when the published commit exists, not when the files exist "
            "locally."),
]


# ---------------------------------------------------------------------------
# Student effort, in hours, per person per row. R2 derived hours from
# duration x units, which produced 1,808 h of student labour against a
# three-person capacity of about 840 h - arithmetically fine, impossible to
# execute. R3 states the human effort directly and Microsoft Project derives
# assignment units so that Work equals these numbers exactly.
#
# Why the numbers are small: the repository's own evidence is that code
# production ran through the automation lanes (single commit identity, 15,047
# commits across refs in six weeks). What the students did is specify, decide,
# review and write. Compute lanes are material resources below and are never
# counted as student hours.
#
# Availability assumption, to be confirmed by each member: 20 h per week per
# student while the module runs (RESOURCES[].avail_week). Over the nine
# scheduled weeks that is 180 h each, 540 h for the group.
EFF = {
    "1.1": {"yang": 3}, "1.2": {"yang": 2}, "1.3": {"yang": 2, "wangjr": 2, "wangxy": 2},
    "2.1": {"yang": 4}, "2.2": {"yang": 9}, "2.3": {"yang": 6}, "2.4": {"yang": 4},
    "3.1": {"yang": 6}, "3.2": {"yang": 4, "wangjr": 3}, "3.3": {"wangjr": 7, "wangxy": 3},
    "4.1": {"yang": 3}, "4.2": {"yang": 2, "wangjr": 2}, "4.3": {"yang": 4}, "4.4": {"wangjr": 6},
    "4.5": {"wangjr": 5},
    "5.1": {"wangjr": 5}, "5.2": {"wangjr": 3}, "5.3": {"wangjr": 4}, "5.4": {"wangjr": 3},
    "6.1": {"wangxy": 5}, "6.2": {"wangxy": 5}, "6.3": {"wangxy": 6}, "6.4": {"wangxy": 4},
    "6.5": {"wangxy": 2},
    "7.1": {"wangxy": 5}, "7.2": {"wangxy": 5}, "7.3": {"wangxy": 6},
    "8.1": {"yang": 6}, "8.2": {"wangxy": 3},
    "9.1": {"wangjr": 7}, "9.2": {"wangxy": 4, "wangjr": 3}, "9.3": {"wangjr": 6}, "9.4": {"wangxy": 5},
    "9.5": {"yang": 3, "wangjr": 3}, "9.6": {"wangjr": 3},
    "10.1": {"yang": 4, "wangjr": 3, "wangxy": 2},
    "10.2": {"yang": 5, "wangjr": 4, "wangxy": 4},
    "10.3": {"yang": 6}, "10.4": {"wangjr": 6, "wangxy": 5},
    "11.1": {"yang": 3, "wangxy": 2}, "11.2": {"yang": 2},
}
# rows whose effort is deliberately NOT booked as student hours: the machine work
LANES_ONLY = {}

# attach the effort table to the rows so every consumer reads one source
def _attach_eff():
    import re as _re
    for _r in PLAN:
        if _r.get("kind") != "task":
            continue
        _k = _re.match(r"^(\d+(?:\.\d+)?)\s", _r["name"]).group(1)
        if _k in EFF:
            _r["eff"] = EFF[_k]
        elif _k not in LANES_ONLY:
            raise AssertionError("row %s has no student effort stated" % _k)
_attach_eff()


RESOURCES = [
    dict(key="yang", name="Yang Jianbin 0802240329 - requirements, architecture, integration",
         initials="YJB", rtype="work", max_units=1.0, avail_week=20.0, std=20.0, ovt=30.0,
         note="MEMBER 1 OF 3, named to this build on 2026-10-22. Identity in git: "
              "Canshu-King / yjianbin419@gmail.com, 1006 of 1095 commits on the reviewed "
              "branch, and the signature line of CityNexus_进度汇报_2026-10-13.md. "
              "STANDARD RATE IS A COURSEWORK PLANNING RATE FOR AN UNEVALUATED STUDENT "
              "TEAM, NOT A PAYROLL FIGURE; the hours behind it are the schedule's own."),
    dict(key="wangjr", name="Wang Jiarui 0802240322 - data integration, backend scopes, testing",
         initials="WJR", rtype="work", max_units=1.0, avail_week=20.0, std=20.0, ovt=30.0,
         note="MEMBER 2 OF 3, named to this build on 2026-10-22. NOT SEPARATELY "
              "EVIDENCED IN GIT: the reviewed branch carries one commit identity, "
              "because the automation lanes committed through it. The responsibility "
              "split is the plan's proposal for the report and is marked to be "
              "confirmed. RATE IS A PLANNING RATE, NOT A WAGE."),
    dict(key="wangxy", name="Wang Xinyue 0802240324 - frontend, agent surface, SRS writing",
         initials="WXY", rtype="work", max_units=1.0, avail_week=20.0, std=20.0, ovt=30.0,
         note="MEMBER 3 OF 3, named to this build on 2026-10-22. See the note on member "
              "2 about git evidence. RATE IS A PLANNING RATE, NOT A WAGE."),
    dict(key="qoder", name="Qoder agent lanes - automated build and test compute",
         initials="QL", rtype="material", std=6.0, ovt=0.0,
         note="EVIDENCED in git by the qoder-ai-lane, Qoder and lane-* author identities. "
              "Entered as a MATERIAL resource on purpose: a compute lane does not work "
              "hours, so it must not accrue labour hours or an hourly wage. The rate is "
              "a placeholder for measured API cost, and Work stays at zero."),
    dict(key="codex", name="Codex co-development - compute",
         initials="CX", rtype="material", std=6.0, ovt=0.0,
         note="EVIDENCED in git by the Codex and Codex Local Integration author "
              "identities. Material resource for the same reason as the Qoder lanes: "
              "cost without labour hours."),
]

PROJECT = dict(
    name="CityNexus - Software Engineering 2026",
    start="2026-09-07 09:00",
    status_date="2026-10-22 09:00",
    author="Generated from the CityNexus repository by the Qoder coursework build",
    company="TUTE - Software Engineering module 2026",
    notes=(
        "CityNexus, chosen project 11 of the 2026 assignment brief: a smart city "
        "traveler system. Part 1 was due 2026-10-02 and Part 2 is due 2026-11-06.\n"
        "\n"
        "HOW THIS SCHEDULE IS MADE. The project starts 2026-09-07, the first working "
        "day on or after the repository's first commit (2026-09-05, a Saturday). Every "
        "task and every milestone is auto scheduled with the constraint 'As Soon As "
        "Possible' - no date is typed into any row, and no milestone pins a start. The "
        "only calendar facts in the file are the project start, the status date "
        "2026-10-22, and the Deadline column, which Project displays but does not obey. "
        "Dates, work, cost, slack and the critical path are all consequences of the "
        "links fed through the scheduling engine.\n"
        "\n"
        "TWO CLOCKS, KEPT APART. The repository has commits on 2026-09-05 and from "
        "2026-09-19 onward with nothing in between, while several documents carry "
        "author dates (09-12, 09-13, 09-15, 09-23) that predate the commit holding them. "
        "Where a row records such an observation it is written into the task's Notes as "
        "'observed' with the basis named (commit / document / owner statement / this "
        "build). An observation is never used as a constraint, so a reader can compare "
        "what the plan computes against what actually happened.\n"
        "\n"
        "WHAT IS HONEST ABOUT PROGRESS. A percentage is entered only where evidence "
        "supports it, and each row's Notes names that evidence. Rows that were not done "
        "are left at 0% inside the window they were planned for, so they read as overdue "
        "rather than being moved to a date that makes the plan look tidy. Part 1 is one "
        "of them: its submission cannot be confirmed or denied from this repository, so "
        "it says so and waits for the course record.\n"
        "\n"
        "NO BASELINE IS SAVED. There is no approved original plan for this project to "
        "save as one, so Baseline start/finish stay empty by design rather than being "
        "back-filled from the current dates.\n"
        "\n"
        "RESOURCES AND COST. Three named students plus two compute lanes. Students are "
        "work resources, so Project derives Work from duration x units x 8h/day and "
        "Cost from Work x rate - the two always correspond. The compute lanes are "
        "material resources, so they cost without pretending to work hours. Rates are "
        "coursework planning rates, not payroll.\n"
        "\n"
        "WHERE THE PARTIAL CREDIT COMES FROM. Backend/frontend/contracts/testing all "
        "start 2026-09-19 in git and run side by side, so those rows are joined to their "
        "design predecessors Start-to-Start rather than end-to-start; a serial finish-to-"
        "start chain would push the finished work past the status date and would be a "
        "false statement about how the project actually ran."
    ),
)
