# CityNexus · Software Engineering Coursework 2026 · Part 2 开工任务书

**Date:** 2026-11-04 (+08:00)  
**Delivery:** Moodle, Friday 2026-11-06 midnight as worded by the provided assignment brief; verify the exact Moodle clock. Internal target: finish and attempt upload by the evening of 2026-11-05.  
**Status:** KICKOFF / NOT SUBMITTED. This taskbook is an instruction, not a completion receipt.

## 0. Contract from the teacher's two-page brief

Part 2 is 50% of course grade. Submit **a complete project plan in PDF format and a fully detailed requirements specification**, total **no more than 20 pages** (safest packaging: one combined 20-page-or-less PDF). Filename must clearly contain all three group members' **names and ID numbers**. The project plan MUST show:
1. task headings;
2. tasks;
3. subtasks;
4. task relationships;
5. resources assigned **with costs**.

The brief does NOT specifically require executable source code, `.mpp` upload or `.vsdx` upload for Part 2. Keep native Office source files for demonstrability, but prioritise the PDF. Do not conflate the *software development project schedule* with the separate 2-day *assignment document production schedule*.

Project title is **Smart City Traveler System**, product **CityNexus**. Use the same framing as Part 1.

## 1. Verified source-of-truth anchors, no reinvention

Work from existing coursework branch `review/se-coursework-deliverables-r1` at observed 2026-11-04 commit `ea220687cfb240ab75ec72dd7c562260c7275e94`; this isolated branch was created from that commit. Existing source files:

- Course plan: `deliverables/SoftwareEngineering_2026/Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp`
- Existing Project exports: `deliverables/SoftwareEngineering_2026/Microsoft_Project/{WBS_View,Gantt_Chart,Network_Diagram,Resource_Sheet,Milestone_Timeline}.pdf`
- More legible bilingual/lecture Gantt PDFs: `deliverables/SoftwareEngineering_2026/Classroom/previews/Teacher_03_Gantt_Presentation_{zh,EN}.pdf`
- Classroom native Project files: `deliverables/SoftwareEngineering_2026/Classroom/Teacher_03_Project_Overview_R4{,_EN}.mpp`
- Architecture and agent workflow diagrams, including English versions: `deliverables/SoftwareEngineering_2026/Classroom/Teacher_01_System_Overview_EN.vsdx` and `Teacher_02_Agent_User_Flow_EN.vsdx`, same folder's `previews`.
- Project evidence: `deliverables/SoftwareEngineering_2026/Evidence/se_project_build_r2_result.json`, `PLAN_RECONCILIATION.md`, `STATUS_AND_OVERDUE.md`, `SOURCE_MAPPING.md`.
- Formal requirements: `requirements/requirements.yaml` and `requirements/traceability.yaml`, `requirements/README.md`, `requirements/BASELINE.md`.
- Use cases: `use-cases/use-cases.yaml`.

Verified planning baseline **as of status date 2026-10-22**, not a claim about 2026-11-04 completion:
- 65 Project tasks; 11 WBS top-level headings; 13 milestones; 61 dependency links; 61 resource assignments.
- 3 student work resources plus 2 compute/material resources. Planned labour 220.9 student-hours. Student resource rate US$20/hr; compute/material rates US$6 per assigned material unit. Project cost at baseline US$4,460.688 (report as US$4,460.69 estimated, not actual). Project builder explicitly sets `CurrencySymbol="$"`.
- Proposed resource responsibilities from the existing Project plan:
  - Yang Jianbin **0802240329**: requirements, architecture, integration.
  - Wang Jiarui **0802240322**: data integration, backend scopes, testing.
  - Wang Xinyue **0802240324**: frontend, agent surface, SRS writing.
  Confirm those planned assignments against actual group contributions before presenting as historical facts.
- Requirements v0.3.0 is a **candidate**, NOT teacher-approved. Exactly 138 entries: 8 BG, 61 FR, 24 BR, 16 NFR, 14 SR, 15 IR; 13 top-level use cases. Explicitly show source vs selected final coursework scope and any not-yet-approved status. Never fabricate customer sign-off.
- Existing Project dates are planned/recorded fields, NOT proof of Moodle submission. As of the older evidence Part 1 submission and teacher acceptance remain unverified; do not invent either.
- Previous large Project PDF prints were dozens of pages (85 for one Gantt): do not splice in unfiltered exports. Use intentionally cropped/selected legible project views or professional redraws from the exact exported plan data, clearly labeled as plan-derived.

## 2. Single output definition and page budget (maximum 20 pages)

Preferred deliverable: **one combined English PDF** with SRS + Project Plan, and editable sources retained separately.
Filename candidate (confirm spelling and all IDs):  
`YangJianbin_0802240329_WangJiarui_0802240322_WangXinyue_0802240324_CityNexus_Part2.pdf`

**Suggested 20-page maximum allocation; simplify rather than shrink illegibly:**

| Page(s) | Required content |
|---|---|
| 1 | Title, project name, three names + student IDs, document version/date |
| 2 | Purpose, stakeholders, scope, assumptions, explicit out-of-scope |
| 3 | Actors, context and two or three defined user scenarios |
| 4-7 | Numbered, testable functional requirements (FR), priority, trigger/input/output/acceptance, references to source IDs |
| 8 | Business rules and non-functional requirements with measurable criteria |
| 9 | Security, privacy, access-control, consent and audit requirements |
| 10 | Data model, external interfaces and provider-failure behaviour |
| 11 | Legible system overview + agent decision and human-confirmation flow (one or two figures) |
| 12 | Acceptance cases, verification method, traceability summary, approval status |
| 13 | Project management approach + 11-stage WBS structure |
| 14 | Readable Gantt timeline + all course-critical milestones |
| 15 | Task/subtask dependency examples, link types, critical path caveat, schedule baseline |
| 16 | Three students + two compute/material resources, assigned workload, capacity assumptions |
| 17 | Costed resource table, rate assumptions, assignment costs, US$4,460.69 plan baseline reconciliation |
| 18 | Test and quality strategy, formal criteria and evidence limitations |
| 19 | Risks, mitigation, scope/change control, maintenance and handover |
| 20 | Source references, customer approval status, limitations and version history |

Aim for 18-19 readable pages and keep 1 page slack. No filler. "Fully detailed" means precise observable behaviour and acceptance conditions for the *selected deliverable scope*, not 138 unedited YAML rows crammed into tiny print. Identify selected/merged/retained requirements by stable IDs, and separately state features excluded from the course-scope release. Do not silently change the source baseline.

## 3. Three parallel lanes (agents are NOT started merely by writing this document)

### Lane A - Codex / SRS editor (P0)

Owner: Codex only when explicitly opened/instructed in its active local session. Output on **this coursework branch** under `deliverables/SoftwareEngineering_2026/Part2/`:
- `SRS_DRAFT_EN.md`: polished English SRS section, not code. Preserve official Smart City Traveler System title and source requirement IDs.
- Detailed requirement table for chosen coherent release: ID, statement ("shall"), trigger, input, output, priority, Given/When/Then acceptance, source (BG/FR/BR/NFR/SR/IR), test/verification method.
- Include explicit flows for (1) personalised city trip planning with places and routes, (2) event-driven trip adjustment / informed consent before persistence, and (3) no feasible option / provider outage. Group-travel capability optional only if the final selected scope includes it.
- Cover latency/reliability/privacy/security/evidence/provenance/accessibility constraints with quantifiable targets or say “proposed to confirm”, NEVER invent measured performance.
- Use only existing project architecture and source contracts. Mark candidate requirement approval status. No new source-code feature work or fresh integration refactors. Provide a short source-ID traceability matrix.

Done when: SRS is readable, internally consistent, testable, traceable and honest about unmet/unspecified evidence. Keep roughly 10-12 finished report pages for SRS.

### Lane B - Qoder / Microsoft Project and diagrams (P0)

Owner: Qoder in **its active Windows Project/Visio session**, not automatically run by GitHub.
- Reuse frozen `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` as plan-of-record. Do **not** rewrite dates, resources, dependencies, actual/estimated costs to make the chart pretty.
- Package one readable project-plan annex comprising 11-stage WBS with selected representative subtasks, actual dependency examples (FS/SS/FF as in source), appropriate milestones, readable Gantt, three-person resource list, two material resources, availability assumption, resource rate/cost summary, and risks/quality.
- Verify totals **65 tasks, 61 links, 61 assignments**, 220.9 student-hours, US$4,460.69 cost baseline against source and state the **2026-10-22** snapshot date. If a live refreshed status differs, show the date and reconciliation; do not overwrite historical evidence.
- Use bilingual Visio PDFs as figures where legible and relevant; not every historical diagram belongs in the report.
- Produce `PROJECT_PLAN_DRAFT_EN.md` plus curated image/PDF assets, with total report allocation ~6-7 pages. Preserve editable .mpp and .vsdx separately. Preview on A4 at 100%, no 85-page print, no microscopic text.

Done when: every teacher-required project-plan field is visible in the *PDF*, not merely hidden inside .mpp, and a human can read it without zoom gymnastics.

### Lane C - document integration & independent QA (GPT + group owner)

- Merge lanes A and B into a **single PDF <=20 pages**; retain editable DOCX or Markdown if used.
- Check title/scope across the whole report, WBS-to-requirement consistency, all three members/IDs in content AND filename, US$ and estimating assumptions, source citations, figure readability, actual vs proposed status.
- Render EVERY PDF page and inspect images; check cropping, legibility, captions, no overflow. Verify page count and fonts; no illegible tiny print.
- Send complete PDF to Moodle via user's authenticated browser and record the course platform's receipt. **GitHub commits do not count as submission**. No claim of upload until receipt is actually observed.

## 4. Assignment production sprint (different from product WBS)

- **Nov 4 morning:** freeze source and grade checklist, copy R11 plan visual assets, begin SRS and project-plan extraction in parallel.
- **Nov 4 evening:** first SRS + plan drafts. Reject gaps in acceptance conditions, task links or costs immediately.
- **Nov 5 noon:** integrated English PDF v1, accurate page count, names/IDs and report architecture fixed.
- **Nov 5 evening:** final visual/content review and attempt Moodle upload before the deadline buffer expires.
- **Nov 6:** contingency and final receipt verification only. The brief's “midnight on Friday” is ambiguous; use Moodle's displayed timestamp rather than assuming end-of-day.

## 5. Explicit failure conditions

A draft is NOT ready merely because:
- Project desktop opens or automated tests pass; the required WBS/dependencies/costs are invisible in the PDF.
- It shows a pretty Gantt with no task links and no assigned cost table.
- It dumps 138 raw YAML items but gives no prioritised and testable SRS.
- It labels unapproved requirements “agreed by teacher”; it converts a plan milestone into a claimed Moodle submission; or it treats future/planned tasks as historically completed.
- PDF spills beyond 20 pages, is unreadable at A4, or lacks all three names/IDs in the filename.
- It only updates a GitHub issue without an actual PDF/Moodle receipt.

## 6. Source integrity

This taskbook is based on the user-provided two-page official coursework PDF plus verified GitHub paths above, as observed 2026-11-04. Use those as sources. Part 2 text says “a complete project plan in pdf format and a fully detailed requirement specification ... no more than 20 pages”; it does not settle whether Moodle wants one combined upload or two attachments. One combined PDF within 20 pages is the conservative default until the actual Moodle submission UI says otherwise.

**First action for both local agents:** read this taskbook AND the named source files; work ONLY on this isolated coursework branch, commit drafts, report exact paths and evidence. Preserve the separate CityNexus product branches.
