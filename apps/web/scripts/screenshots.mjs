// Regenerates the README screenshots from a running stack (web on :3000, API on :8000):
//   cd apps/web && node scripts/screenshots.mjs
// The analyst screenshot renders a recorded response (e2e/fixtures/analyst-answer.json: a scripted run over the real
// database), because a live model call needs an API key. The README says so.
import { mkdirSync, readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const answer = JSON.parse(readFileSync("e2e/fixtures/analyst-answer.json", "utf-8"));
const out = "../../docs/img";
mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1360, height: 860 }, deviceScaleFactor: 1.5, colorScheme: "dark" });
await page.route("**/api/v1/analyst/status", (r) => r.fulfill({ json: { configured: true, provider: "openai", model: "gpt-5.6-luna" } }));
await page.route("**/api/v1/analyst/history**", (r) => r.fulfill({ json: [] }));
await page.route("**/api/v1/analyst/chat", (r) => r.fulfill({ json: answer }));
const url = (tab) => `http://localhost:3000/#match=3857300&tab=${tab}`;
const centre = async () => {
  await page.evaluate(() => document.getElementById("match-centre").scrollIntoView());
  await page.evaluate(() => window.scrollBy(0, 70));
  await page.waitForTimeout(700);
};

// hero: let the passing move reach the VAR stamp
await page.goto("http://localhost:3000/");
await page.getByRole("heading", { level: 1 }).waitFor();
await page.waitForTimeout(7200);
await page.screenshot({ path: `${out}/hero.png` });

await page.goto(url("overview"));
await page.getByText("Expected goals (xG)").waitFor();
await page.waitForTimeout(1200);
await centre();
await page.screenshot({ path: `${out}/overview.png` });

await page.goto(url("shots"));
await page.locator('svg[role="img"] g[role="button"]').first().waitFor();
await centre();
await page.locator("ul button", { hasText: "Lionel Messi" }).first().click(); // the "best chances" list
await page.getByText("Event id", { exact: true }).scrollIntoViewIfNeeded();
await page.screenshot({ path: `${out}/shot-map.png` });

await page.goto(url("heatmaps"));
await page.getByLabel("Player").selectOption({ label: "Lionel Messi (110′)" });
await page.getByTestId("heat-cell").first().waitFor();
await page.waitForTimeout(900);
await centre();
await page.evaluate(() => window.scrollBy(0, 360)); // bring the pitch into frame
await page.waitForTimeout(500);
await page.screenshot({ path: `${out}/heatmap.png` });

await page.goto(url("analyst"));
await page.getByRole("button", { name: /Why did Argentina create more chances/ }).click();
await page.getByText("Measured findings").waitFor();
await page.waitForTimeout(700);
await page.getByText("Measured findings").scrollIntoViewIfNeeded();
await page.screenshot({ path: `${out}/analyst.png` });

await page.goto("http://localhost:3000/about#stack");
await page.getByRole("button", { name: /^10, Agent loop/ }).waitFor();
await page.waitForTimeout(900);
await page.evaluate(() => document.getElementById("stack").scrollIntoView());
await page.screenshot({ path: `${out}/about-xi.png` });
await page.goto("http://localhost:3000/about#var");
await page.getByRole("button", { name: /3\.5 made up/ }).click();
await page.waitForTimeout(700);
await page.evaluate(() => document.getElementById("var").scrollIntoView());
await page.screenshot({ path: `${out}/about-var.png` });

await browser.close();
console.log("screenshots written to", out);
