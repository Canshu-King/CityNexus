import { expect, test } from "@playwright/test";
const jid = "00000000-0000-4000-8000-000000000981";
const tid = "00000000-0000-4000-8000-000000000982";
for (const width of [390, 430]) test(`TEST_FIXTURE prepare selected draft dates and restore at ${width}`, async ({ page }, testInfo) => {
  await page.setViewportSize({width, height: 932});
  await page.addInitScript(({jid,tid}) => {
    sessionStorage.setItem("citynexus.traveler.bearer", "VARIANT_TEST_FIXTURE_TOKEN");
    sessionStorage.setItem("citynexus.traveler.session-id", "VARIANT_FIXTURE_OWNER");
    localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({id:jid, ownerTravelerId:"VARIANT_FIXTURE_OWNER",cityCode:"TEST_FIXTURE",cityName:"TEST_FIXTURE",status:"DRAFT"}));
    localStorage.setItem(`citynexus.revolution.goal-task.VARIANT_FIXTURE_OWNER.${jid}`,tid);
  },{jid,tid});
  let puts = 0; let prepares = 0; let plans: unknown[] = []; const generates: Record<string, unknown>[] = []; let generateCalls = 0;
  const task = {task_id:tid, journey_id:jid, status:"PARTIAL_READY",goal:"TEST_FIXTURE 两日",mode:"GOAL_PLANNING",consent:{model:true,online_research:true},budget:{max_model_turns:24,max_tool_calls:48},usage:{model_turns:4,tool_calls:3},tool_steps:[],research_places:[],conversation:[],
    draft_artifact:{revision:4,status:"DRAFT",days:[{date:"2026-10-21",slots:[{title:"TEST_FIXTURE 原草案",time_of_day:"afternoon",notes:""}]}]},
    draft_variants:[{id:"relaxed",title:"轻松慢逛",comparison:"使用附近两处来源地点，减少移动",source_place_ids:["amap:fixture-a"],route_ids:[],unknown_summary:["营业与票价待查"],artifact:{revision:1,status:"DRAFT",days:[{date:"2026-10-21",slots:[{title:"TEST_FIXTURE 轻松文化行程",time_of_day:"afternoon",notes:"营业待查",place_id:"amap:fixture-a"}]}]}}]};
  const baseVariant = task.draft_variants[0];
  task.draft_variants.push(...["budget", "local"].map((id, index) => ({ ...baseVariant, id, title: index ? "本地风味" : "预算优先", artifact: { ...baseVariant.artifact, days: [{ date: "2026-10-21", slots: [{ ...baseVariant.artifact.days[0].slots[0], title: `TEST_FIXTURE 独立方案${id}` }] }] } })));
  const root = `/api/v1/journeys/${jid}`;
  await page.route("**/api/v1/**",async route=>{
    const path = new URL(route.request().url()).pathname;
    const reply=(data:unknown)=>route.fulfill({status:200,contentType:"application/json",body:JSON.stringify(data)});
    if(path==="/api/v1/travelers/session")return reply({traveler_id:"VARIANT_FIXTURE_OWNER"});
    if(path==="/api/v1/agent/runtime-status")return reply({ai_state:"CONFIGURED_UNVERIFIED",hermes_compat_configured:true});
    if(path===root)return reply({id:jid,status:"DRAFT",timezone:"Asia/Shanghai",title:"TEST_FIXTURE"});
    if(path===`${root}/departure/commit`){
      return route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({
        error: { code: "PLAN_INFEASIBLE", reason_code: "PLAN_INFEASIBLE",
          message: "这版方案排不下：两段安排之间留的赶路时间不够（1 段）。" } }) });
    }
    if(path===`${root}/plans`)return reply(plans);
    if(path===`${root}/departure`)return reply({journey_id:jid,gate:"NO_PLAN_SELECTED",candidates:[],selected_plan:null});
    if(path===`${root}/members/me`)return reply({journey_id:jid,may_confirm_departure:true});
    if(path===`${root}/map-places`)return reply({journey_id:jid,candidates:[]});
    if(path===`${root}/planning-intent`)return reply({journey_id:jid,intent:null,candidates:[],trip:{dates:["2026-10-21"],party_size:1,budget:{amount_minor:50000,currency:"CNY"}}});
    if(path===`${root}/bootstrap-shortlist`)return reply({journey_id:jid,pocket_walk:null});
    if(path===`${root}/bootstrap-discovery/current`)return reply({journey_id:jid,candidates:[],receipt_id:null});
    if(path===`${root}/agent/goal-tasks/${tid}/prepare-plan`){
      expect(route.request().method()).toBe("POST");
      expect(route.request().headers().authorization).toBe("Bearer VARIANT_TEST_FIXTURE_TOKEN");
      expect(route.request().headers()["idempotency-key"]).toBeTruthy();
      const body=route.request().postDataJSON();expect(body.expected_revision).toBe(4);
      expect(body.schedule).toEqual([{day_index:0,slot_index:0,start_time:"14:00",end_time:"16:00"}]);prepares++;
      plans=[{id:"plan-fixture",journey_id:jid,status:"CANDIDATE",version_no:1,selectable:false,stale:true,explanation:{compose_source:"SELECTED_GOAL_DRAFT"},total_cost:{amount_minor:0,currency:"CNY"},total_cost_status:"PARTIAL_UNKNOWN",activities:[{id:"activity-fixture",sequence_no:1,title:"TEST_FIXTURE 原草案",start_at:"2026-10-21T14:00:00+08:00",end_at:"2026-10-21T16:00:00+08:00",cost_status:"UNKNOWN",estimated_cost:{amount_minor:0,currency:"CNY"},travel_from_prev_min:0,metadata:{}}]}];
      const result = {journey_id:jid,task_id:tid,draft_revision:4,plan_version_id:"plan-fixture",status:"CANDIDATE",selected:false,activated:false,slots_count:1,mobility_frozen:true,gaps:[{sequence_no:1,title:"TEST_FIXTURE 原草案",kind:"OPENING_HOURS",status:"UNKNOWN",place_id:null}]};
      Object.assign(task,{prepared_plan:{result,schedule:body.schedule}});return reply(result);
    }
    if(path===`${root}/plans/generate`){
      expect(route.request().method()).toBe("POST");
      expect(route.request().headers().authorization).toBe("Bearer VARIANT_TEST_FIXTURE_TOKEN");
      generates.push(route.request().postDataJSON());
      generateCalls += 1;
      if (generateCalls === 2) {
        return route.fulfill({ status: 422, contentType: "application/json", body: JSON.stringify({
          error: { code: "VALIDATION_ERROR", message: "No feasible plan candidates satisfy the journey constraints",
            reason_code: "CATALOG_INSUFFICIENT", details: { places_in_catalog: 54, day_sequences_available: 0 } } }) });
      }
      plans = [1, 2, 3].map((n) => ({ id: `plan-generated-${n}`, journey_id: jid, status: "CANDIDATE", version_no: n + 1,
        selectable: n === 1, stale: false, explanation: { compose_source: "SELECTED_GOAL_DRAFT" },
        total_cost: { amount_minor: 0, currency: "CNY" }, total_cost_status: "PARTIAL_UNKNOWN", activities: [] }));
      return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(plans) });
    }
    if(path===`${root}/agent/goal-tasks/${tid}`)return reply(task);
    if(path===`${root}/agent/goal-tasks/${tid}/events`)return reply({task_id:tid,events:[],next_cursor:null});
    if(path===`${root}/agent/goal-tasks/${tid}/draft`){
      expect(route.request().headers().authorization).toBe("Bearer VARIANT_TEST_FIXTURE_TOKEN");
      expect(route.request().method()).toBe("PUT");
      const body=route.request().postDataJSON();expect(body.expected_revision).toBe(4);puts++;
      task.draft_artifact={revision:5,status:"DRAFT",days:body.days};return reply(task);
    }
    return reply({});
  });
  const gapRows = [{ day_index: 0, slot_index: 0, title: "TEST_FIXTURE 原草案", planned_start: "14:00", planned_end: "16:00",
    proposed_start: "14:18", proposed_end: "16:18", extra_minutes: 18, direct_cause: true }];
  await page.route(`**${root}/agent/goal-tasks/${tid}/plans/plan-fixture/travel-gaps`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      journey_id: jid, task_id: tid, plan_version_id: "plan-fixture", hops: [], rows: gapRows }) }));
  await page.goto("/revolution");
  await page.getByTestId("rev-mobile-tab-trips").click();
  const card=page.getByRole("region",{name:"当前草案的出发准备"});
  await expect(card).toBeVisible();
  await expect(card).toContainText("时间可以稍后调整");
  const save=card.getByRole("button",{name:"保存为正式候选方案"});
  await expect(save).toBeDisabled();
  // P1: the twelve time inputs start folded; the save control stays outside the disclosure.
  await expect(card.getByLabel("TEST_FIXTURE 原草案结束时间")).not.toBeVisible();
  await card.scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath(`draft-schedule-folded-${width}.png`) });
  await card.getByText("编辑行程时间（可选）", { exact: true }).click();
  await expect(card.getByLabel("TEST_FIXTURE 原草案结束时间")).toBeVisible();
  await card.getByLabel("TEST_FIXTURE 原草案结束时间").fill("16:00");
  await card.getByLabel("按以上时间准备方案").check();
  await save.click();
  await expect.poll(()=>prepares).toBe(1);
  await expect(card).toContainText("已保存 1 项正式安排");
  const workbench=page.getByTestId("rev-plan-workbench");
  await expect(workbench.getByTestId("rev-plan-option")).toHaveCount(1);
  await expect(workbench).toContainText("费用待确认");
  await expect(workbench.getByTestId("rev-plan-select")).toHaveCount(0);
  await page.reload();
  await page.getByTestId("rev-mobile-tab-trips").click();
  await expect(page.getByTestId("rev-plan-option")).toContainText("TEST_FIXTURE 原草案");
  await expect(page.getByRole("region",{name:"当前草案的出发准备"})).toContainText("1 项安排已保存，刷新也能找回。");
  expect(puts).toBe(0);expect(prepares).toBe(1);
  // The saved arrangements are not candidates: the generate door must exist, ask plans/generate
  // for three candidates, and make the workbench show them without a reload.
  await expect(card.getByTestId("rev-v3-generate-plans")).toBeEnabled();
  await card.getByTestId("rev-v3-generate-plans").click();
  await expect.poll(() => generates.length).toBe(1);
  expect(generates[0].candidate_count).toBe(3);
  await expect(card).toContainText("已生成 3 份正式候选方案");
  await expect(workbench.getByTestId("rev-plan-option")).toHaveCount(3);
  // A catalogue shortfall is not a retryable accident: the screen must name the city's size and
  // point back to the draft candidate, not show a generic "try again".
  await card.getByTestId("rev-v3-generate-plans").click();
  await expect.poll(() => generateCalls).toBe(2);
  await expect(card).toContainText("54 个真实地点");
  await expect(card).toContainText("继续用上面这份草案候选就可以");
  // A refused selection must offer its own next step where the refusal is shown.  The commit
  // stub answers 200 with a body that does not name this plan; what matters here is the handoff:
  // the button appears, and pressing it reveals the diff in the departure card (no second write).
  await workbench.getByTestId("rev-plan-select").first().click();
  await expect(page.getByTestId("rev-plan-replan")).toBeVisible();
  await page.getByTestId("rev-plan-replan").click();
  await expect(page.locator("[data-testid='rev-v3-replan-diff']")).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
});
