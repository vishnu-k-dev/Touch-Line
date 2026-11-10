import { expect, test } from "@playwright/test";

test.describe("how it works", () => {
  test("explains the stack, the pipeline, the numbers and the limits", async ({ page }) => {
    await page.goto("/about");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Under the hood");
    for (const h of ["The Starting XI", "One question, five touches", "The VAR check", "Search by meaning, filter by fact", "What I measured", "Offside lines"]) {
      await expect(page.getByRole("heading", { name: h })).toBeVisible();
    }
    await expect(page.getByText("Event data only.")).toBeVisible();
    await expect(page.getByText(/On nine golden questions/)).toBeVisible();
    await expect(page.getByText(/Nine questions is a smoke test, not a benchmark/)).toBeVisible(); // honest about how little it proves
  });

  test("hovering a player in the starting XI shows what that piece does", async ({ page }) => {
    await page.goto("/about#stack");
    await page.getByRole("button", { name: /^7, Search \(RAG\)/ }).hover();
    await expect(page.getByRole("heading", { name: "Search (RAG)" })).toBeVisible();
    await expect(page.getByText("apps/api/app/services/rag.py")).toBeVisible();
    await page.getByRole("button", { name: /^1, PostgreSQL/ }).focus();
    await expect(page.getByRole("heading", { name: "PostgreSQL + pgvector" })).toBeVisible();
  });

  test("the VAR demo lets a real number stand, derives a gap, and rejects a made-up one", async ({ page }) => {
    await page.goto("/about#var");
    const claim = page.getByLabel("Claimed xG for Argentina");
    await expect(page.getByText("VAR: goal stands")).toBeVisible();
    await page.getByRole("button", { name: /3\.5 made up/ }).click();
    await expect(claim).toHaveValue("3.5");
    await expect(page.getByText("VAR: no goal")).toBeVisible();
    await expect(page.getByText("3.5 does not appear in the cited tool results.")).toBeVisible();
    await claim.fill("2.34");
    await expect(page.getByText("VAR: goal stands")).toBeVisible();
    await expect(page.getByText(/2\.34 = 2\.49 − 0\.15/)).toBeVisible();
    await claim.fill("");
    await expect(page.getByText("Type a number.")).toBeVisible();
  });

  test("the on-page links jump to their sections", async ({ page }) => {
    await page.goto("/about");
    await page.getByRole("navigation", { name: "On this page" }).getByRole("link", { name: "Offside lines" }).click();
    await expect(page).toHaveURL(/#limits$/);
    await expect(page.getByRole("heading", { name: "Offside lines" })).toBeInViewport();
  });

  test("the header marks the current page", async ({ page }) => {
    await page.goto("/about");
    await expect(page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "How it works" })).toHaveAttribute("aria-current", "page");
    await page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "Match Centre" }).click();
    await expect(page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "Match Centre" })).toHaveAttribute("aria-current", "page");
  });
});
