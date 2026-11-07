import { expect, test } from "@playwright/test";
import { newUser, pickShow, prefs } from "./helpers";

test("two people in the same show see each other's holds live", async ({ browser }) => {
  const a = await (await browser.newContext()).newPage();
  const b = await (await browser.newContext()).newPage();
  for (const p of [a, b]) {
    await prefs(p, { viewMode: "2d" });
    await newUser(p);
  }
  const showId = await pickShow(a, 5);
  await a.goto(`/seats/?show=${showId}`);
  await b.goto(`/seats/?show=${showId}`);

  const seat = a.getByRole("gridcell", { name: /, available/ }).nth(25);
  const label = (await seat.getAttribute("aria-label"))!.split(",")[0];
  await seat.click();
  await expect(a.getByRole("gridcell", { name: new RegExp(`^${label}, .*selected by you`) })).toBeVisible();
  // B never refreshed - the websocket did it
  await expect(b.getByRole("gridcell", { name: new RegExp(`^${label}, .*held by someone else`) })).toBeVisible({ timeout: 5000 });

  await a.getByRole("gridcell", { name: new RegExp(`^${label},`) }).click(); // release
  await expect(b.getByRole("gridcell", { name: new RegExp(`^${label}, .*available`) })).toBeVisible({ timeout: 5000 });
});
