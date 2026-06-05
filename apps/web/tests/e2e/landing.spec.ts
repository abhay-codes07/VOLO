import { expect, test } from "@playwright/test";

test("landing page shows the Volo hero + trajectory canvases", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Volo/i);
  await expect(page.getByText(/Mission control/i)).toBeVisible();
  // At least one trajectory canvas SVG renders.
  await expect(page.locator("svg").first()).toBeVisible();
});

test("login page reachable and shows Continue button", async ({ page }) => {
  await page.goto("/auth/login");
  await expect(page.getByRole("button", { name: /CONTINUE WITH GITHUB/i })).toBeVisible();
});
