import { expect, test } from "@playwright/test";

test("home links to patient-only synthetic registration", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Explore as a patient" }).click();
  await expect(page.getByRole("heading", { name: "Create your demo account." })).toBeVisible();
  await expect(page.getByText("Physician accounts are provisioned separately.")).toBeVisible();
  await page.getByLabel("Fictional display name").fill("Synthetic Demo Patient");
  await page.getByLabel("Demo email").fill(`synthetic.local.${Date.now()}@example.com`);
  await page.getByLabel("Password (at least 12 characters)").fill("Synthetic-test-password-2026");
  await page.getByRole("button", { name: "Create patient account" }).click();
  await expect(page.getByRole("heading", { name: "Your monitoring home" })).toBeVisible();
});
