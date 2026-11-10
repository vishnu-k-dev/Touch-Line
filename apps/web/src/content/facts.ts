/**
 * Numbers shown on the site. Every one was measured in this repository (see docs/architecture.md).
 * Update them when the code changes; the README and the About page both read from here.
 */
export const FACTS = {
  matches: 5,
  events: 19442,
  documents: 156,
  tools: 8,
  apiTests: 129,
  unitTests: 15,
  e2eTests: 30,
  retrievalRecall: 1.0,
  retrievalQuestions: 20,
  momentHitRate: 1.0,
  teamPlayersOnPitch: 11,
  blockedShotsChecked: 25,
  blockedShotsZeroDefenders: 11,
  apiMemoryMiB: 345,
  firstRunRecall: 0.9,
};

/**
 * Headline accuracy of the analyst against its golden questions. null until the eval has been run against a live model:
 *   cd apps/api && python -m app.evals.agent_eval --out eval.json
 */
export const ANALYST_EVAL: null | { model: string; passRate: number; grounded: number; costPerQuestionUsd: number } = null;
