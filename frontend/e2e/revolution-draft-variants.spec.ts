import { expect, test } from "@playwright/test";
const jid = "00000000-0000-4000-8000-000000000981";
const tid = "00000000-0000-4000-8000-000000000982";
for (const width of [390, 430]) test(`TEST_FIXTURE choose a sourced draft variant and restore at ${width}`, async ({ page }) => {
  await page.setViewportSize({width, height: 932});
  await page.addInitScript(({jid,tid}) => {
    sessionStorage.setItem("citynexus.traveler.bearer", "VARIANT_TEST_FIXTURE_TOKEN");
    sessionStorage.setItem("citynexus.traveler.session-id", "VARIANT_FIXTURE_OWNER");
    localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({id:jid, ownerTravelerId:"VARIANT_FIXTURE_OWNER",cityCode:"TEST_FIXTURE",cityName:"TEST_FIXTURE",status:"DRAFT"}));
    localStorage.setItem(`citynexus.revolution.goal-task.VARIANT_FIXTURE_OWNER.${jid}`,tid);
  },{jid,tid});
  let puts = 0;
  const task = {task_id:tid, journey_id:jid, status:"PARTIAL_READY",goal:"TEST_FIXTURE 两日",mode:"GOAL_PLANNING",consent:{model:true,online_research:true},budget:{max_model_turns:24,max_tool_calls:48},usage:{model_turns:4,tool_calls:3},tool_steps:[],research_places:[],conversation:[],
    draft_artifact:{revision:4,status:"DRAFT",days:[{date:"2026-10-21",slots:[{title:"TEST_FIXTURE 原草案",time_of_day:"afternoon",notes:""}]}]},
    draft_variants:[{id:"relaxed",title:"轻松慢逛",comparison:"使用附近两处来源地点，减少移动",source_place_ids:["amap:fixture-a"],route_ids:[],unknown_summary:["营业与票价待查"],artifact:{revision:1,status:"DRAFT",days:[{date:"2026-10-21",slots:[{title:"TEST_FIXTURE 轻松文化行程",time_of_day:"afternoon",notes:"营业待查",place_id:"amap:fixture-a"}]}]}}]};
  const root = `/api/v1/journeys/${jid}`;
  await page.route("**/api/v1/**",async route=>{
    const path = new URL(route.request().url()).pathname;
    const reply=(data:unknown)=>route.fulfill({status:200,contentType:"application/json",body:JSON.stringify(data)});
    if(path==="/api/v1/travelers/session")return reply({traveler_id:"VARIANT_FIXTURE_OWNER"});
    if(path==="/api/v1/agent/runtime-status")return reply({ai_state:"CONFIGURED_UNVERIFIED",hermes_compat_configured:true});
    if(path===root)return reply({id:jid,status:"DRAFT",timezone:"Asia/Shanghai",title:"TEST_FIXTURE"});
    if(path===`${root}/plans`)return reply([]);
    if(path===`${root}/map-places`)return reply({journey_id:jid,candidates:[]});
    if(path===`${root}/planning-intent`)return reply({journey_id:jid,intent:null,candidates:[],trip:{dates:["2026-10-21"],party_size:1,budget:{amount_minor:50000,currency:"CNY"}}});
    if(path===`${root}/bootstrap-shortlist`)return reply({journey_id:jid,pocket_walk:null});
    if(path===`${root}/bootstrap-discovery/current`)return reply({journey_id:jid,candidates:[],receipt_id:null});
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
  await page.goto("/revolution");
  await page.getByTestId("rev-mobile-tab-assistant").click();
  await page.getByTestId("rev-mission-layer-timeline").click();
  const variants=page.getByRole("region",{name:"旅行方案对比"});
  await expect(variants).toBeVisible();
  await variants.getByRole("button",{name:"查看每天安排与待查事项"}).click();
  await expect(variants).toContainText("营业与票价待查");
  await variants.getByRole("button",{name:"选用这份安排"}).click();
  await expect.poll(()=>puts).toBe(1);
  await page.reload();await page.getByTestId("rev-mobile-tab-assistant").click();
  await page.getByTestId("rev-mission-layer-timeline").click();
  const editor=page.getByTestId("rev-mission-timeline-pane").locator(".rev-goal-draft");
  await editor.locator(".rev-goal-draft-slot summary").first().click();
  await expect(editor.getByLabel("安排",{exact:true})).toHaveValue("TEST_FIXTURE 轻松文化行程");
  expect(puts).toBe(1);
});
