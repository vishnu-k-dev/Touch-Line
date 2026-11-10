import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

// A real analyst response (scripted model, real database and event ids), so the UI is tested against the true schema.
const answer = JSON.parse(readFileSync(path.join(__dirname, "fixtures", "analyst-answer.json"), "utf-8"));
const SAUDI = 3857300; // Argentina 1-2 Saudi Arabia

async function mockAnalyst(page: Page, chat: object | { status: number; json: object }, history: object[] = []) {
  await page.route("**/api/v1/analyst/status", (r) => r.fulfill({ json: { configured: true, provider: "openai", model: "gpt-5.6-luna" } }));
  await page.route("**/api/v1/analyst/history**", (r) => (r.request().method() === "DELETE" ? r.fulfill({ json: { deleted: history.length } }) : r.fulfill({ json: history })));
  await page.route("**/api/v1/analyst/chat", (r) =>
    "status" in chat && typeof chat.status === "number" && "json" in chat ? r.fulfill({ status: chat.status, json: chat.json }) : r.fulfill({ json: chat }),
  );
}
const goToMatch = (page: Page, tab: string, match = SAUDI) => page.goto(`/#match=${match}&tab=${tab}`);

test.describe("home", () => {
  test("opens with the hero, the pitch animation, and the headline numbers", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Read the game.");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("workings.");
    await expect(page.getByRole("img", { name: /illustrated attacking move/i })).toBeVisible();
    await expect(page.getByText("Match events logged")).toBeVisible();
    await expect(page.getByText("19,442")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Why you can trust the answer" })).toBeAttached();
  });

  test("the call to action scrolls to the Match Centre; the other goes to the About page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /Open the Match Centre/ }).click();
    await expect(page).toHaveURL(/#match-centre$/);
    await expect(page.getByRole("heading", { name: "Pick a fixture" })).toBeInViewport();
    await page.goto("/");
    await page.getByRole("link", { name: /How it works/ }).first().click();
    await expect(page).toHaveURL(/\/about$/);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Under the hood");
  });

  test("an unknown page is offside", async ({ page }) => {
    await page.goto("/not-a-real-page");
    await expect(page.getByRole("heading", { name: "Offside!" })).toBeVisible();
    await page.getByRole("link", { name: /Back to the Match Centre/ }).click();
    await expect(page).toHaveURL(/localhost:3000\/$/);
  });
});

test.describe("match centre", () => {
  test("lists the five fixtures as tickets with the xG story", async ({ page }) => {
    await page.goto("/");
    const nav = page.getByRole("navigation", { name: "Matches" });
    await expect(nav.getByRole("button")).toHaveCount(5);
    await expect(nav.getByText("Argentina had more xG (2.49 v 0.15) but lost")).toBeVisible();
    await expect(nav.getByText(/level after extra time, decided on penalties/)).toHaveCount(2);
  });

  test("selecting a fixture updates the scoreboard, the stats and the URL", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("navigation", { name: "Matches" }).getByRole("button", { name: /Germany/ }).click();
    await expect(page).toHaveURL(/match=3857284/);
    await expect(page.getByRole("region", { name: "Scoreboard" })).toContainText("Germany");
    await expect(page.getByText("Expected goals (xG)")).toBeVisible();
    await expect(page.getByText("2.77", { exact: true }).first()).toBeVisible();
    await page.getByText("How each number is defined").click();
    await expect(page.getByText(/Passes allowed per defensive action/)).toBeVisible();
  });

  test("a deep link opens the right match and tab, and arrow keys move between tabs", async ({ page }) => {
    await page.goto(`/#match=3869685&tab=players`);
    await expect(page.getByRole("tab", { name: /Squad Sheet/ })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("cell", { name: /Lionel Messi/ })).toBeVisible();
    await page.getByRole("tab", { name: /Squad Sheet/ }).focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: /Heat Check/ })).toHaveAttribute("aria-selected", "true");
    await expect(page).toHaveURL(/tab=heatmaps/);
  });

  test("shot map draws every shot, filters to goals, and shows 360 context on keyboard focus", async ({ page }) => {
    await goToMatch(page, "shots");
    const dots = page.locator('svg[role="img"] g[role="button"]');
    await expect(dots).toHaveCount(18); // 15 + 3, penalty shootout excluded
    await page.getByLabel("Goals only").check();
    await expect(dots).toHaveCount(3);
    await dots.first().focus();
    await expect(page.getByText(/360 freeze-frame:/)).toBeVisible();
    await expect(page.getByText("Event id", { exact: true })).toBeVisible();
  });

  test("squad sheet: Messi leads on xG, shows minutes, and links to his heat check", async ({ page }) => {
    await goToMatch(page, "players");
    const firstRow = page.getByRole("row").nth(1);
    await expect(firstRow).toContainText("Lionel Messi");
    await expect(firstRow).toContainText("1.07");
    await expect(firstRow).toContainText("110");
    await firstRow.getByRole("button", { name: "Heatmap" }).click();
    await expect(page).toHaveURL(/tab=heatmaps/);
    await expect(page.getByLabel("Player")).toHaveValue(/\d+/);
  });

  test("heat check: narrowing from the team to one player changes the total", async ({ page }) => {
    await goToMatch(page, "heatmaps");
    const total = page.locator("p[aria-live='polite']").filter({ hasText: /events$/ });
    await expect(total).toHaveText("1953 events"); // Argentina, all on-ball actions
    await page.getByLabel("Player").selectOption({ label: "Lionel Messi (110′)" });
    await expect(total).not.toHaveText("1953 events");
    await expect(total).toHaveText(/^\d+ events$/);
    await page.getByLabel("Show").selectOption("pressures");
    await expect(total).toHaveText(/^\d+ events$/);
  });

  test("heat check is red where it is busiest, never green, and hovering reads out a square", async ({ page }) => {
    await goToMatch(page, "heatmaps");
    const cells = page.getByTestId("heat-cell");
    await expect(cells.first()).toBeVisible();
    const data = await cells.evaluateAll((els) =>
      els.map((e) => ({ count: Number(e.getAttribute("data-count")), fill: e.getAttribute("fill") ?? "" })),
    );
    const hue = (fill: string) => Number(/hsl\((\d+)/.exec(fill)?.[1] ?? "999");
    const max = Math.max(...data.map((d) => d.count));
    expect(data.filter((d) => d.count === max).every((d) => hue(d.fill) === 0)).toBe(true); // the busiest square is pure red
    expect(data.every((d) => hue(d.fill) <= 40)).toBe(true); // everything sits between amber and red: no green
    await cells.first().hover();
    await expect(page.getByText(/events · \d+–\d+ yards upfield/)).toBeVisible();
  });
});

test.describe("analyst", () => {
  test("a verified answer shows VAR badges, inference, limitations and the tool trace", async ({ page }) => {
    await mockAnalyst(page, answer);
    await goToMatch(page, "analyst");
    await page.getByRole("button", { name: /Why did Argentina create more chances/ }).click();
    await expect(page.getByText("VAR: goal stands")).toHaveCount(3);
    await expect(page.getByText("Inference (not measured, may be wrong)")).toBeVisible();
    await expect(page.getByText("One match is a small sample.")).toBeVisible();
    await page.getByText(/How it answered: 3 tool calls/).click();
    for (const tool of ["get_match_summary", "get_shot_map", "get_player_stats"]) await expect(page.getByText(tool, { exact: true })).toBeVisible();
  });

  test("an evidence chip opens that exact shot on the shot map", async ({ page }) => {
    await mockAnalyst(page, answer);
    await goToMatch(page, "analyst");
    await page.getByRole("button", { name: /Why did Argentina create more chances/ }).click();
    await page.getByRole("button", { name: "87e2e8be" }).click();
    await expect(page).toHaveURL(/tab=shots/);
    await expect(page.getByText("87e2e8be…")).toBeVisible();
    await expect(page.getByText("Outcome").locator("..")).toContainText("Goal");
  });

  test("unverified findings are flagged for review, not hidden", async ({ page }) => {
    const flagged = structuredClone(answer);
    flagged.status = "unverified";
    flagged.validation = { passed: false, violations: ["finding 1 (xG): Argentina xG=9.9 does not appear in the cited tool results"] };
    Object.assign(flagged.answer.findings[0], { verified: false, problems: ["Argentina xG=9.9 does not appear in the cited tool results"] });
    await mockAnalyst(page, flagged);
    await goToMatch(page, "analyst");
    await page.getByRole("button", { name: /Why did Argentina create more chances/ }).click();
    await expect(page.getByText("VAR: under review")).toBeVisible();
    await expect(page.getByText(/Some findings could not be checked/)).toBeVisible();
    await expect(page.getByText("VAR: goal stands")).toHaveCount(2);
  });

  test("an unconfigured server explains itself", async ({ page }) => {
    await mockAnalyst(page, { status: 503, json: { detail: "The AI analyst is not configured: set LLM_API_KEY and restart the API." } });
    await goToMatch(page, "analyst");
    await page.getByRole("button", { name: /Why did Argentina create more chances/ }).click();
    const alert = page.getByRole("alert").filter({ hasText: "VAR room is closed" }); // Next.js adds its own route-announcer alert
    await expect(alert).toContainText("LLM_API_KEY");
  });

  test("earlier questions come back after a reload, and can be cleared", async ({ page }) => {
    const earlier = [{ id: 7, match_id: SAUDI, question: "Why did Argentina lose?", created_at: "2026-11-10T10:00:00Z", result: answer }];
    await mockAnalyst(page, answer, earlier);
    await goToMatch(page, "analyst");
    await expect(page.getByText("Picked up where you left off: 1 earlier question")).toBeVisible();
    await expect(page.getByText("Why did Argentina lose?")).toBeVisible();
    await expect(page.getByText("VAR: goal stands")).toHaveCount(3);
    await page.reload();
    await expect(page.getByText("Picked up where you left off: 1 earlier question")).toBeVisible();
    const deleted = page.waitForRequest((r) => r.method() === "DELETE" && r.url().includes(`match_id=${SAUDI}`));
    await page.getByRole("button", { name: "Clear history" }).click();
    await deleted;
    await expect(page.getByText("Why did Argentina lose?")).toHaveCount(0);
    await expect(page.getByText(/Picked up where you left off/)).toHaveCount(0);
  });

  test("every analyst call carries the same anonymous visitor id, before and after a reload", async ({ page }) => {
    const seen: string[] = [];
    await mockAnalyst(page, answer);
    page.on("request", (r) => {
      const id = r.headers()["x-visitor-id"];
      if (id && r.url().includes("/analyst/")) seen.push(id);
    });
    await goToMatch(page, "analyst");
    await page.getByRole("button", { name: /Why did Argentina create more chances/ }).click();
    await expect(page.getByText("VAR: goal stands")).toHaveCount(3);
    await page.reload();
    await expect(page.getByRole("tab", { name: /Analyst/ })).toHaveAttribute("aria-selected", "true");
    await page.waitForTimeout(500);
    expect(seen.length).toBeGreaterThanOrEqual(3); // history, chat, history again
    expect(new Set(seen).size).toBe(1);
    expect(seen[0]).toMatch(/^[A-Za-z0-9_-]{8,64}$/);
  });
});

test("the page explains itself when the API is down", async ({ page }) => {
  await page.route("**/api/v1/matches", (r) => r.abort());
  await page.goto("/");
  await expect(page.getByRole("alert").filter({ hasText: "could not reach the API" })).toBeVisible();
});
