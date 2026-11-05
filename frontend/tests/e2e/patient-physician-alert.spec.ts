import { createHmac } from "node:crypto";
import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const apiBase = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://localhost:8000";
const password = "Synthetic-demo-password-2026";

function b64url(value: string | Buffer): string { return Buffer.from(value).toString("base64url"); }
function bootstrapToken(userId: string, role: "physician" | "admin"): string {
  const header = b64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = b64url(JSON.stringify({ sub: userId, role, mfa: true, exp: Math.floor(Date.now() / 1000) + 300, iat: Math.floor(Date.now() / 1000) }));
  const signature = createHmac("sha256", "development-only-change-me-before-any-deployment").update(`${header}.${payload}`).digest("base64url");
  return `${header}.${payload}.${signature}`;
}
function totp(secret: string): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"; let bits = "";
  for (const letter of secret.replace(/=+$/, "")) bits += alphabet.indexOf(letter).toString(2).padStart(5, "0");
  const raw = Buffer.from(bits.match(/.{8}/g)?.map((byte) => String.fromCharCode(Number.parseInt(byte, 2))).join("") ?? "", "binary");
  const counter = Math.floor(Date.now() / 1000 / 30); const bytes = Buffer.alloc(8); bytes.writeBigUInt64BE(BigInt(counter));
  const digest = createHmac("sha1", raw).update(bytes).digest(); const offset = digest[digest.length - 1] & 15;
  return (((digest.readUInt32BE(offset) & 0x7fffffff) % 1_000_000).toString().padStart(6, "0"));
}
async function post(path: string, body: unknown, headers: Record<string, string> = {}): Promise<Record<string, string>> {
  const response = await fetch(`${apiBase}${path}`, { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body) });
  if (!response.ok) throw new Error(`${path}: ${response.status} ${await response.text()}`);
  return response.status === 204 ? {} : await response.json() as Record<string, string>;
}
async function activatePrivilegedAccount(userId: string, role: "physician" | "admin"): Promise<string> {
  const token = bootstrapToken(userId, role);
  const enrollment = await post("/api/v1/auth/mfa/enroll", {}, { Authorization: `Bearer ${token}` });
  const secret = new URL(enrollment.provisioning_uri).searchParams.get("secret"); if (!secret) throw new Error("Synthetic MFA enrollment did not return a secret");
  await post("/api/v1/auth/mfa/verify", { code: totp(secret) }, { Authorization: `Bearer ${token}` });
  return secret;
}

test("synthetic patient alert is acknowledged by an authorized physician", async ({ page }) => {
  test.setTimeout(150_000);
  const authWindowStart = Date.now();
  const suffix = `${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
  const patient = await post("/api/v1/auth/register", { email: `synthetic.patient.${suffix}@example.com`, password, display_name: `Synthetic Patient ${suffix}` });
  const physician = await post("/api/v1/auth/provision", { email: `synthetic.physician.${suffix}@example.com`, password, role: "physician", registration_no: `SYN-E2E-${suffix}` }, { "X-Provisioning-Key": "development-only-admin-provisioning-key" });
  const admin = await post("/api/v1/auth/provision", { email: `synthetic.admin.${suffix}@example.com`, password, role: "admin" }, { "X-Provisioning-Key": "development-only-admin-provisioning-key" });
  const physicianSecret = await activatePrivilegedAccount(physician.id, "physician");
  const adminSecret = await activatePrivilegedAccount(admin.id, "admin");
  const consent = await post("/api/v1/consents", { purpose: "monitoring", version: "synthetic-e2e-v1" }, { Authorization: `Bearer ${patient.access_token}` });
  const patientId = (await (await fetch(`${apiBase}/api/v1/patients/me`, { headers: { Authorization: `Bearer ${patient.access_token}` } })).json()).id as string;
  const adminLogin = await post("/api/v1/auth/login", { email: `synthetic.admin.${suffix}@example.com`, password, totp_code: totp(adminSecret) });
  await post("/api/v1/admin/assignments", { patient_id: patientId, physician_id: physician.physician_id, consent_id: consent.id }, { Authorization: `Bearer ${adminLogin.access_token}` });

  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("/login"); await page.getByLabel("Email").fill(`synthetic.patient.${suffix}@example.com`); await page.getByLabel("Password", { exact: true }).fill(password); await page.waitForTimeout(100); await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Your monitoring home" })).toBeVisible();
  // 53 is an unreviewed synthetic fixture boundary (<54), not a clinical recommendation.
  await page.getByRole("textbox", { name: "Glucose" }).fill("53"); await page.getByRole("button", { name: "Save readings" }).click();
  await expect(page.getByRole("status")).toContainText("Reading submitted"); await page.reload();
  await expect(page.getByText("Urgent synthetic-demo alert", { exact: false })).toBeVisible();
  await expect(new AxeBuilder({ page }).analyze()).resolves.toMatchObject({ violations: [] });
  await expect(page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).resolves.toBeTruthy();
  await page.getByRole("link", { name: "Meal photos" }).click();
  await page.locator("#meal-photo").setInputFiles({
    name: "synthetic-meal.png", mimeType: "image/png",
    buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAEklEQVR4nGPkUbJgYGBgYgADAATGAGqWLTkEAAAAAElFTkSuQmCC", "base64"),
  });
  await page.getByRole("button", { name: "Upload for review" }).click();
  await expect(page.getByRole("status")).toContainText("submitted for optional physician review");

  // Preserve the configured auth limit: the setup intentionally uses a full rate window.
  await page.waitForTimeout(Math.max(0, 61_000 - (Date.now() - authWindowStart)));
  await page.getByRole("button", { name: "Log out" }).click(); await page.getByLabel("Email").fill(`synthetic.physician.${suffix}@example.com`); await page.getByLabel("Password", { exact: true }).fill(password); await page.getByRole("button", { name: "Physician", exact: false }).click(); await page.getByLabel("MFA code (if required)").fill(totp(physicianSecret)); await page.waitForTimeout(100); await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Physician overview" })).toBeVisible(); await expect(page.getByText("urgent", { exact: false })).toBeVisible();
  await page.getByRole("link", { name: `Synthetic Patient ${suffix}` }).click(); await page.getByRole("button", { name: "Acknowledge alert" }).click(); await expect(page.getByRole("status")).toContainText("acknowledged");
  await expect(page.getByRole("heading", { name: "Meal-photo review" })).toBeVisible();
  await page.getByLabel("Add a non-clinical comment").fill("Synthetic optional review comment.");
  await page.getByRole("button", { name: "Add comment" }).click();
  await expect(page.getByText("Comment added.", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click(); await page.getByLabel("Email").fill(`synthetic.patient.${suffix}@example.com`); await page.getByLabel("Password", { exact: true }).fill(password); await page.waitForTimeout(100); await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Your monitoring home" })).toBeVisible();
  await page.getByRole("link", { name: "Meal photos" }).click();
  await expect(page.getByText("Synthetic optional review comment.")).toBeVisible();
});
