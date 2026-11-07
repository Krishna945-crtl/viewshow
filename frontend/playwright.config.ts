import { defineConfig, devices } from "@playwright/test";

// Expects the API on :8000 (seeded) and the static build served on :3000.
// See README "Running the end-to-end tests".
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  // CI runners have 2 cores and render WebGL in software; leaving the 3D seated view
  // can block the main thread for a few seconds, so the default 5s is too tight there
  expect: { timeout: process.env.CI ? 15_000 : 5_000 },
  workers: 1,
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "off",
    // PW_CHROMIUM lets CI / sandboxes point at a preinstalled browser
    launchOptions: { executablePath: process.env.PW_CHROMIUM || undefined, args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] },
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1366, height: 820 } } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
