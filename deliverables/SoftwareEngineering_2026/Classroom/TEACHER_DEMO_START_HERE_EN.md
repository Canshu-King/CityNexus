# Start here (English set — three files, ~2.5 minutes)

The Chinese set is `TEACHER_DEMO_START_HERE.md`. This is the English twin,
generated 2026-10-29, for bilingual or international presentation.
Every file here is a native, editable document — not a picture: shapes can be
dragged in Visio, durations edited in Project. The forensic originals (source
line numbers, the 65-row plan, resource assignments) are untouched in
`Visio/` and `Microsoft_Project/`.

## Order and script

### ① `Teacher_01_System_Overview_EN.vsdx` — 30 s: what the system is

Double-click to open (the `[Read-Only]` title is fine; Save-As a copy to demo
editing).

> "CityNexus is an urban travel assistant. The traveller asks for a trip, the
> frontend hands it to the backend, the backend hands it to the Agent; the
> Agent calls place & routing tools and builds itinerary options that are shown
> on a map — **and the final write happens only after the user confirms**. That
> is the whole system: eight boxes, one screen."

Close on the note: no source line numbers appear on the drawing; the provenance
lives in Shape Data (select a box, press `Ctrl+1`).

### ② `Teacher_02_Agent_User_Flow_EN.vsdx` — 30 s: the Agent cannot change trips

> "This is the user flow of the same system. The diamond is the point: only
> 'no' writes anything and leaves an audit trail; 'yes' only produces a new
> proposal and loops back to the tool-call step — the itinerary table does not
> move. The Agent proposes; the power to change a trip stays with the user."

The appendix page (page 2) holds the code-level evidence for that loop; it is
not projected.

### ③′ `previews/Teacher_03_Gantt_Presentation_EN.png` — the projector visual (optional replacement for ③)

> "Read in three seconds: **green = finished, the dark part of a blue 
> bar is where we are and the light tail is what remains, the red dashed 
> lines are the three hard dates** (Part 1, mid-term, Part 2 on 11-06), 
> and the diamond lane is the 13 milestones. Same data as the Project 
> file — expand details live with ③."

Drawn by `Evidence/scripts/se_r8_gantt_draw_r1.py` from data exported by 
`se_r8_gantt_export_r1.py`; nothing rescheduled. The native file stays 
the editable deliverable.

### ③ `Teacher_03_Project_Overview_R4_EN.mpp` — 60 s: the plan behind it

Opens on a collapsed Gantt: 11 English work-package rows with full dates,
percent complete and gray summary bars, September to December 2026. All 65
tasks, dependencies and resource assignments of the real plan are inside —
expand (Outline → Show Subtasks) to show any of them on demand. Green arrows on
milestone rows are contract/check deadlines, which are not plan dates.

The Chinese twins of ① ② ③ (`Teacher_01_…vsdx`, `Teacher_02_…vsdx`,
`Teacher_03_Project_Overview_R4.mpp`) carry the same geometry and the same
data — switch languages by switching files, nothing else changes.
