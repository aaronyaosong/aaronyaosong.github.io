import { test, expect } from "@playwright/test";


test("homepage renders coffees from latest snapshot", async ({ page }) => {
  await page.goto("/index.html");

  await expect(page.getByRole("heading", { name: "What coffee is available right now in NZ?" })).toBeVisible();
  await expect(page.locator(".card").first()).toBeVisible();
  await expect(page.locator("#resultCount")).toContainText("result");
});