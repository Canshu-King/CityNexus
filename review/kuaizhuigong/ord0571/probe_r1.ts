import { dictionaryCopy } from "../../../frontend/src/i18n/LocaleContext";

const KEYS = [
  "main.cityNexusRequestFailed",
  "main.cityNexusRequestRefusedHttp",
  "main.persistedOperationUpdate",
  "main.generalRecovery",
  "main.activateAStandingMissionOnceSubsequentCitySignalsCanLaunchRecoveryWithoutANewChatMessage",
  "main.noDominantFailureMode",
  "main.notEvaluated",
  "main.validatedActivity",
  "main.noActionableTarget",
  "main.outcomeEvidence",
  "main.explicitWins",
  "main.notReported",
  "main.noUpcomingActivity",
  "main.noActiveC4",
  "main.notAvailable",
  "main.verifiedFeasible",
  "main.notFeasible",
  "main.notPreserved",
  "main.verifiedEvidenceAttached",
  "main.evidenceUnavailable",
  "recovery.noDominantMode",
  "recovery.noneOnThisJourney",
];

for (const key of KEYS) {
  console.log(`zh | ${key} | ${dictionaryCopy("zh-CN", key)}`);
  console.log(`en | ${key} | ${dictionaryCopy("en", key)}`);
}
