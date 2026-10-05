import { expect, test } from "@playwright/test";
import { ensureDemoJourney, openScreen } from "./_qoderShellSeed";

const TOKEN = "r28-ui-signed-bearer";
const mission = {
  id: "r28-ui-mission",
  journey_id: "journey-from-route",
  trigger_event_id: null,
  user_text: "Resolve the shared trade-off.",
  status: "WAITING_FOR_MEMBERS",
  parent_mission_id: null,
  clarification: {
    kind: "COLLECTIVE_TRADEOFF",
    clarification_id: "r28-ui-clarification",
    status: "WAITING_FOR_MEMBERS",
  },
};

test.describe("R28 collective decision surface", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((token) => {
      window.sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, TOKEN);
    await ensureDemoJourney(page);
    await openScreen(page, "/v8/hub", ["today-heading"]);
  });

  test("shows member progress and sends the signed traveler bearer when answering", async ({ page }) => {
    let answerAuthorization = "";
    await page.route("**/api/v1/journeys/*/missions/pending", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          journey_id: "journey-from-route",
          viewer: {
            traveler_id: "traveler-owner",
            member_id: "member-owner",
            role: "OWNER",
            auth_method: "SIGNED_HMAC_BEARER",
          },
          items: [{
            mission,
            run: null,
            continuation: null,
            collective: {
              status: "WAITING_FOR_MEMBERS",
              policy: "MATERIAL_TRADEOFF_REQUIRES_ALL_RELEVANT_MEMBER_RESPONSES",
              required_count: 2,
              response_count: 1,
              viewer_member_id: "member-owner",
              viewer_has_responded: false,
              selected_proposal_id: null,
              required_members: [
                {
                  member_id: "member-owner",
                  traveler_id: "traveler-owner",
                  role: "OWNER",
                  display_name: "Owner",
                  responded: false,
                  is_viewer: true,
                },
                {
                  member_id: "member-admin",
                  traveler_id: "traveler-admin",
                  role: "ADMIN",
                  display_name: "Admin",
                  responded: true,
                  is_viewer: false,
                },
              ],
              candidate_options: [
                {
                  proposal_id: "11111111-1111-1111-1111-111111111111",
                  status: "GROUNDED_FEASIBLE",
                  display_places: [{ place_id: "garden", name: "Garden", category: "garden" }],
                  fit_subject_tags: ["garden", "quiet"],
                  fairness: { unacceptable_member_ids: ["member-admin"] },
                },
                {
                  proposal_id: "22222222-2222-2222-2222-222222222222",
                  status: "GROUNDED_FEASIBLE",
                  display_places: [{ place_id: "museum", name: "Museum", category: "museum" }],
                  fit_subject_tags: ["museum", "craft"],
                  fairness: { unacceptable_member_ids: ["member-owner"] },
                },
              ],
            },
          }],
        }),
      });
    });

    await page.route("**/api/v1/journeys/*/missions/*/collective-clarification/member-owner", async (route) => {
      answerAuthorization = route.request().headers()["authorization"] ?? "";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          journey_id: "journey-from-route",
          mission_id: mission.id,
          clarification_id: "r28-ui-clarification",
          status: "WAITING_FOR_MEMBERS",
          responses: {
            "member-owner": {
              member_id: "member-owner",
              proposal_id: "11111111-1111-1111-1111-111111111111",
            },
          },
          baseline_preferences_unchanged: true,
          traveler_twin_unchanged: true,
          child_mission: null,
        }),
      });
    });

    await page.getByTestId("v18-copilot-dock").locator(".cn-copilot-edge").click();
    await expect(page.getByTestId("collective-decision")).toBeVisible();
    await expect(page.getByTestId("collective-progress")).toHaveText("1/2");
    await expect(page.getByTestId("collective-member")).toHaveCount(2);
    await expect(page.getByTestId("collective-option")).toHaveCount(2);

    await page.getByTestId("collective-option").first().getByRole("button").click();
    await expect.poll(() => answerAuthorization).toBe(`Bearer ${TOKEN}`);
    await expect(page.locator(".cn-collective-notice")).toContainText(/saved|等待/i);
  });

  test("shows durable approval and sends the same signed identity when approving", async ({ page }) => {
    let approvalAuthorization = "";
    await page.route("**/api/v1/journeys/*/missions/pending", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          journey_id: "journey-from-route",
          viewer: {
            traveler_id: "traveler-owner",
            member_id: "member-owner",
            role: "OWNER",
            auth_method: "SIGNED_HMAC_BEARER",
          },
          items: [{
            mission: {
              ...mission,
              id: "r28-approval-mission",
              status: "WAITING_FOR_APPROVAL",
              clarification: {},
            },
            run: {
              run_id: "r28-run",
              mission_id: "r28-approval-mission",
              provider_key: "hermes",
              model_key: "test",
              status: "WAITING_FOR_APPROVAL",
              outcome: "waiting",
              failure_reason: null,
              tool_steps: [],
              completion_contract: { kind: "APPROVAL_PENDING" },
            },
            collective: null,
            continuation: {
              pending_action_id: "pending-1",
              pending_status: "PENDING",
              tool_name: "accept_replan",
              approval_id: "approval-1",
              approval_status: "PENDING",
              required_decision: "REQUIRE_CONFIRMATION",
              approved_by: null,
              viewer_can_approve: true,
            },
          }],
        }),
      });
    });

    await page.route("**/api/v1/journeys/*/agent/approvals/approval-1/approve", async (route) => {
      approvalAuthorization = route.request().headers()["authorization"] ?? "";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          approval_id: "approval-1",
          journey_id: "journey-from-route",
          action: "ACCEPT_REPLAN",
          target_type: "ReplanProposal",
          target_id: "proposal-1",
          status: "CONSUMED",
          approval_method: "USER_CONFIRMATION",
          approved_by: "traveler-owner",
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 60_000).toISOString(),
          approved_at: new Date().toISOString(),
          consumed_at: new Date().toISOString(),
          continuation: {
            status: "RESUMED",
            pending_action_id: "pending-1",
            run_id: "r28-run",
            mission_id: "r28-approval-mission",
            replayed: false,
          },
        }),
      });
    });

    await page.getByTestId("v18-copilot-dock").locator(".cn-copilot-edge").click();
    await expect(page.getByTestId("collective-approval")).toBeVisible();
    await page.getByTestId("collective-approve").click();
    await expect.poll(() => approvalAuthorization).toBe(`Bearer ${TOKEN}`);
    await expect(page.locator(".cn-collective-notice")).toContainText(/resumed|继续|完成/i);
  });

  test("shows disagreement, renewed two-member consent, then approval", async ({ page }) => {
    let stage = 0;
    let viewer: "owner" | "admin" = "owner";
    let round2OwnerAuthorization = "";
    let round2AdminAuthorization = "";
    let approvalAuthorization = "";
    const adminToken = "r29-ui-admin-signed-bearer";
    const ownerProposal = "11111111-1111-1111-1111-111111111111";
    const adminProposal = "22222222-2222-2222-2222-222222222222";
    const compromiseProposal = "33333333-3333-3333-3333-333333333333";

    const viewerRecord = () => viewer === "owner"
      ? { traveler_id: "traveler-owner", member_id: "member-owner", role: "OWNER", auth_method: "SIGNED_HMAC_BEARER" }
      : { traveler_id: "traveler-admin", member_id: "member-admin", role: "ADMIN", auth_method: "SIGNED_HMAC_BEARER" };

    const collective = (
      options: Array<Record<string, unknown>>,
      responseCount: number,
      respondedMembers: string[],
    ) => {
      const viewerMemberId = viewer === "owner" ? "member-owner" : "member-admin";
      return {
        status: "WAITING_FOR_MEMBERS",
        policy: stage >= 2
          ? "POST_DISAGREEMENT_REQUIRES_RENEWED_MEMBER_CONSENT"
          : "MATERIAL_TRADEOFF_REQUIRES_ALL_RELEVANT_MEMBER_RESPONSES",
        required_count: 2,
        response_count: responseCount,
        viewer_member_id: viewerMemberId,
        viewer_has_responded: respondedMembers.includes(viewerMemberId),
        selected_proposal_id: null,
        required_members: [
          {
            member_id: "member-owner",
            traveler_id: "traveler-owner",
            role: "OWNER",
            display_name: "Owner",
            responded: respondedMembers.includes("member-owner"),
            is_viewer: viewer === "owner",
          },
          {
            member_id: "member-admin",
            traveler_id: "traveler-admin",
            role: "ADMIN",
            display_name: "Admin",
            responded: respondedMembers.includes("member-admin"),
            is_viewer: viewer === "admin",
          },
        ],
        candidate_options: options,
      };
    };

    const oldOptions = [
      {
        proposal_id: ownerProposal,
        status: "GROUNDED_FEASIBLE",
        display_places: [{ place_id: "garden", name: "Garden", category: "garden" }],
        fit_subject_tags: ["garden"],
        fairness: { unacceptable_member_ids: ["member-admin"] },
      },
      {
        proposal_id: adminProposal,
        status: "GROUNDED_FEASIBLE",
        display_places: [{ place_id: "museum", name: "Museum", category: "museum" }],
        fit_subject_tags: ["museum"],
        fairness: { unacceptable_member_ids: ["member-owner"] },
      },
    ];
    const compromiseOption = {
      proposal_id: compromiseProposal,
      status: "GROUNDED_FEASIBLE",
      display_places: [{ place_id: "craft-garden", name: "Craft Garden", category: "craft" }],
      fit_subject_tags: ["craft", "garden"],
      fairness: { minimum_member_fit: 0.7, maximum_regret: 0.2, unacceptable_member_ids: [] },
    };
    const renewedOptions = [...oldOptions, compromiseOption];

    await page.route("**/api/v1/journeys/*/missions/pending", async (route) => {
      let item: Record<string, unknown>;
      if (stage === 0) {
        item = {
          mission: {
            ...mission,
            id: "r29-round-1",
            status: "WAITING_FOR_MEMBERS",
            clarification: { ...mission.clarification, clarification_id: "r29-round-1" },
          },
          run: null,
          continuation: null,
          collective: collective(oldOptions, 1, ["member-admin"]),
        };
      } else if (stage === 2) {
        item = {
          mission: {
            ...mission,
            id: "r29-round-2",
            status: "WAITING_FOR_MEMBERS",
            parent_mission_id: "r29-round-1",
            clarification: { ...mission.clarification, clarification_id: "r29-round-2" },
          },
          run: null,
          continuation: null,
          collective: collective(renewedOptions, 0, []),
        };
      } else if (stage === 3) {
        item = {
          mission: {
            ...mission,
            id: "r29-round-2",
            status: "WAITING_FOR_MEMBERS",
            parent_mission_id: "r29-round-1",
            clarification: { ...mission.clarification, clarification_id: "r29-round-2" },
          },
          run: null,
          continuation: null,
          collective: collective(renewedOptions, 1, ["member-owner"]),
        };
      } else {
        item = {
          mission: {
            ...mission,
            id: "r29-resolved-child",
            status: "WAITING_FOR_APPROVAL",
            parent_mission_id: "r29-round-2",
            clarification: {},
          },
          run: {
            run_id: "r29-final-run",
            mission_id: "r29-resolved-child",
            provider_key: "hermes",
            model_key: "test",
            status: "WAITING_FOR_APPROVAL",
            outcome: "waiting",
            failure_reason: null,
            tool_steps: [],
            completion_contract: { kind: "APPROVAL_PENDING" },
          },
          collective: null,
          continuation: {
            pending_action_id: "r29-pending",
            pending_status: "PENDING",
            tool_name: "accept_replan",
            approval_id: "r29-approval",
            approval_status: "PENDING",
            required_decision: "REQUIRE_CONFIRMATION",
            approved_by: null,
            viewer_can_approve: viewer === "owner",
          },
        };
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          journey_id: "journey-from-route",
          viewer: viewerRecord(),
          items: [item],
        }),
      });
    });

    await page.route("**/api/v1/journeys/*/missions/r29-round-1/collective-clarification/member-owner", async (route) => {
      stage = 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "MEDIATION_REQUIRED",
          child_mission: { id: "r29-mediator" },
        }),
      });
    });

    await page.route("**/api/v1/journeys/*/missions/r29-mediator/resume", async (route) => {
      stage = 2;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          run: {
            run_id: "r29-mediator-run",
            mission_id: "r29-mediator",
            provider_key: "hermes",
            model_key: "test",
            status: "WAITING_FOR_MEMBERS",
            outcome: "waiting",
            failure_reason: null,
            tool_steps: [],
            completion_contract: { kind: "CLARIFICATION_REQUIRED" },
          },
        }),
      });
    });

    await page.route("**/api/v1/journeys/*/missions/r29-round-2/collective-clarification/member-owner", async (route) => {
      round2OwnerAuthorization = route.request().headers()["authorization"] ?? "";
      stage = 3;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "WAITING_FOR_MEMBERS",
          responses: {
            "member-owner": { member_id: "member-owner", proposal_id: compromiseProposal },
          },
          child_mission: null,
        }),
      });
    });

    await page.route("**/api/v1/journeys/*/missions/r29-round-2/collective-clarification/member-admin", async (route) => {
      round2AdminAuthorization = route.request().headers()["authorization"] ?? "";
      stage = 4;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "RESOLVED",
          responses: {
            "member-owner": { member_id: "member-owner", proposal_id: compromiseProposal },
            "member-admin": { member_id: "member-admin", proposal_id: compromiseProposal },
          },
          child_mission: { id: "r29-resolved-child" },
        }),
      });
    });

    await page.route("**/api/v1/journeys/*/missions/r29-resolved-child/resume", async (route) => {
      stage = 5;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          run: {
            run_id: "r29-final-run",
            mission_id: "r29-resolved-child",
            provider_key: "hermes",
            model_key: "test",
            status: "WAITING_FOR_APPROVAL",
            outcome: "waiting",
            failure_reason: null,
            tool_steps: [],
            completion_contract: { kind: "APPROVAL_PENDING" },
          },
        }),
      });
    });

    await page.route("**/api/v1/journeys/*/agent/approvals/r29-approval/approve", async (route) => {
      approvalAuthorization = route.request().headers()["authorization"] ?? "";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          approval_id: "r29-approval",
          journey_id: "journey-from-route",
          action: "ACCEPT_REPLAN",
          target_type: "ReplanProposal",
          target_id: compromiseProposal,
          status: "CONSUMED",
          approval_method: "USER_CONFIRMATION",
          approved_by: "traveler-owner",
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 60_000).toISOString(),
          approved_at: new Date().toISOString(),
          consumed_at: new Date().toISOString(),
          continuation: {
            status: "RESUMED",
            pending_action_id: "r29-pending",
            run_id: "r29-final-run",
            mission_id: "r29-resolved-child",
            replayed: false,
          },
        }),
      });
    });

    await page.getByTestId("v18-copilot-dock").locator(".cn-copilot-edge").click();
    await expect(page.getByTestId("collective-decision")).toBeVisible();

    // Round 1 ends in explicit disagreement. The mediator auto-resumes and
    // returns a genuinely changed decision surface; no proposal is a winner.
    await page.getByTestId("collective-option").first().getByRole("button").click();
    await expect(page.locator(".cn-collective-notice")).toContainText(/mediating|调解|折中/i);
    await expect(page.getByTestId("collective-decision")).toBeVisible();
    await expect(page.getByTestId("collective-option")).toHaveCount(3);
    await expect(page.getByText("Craft Garden")).toBeVisible();
    await expect(page.getByText(/winner|获胜者/i)).toHaveCount(0);

    // OWNER choosing the improved compromise is not enough. The product must
    // remain in WAITING_FOR_MEMBERS and must not surface approval yet.
    await page.getByTestId("collective-option").filter({ hasText: "Craft Garden" }).getByRole("button").click();
    await expect.poll(() => round2OwnerAuthorization).toBe(`Bearer ${TOKEN}`);
    await expect(page.getByTestId("collective-progress")).toHaveText("1/2");
    await expect(page.getByTestId("collective-approval")).toHaveCount(0);

    // Switch to the ADMIN signed session, refresh the same server-owned round,
    // and require that second principal to choose the compromise independently.
    viewer = "admin";
    await page.evaluate((token) => {
      window.sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, adminToken);
    await page.getByRole("button", { name: /Refresh task status|刷新任务状态/i }).click();
    await expect(page.getByText(/ADMIN/)).toBeVisible();
    await page.getByTestId("collective-option").filter({ hasText: "Craft Garden" }).getByRole("button").click();
    await expect.poll(() => round2AdminAuthorization).toBe(`Bearer ${adminToken}`);

    // After both renewed responses, the normal governed approval boundary may
    // appear. ADMIN can see it but cannot approve an OWNER-only mutation.
    await expect(page.getByTestId("collective-approval")).toBeVisible();
    await expect(page.getByTestId("collective-approve")).toHaveCount(0);

    viewer = "owner";
    await page.evaluate((token) => {
      window.sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, TOKEN);
    await page.getByRole("button", { name: /Refresh task status|刷新任务状态/i }).click();
    await expect(page.getByTestId("collective-approve")).toBeVisible();
    await page.getByTestId("collective-approve").click();
    await expect.poll(() => approvalAuthorization).toBe(`Bearer ${TOKEN}`);
    await expect(page.locator(".cn-collective-notice")).toContainText(/resumed|继续|完成/i);
  });
});
