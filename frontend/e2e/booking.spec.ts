import { expect, test } from "@playwright/test";
import { newUser, pickShow, prefs } from "./helpers";

test("browse -> pick seat in 2D -> view from seat -> pay (sandbox) -> ticket", async ({ page }) => {
  await prefs(page, { viewMode: "2d" });
  await newUser(page);

  await page.goto("/home/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const showId = await pickShow(page, 1);

  await page.goto(`/seats/?show=${showId}`);
  const seat = page.getByRole("gridcell", { name: /, available/ }).nth(40);
  const label = (await seat.getAttribute("aria-label"))!.split(",")[0];
  await seat.click();
  await expect(page.getByRole("gridcell", { name: new RegExp(`^${label}, .*selected by you`) })).toBeVisible();
  await expect(page.getByText(/1 seat ·/)).toBeVisible();

  // view from my seat flips to 3D and shows the seated banner
  await page.getByRole("button", { name: "👁 View from seat" }).click();
  await expect(page.getByText(`Seated view · ${label}`)).toBeVisible();
  await expect(page.locator("canvas")).toBeVisible();
  await page.getByRole("button", { name: /Exit view from/ }).click();

  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("heading", { name: "Booking summary" })).toBeVisible();
  await page.getByRole("button", { name: /^Pay/ }).click();
  await expect(page.getByText("Sandbox · no real money moves")).toBeVisible();
  await page.getByRole("button", { name: /\(success\)/ }).click();

  await expect(page.getByRole("article", { name: "Digital ticket" })).toBeVisible();
  await expect(page.getByText(label, { exact: false }).first()).toBeVisible();
  await expect(page.locator("svg title", { hasText: "Ticket QR" })).toHaveCount(1);
});

test("declined card keeps the seats held so the user can retry", async ({ page }) => {
  await prefs(page, { viewMode: "2d" });
  await newUser(page);
  await page.goto(`/seats/?show=${await pickShow(page, 2)}`);
  await page.getByRole("gridcell", { name: /, available/ }).nth(10).click();
  await expect(page.getByText(/1 seat ·/)).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: /^Pay/ }).click();
  await page.getByRole("button", { name: "Simulate card decline" }).click();
  await expect(page.getByText(/didn't go through/)).toBeVisible();
  await expect(page.getByRole("button", { name: /^Pay/ })).toBeEnabled();
});

test("2D map is keyboard navigable", async ({ page }) => {
  await prefs(page, { viewMode: "2d" });
  await page.goto(`/seats/?show=${await pickShow(page, 3)}`);
  const first = page.locator('[role="gridcell"][tabindex="0"]');
  await first.focus();
  const before = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
  await page.keyboard.press("ArrowRight");
  const after = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
  expect(after).not.toEqual(before);
  await page.keyboard.press("ArrowDown");
  const down = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
  expect(down?.[0]).not.toEqual(after?.[0]); // moved to another row
});

test("3D auditorium renders and switches viewpoints", async ({ page }) => {
  await prefs(page, { viewMode: "3d" });
  await page.goto(`/seats/?show=${await pickShow(page, 4)}`);
  await expect(page.locator("canvas")).toBeVisible({ timeout: 20_000 });
  for (const v of ["Back row", "Side", "From stage", "Overview"]) await page.getByRole("button", { name: v, exact: true }).click();
  await expect(page.getByRole("button", { name: "Overview", exact: true })).toHaveAttribute("aria-pressed", "true");
});
