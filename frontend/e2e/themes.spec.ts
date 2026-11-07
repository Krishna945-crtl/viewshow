import { expect, test } from "@playwright/test";
import { deflateSync } from "node:zlib";
import { API, prefs } from "./helpers";

/** A tiny solid-colour PNG, built by hand so the test needs no image files. */
function solidPng(hex: string, w = 24, h = 36) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const crcTable = Array.from({ length: 256 }, (_, n) => {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  });
  const crc = (buf: Buffer) => {
    let c = 0xffffffff;
    for (const byte of buf) c = crcTable[(c ^ byte) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  };
  const chunk = (type: string, data: Buffer) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const body = Buffer.concat([Buffer.from(type), data]);
    const sum = Buffer.alloc(4); sum.writeUInt32BE(crc(body));
    return Buffer.concat([len, body, sum]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2;
  const row = Buffer.concat([Buffer.from([0]), Buffer.from(Array.from({ length: w }, () => [r, g, b]).flat())]);
  const raw = Buffer.concat(Array.from({ length: h }, () => row));
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), chunk("IHDR", ihdr),
    chunk("IDAT", deflateSync(raw)), chunk("IEND", Buffer.alloc(0))]);
}

test("Theme Lab designs a hall for a movie it has never seen", async ({ page }) => {
  await prefs(page, {});
  await page.goto("/lab/");
  await page.getByLabel("Title").fill("Temple Run Saga");
  await page.getByLabel("Genres").fill("Fantasy, Action");
  await page.getByLabel("Synopsis").fill("A village priest guards an ancient temple and its sacred deity from a demon.");
  await page.getByRole("button", { name: "Generate atmosphere" }).click();

  await expect(page.getByRole("heading", { name: "Temple Run Saga (auto)" })).toBeVisible();
  await expect(page.getByText("Mythic", { exact: true })).toBeVisible();
  await expect(page.getByText(/story 'deity'/)).toBeVisible();

  // a poster's colours take over the palette
  await page.getByLabel(/Poster \(optional/).setInputFiles({ name: "p.png", mimeType: "image/png", buffer: solidPng("#1e6fd9") });
  await expect(page.getByLabel("Extracted colours")).toBeVisible();
  await page.getByRole("button", { name: "Generate atmosphere" }).click();
  await expect(page.getByText("Colours taken from the poster")).toBeVisible();
});

test("admin uploads key art and the movie's theme follows it", async ({ page }) => {
  const r = await page.request.post(`${API}/auth/login`, { data: { email: "admin@cineverse.dev", password: "Admin@123" } });
  const body = await r.json();
  await prefs(page, {});
  await page.evaluate((s) => localStorage.setItem("cv.session", JSON.stringify(s)),
    { access: body.access_token, refresh: body.refresh_token, user: body.user });

  // a throwaway movie so reruns don't stack colours on a seeded one
  const title = `E2E Art ${Date.now()}`;
  const created = await page.request.post(`${API}/admin/movies`, {
    headers: { Authorization: `Bearer ${body.access_token}` }, data: { title, genres: ["Drama"] },
  });
  expect(created.ok()).toBeTruthy();
  const movieId = (await created.json()).id as string;

  await page.goto("/admin/");
  await page.getByRole("tab", { name: "movies" }).click();
  await page.getByRole("button", { name: new RegExp(title) }).click();
  await expect(page.getByRole("heading", { name: "Why this look?" })).toBeVisible();

  await page.getByLabel("Poster image").setInputFiles({ name: "art.png", mimeType: "image/png", buffer: solidPng("#ff3fa4") });
  await page.getByRole("button", { name: "Upload" }).click();
  await expect(page.getByText("Poster colours applied to the theme")).toBeVisible();
  await expect(page.getByText("Colours taken from the poster")).toBeVisible();

  // archive it so reruns don't fill the catalogue with test films
  await page.request.delete(`${API}/admin/movies/${movieId}`, { headers: { Authorization: `Bearer ${body.access_token}` } });
});
