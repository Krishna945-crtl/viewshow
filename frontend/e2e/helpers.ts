import { expect, type Page } from "@playwright/test";

export const API = process.env.E2E_API_URL || "http://localhost:8000/api";

export async function prefs(page: Page, p: Record<string, unknown>) {
  await page.goto("/");
  await page.evaluate((v) => localStorage.setItem("cv.prefs", JSON.stringify({ onboarded: true, ...v })), p);
}

export async function newUser(page: Page) {
  const email = `e2e${Date.now()}${Math.floor(Math.random() * 1e4)}@example.com`;
  const r = await page.request.post(`${API}/auth/register`, { data: { email, password: "Passw0rd!", full_name: "E2E Tester" } });
  expect(r.ok()).toBeTruthy();
  const body = await r.json();
  await page.evaluate((s) => localStorage.setItem("cv.session", JSON.stringify(s)),
    { access: body.access_token, refresh: body.refresh_token, user: body.user });
  return body;
}

/** A future show in a big auditorium, picked fresh so tests don't fight over seats. */
export async function pickShow(page: Page, index = 0) {
  const movies = await (await page.request.get(`${API}/movies`)).json();
  const st = await (await page.request.get(`${API}/movies/${movies[index % movies.length].slug}/showtimes`)).json();
  const shows = st.theatres.flatMap((t: { shows: { id: string; auditorium: { name: string } }[] }) => t.shows);
  return (shows.find((s: { auditorium: { name: string } }) => s.auditorium.name.includes("Grand")) ?? shows[0]).id as string;
}
