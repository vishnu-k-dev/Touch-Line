import { expect, test } from "@playwright/test";

// Regression test for a real bug: a grid track sized to its content made the whole page scroll sideways on phones.
const noSideScroll = async (page: import("@playwright/test").Page) => {
  await page.waitForTimeout(900); // let data-driven content render
  const { scroll, client } = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  expect(scroll).toBeLessThanOrEqual(client);
};

for (const tab of ["overview", "shots", "players", "heatmaps", "analyst"]) {
  test(`no horizontal page scroll on a phone: ${tab}`, async ({ page }) => {
    await page.goto(`/#match=3857300&tab=${tab}`);
    await expect(page.getByRole("tab", { name: /./ }).first()).toBeVisible();
    await noSideScroll(page);
  });
}

test("no horizontal page scroll on a phone: the hero", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await noSideScroll(page);
});

test("no horizontal page scroll on a phone: the About page", async ({ page }) => {
  await page.goto("/about");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await noSideScroll(page);
});

test("the starting XI still works by tapping on a phone", async ({ page }) => {
  await page.goto("/about#stack");
  await page.getByRole("button", { name: /^7, Search \(RAG\)/ }).tap();
  await expect(page.getByRole("heading", { name: "Search (RAG)" })).toBeVisible();
});
