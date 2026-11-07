import type { CapacitorConfig } from "@capacitor/cli";

// The static Next.js export in ./out is the whole app - the same build runs
// in the browser, on Android and on iOS. Point NEXT_PUBLIC_API_URL at a
// reachable API before `npm run cap:sync` (a phone can't reach "localhost").
const config: CapacitorConfig = {
  appId: "dev.cineverse.app",
  appName: "CineVerse 3D",
  webDir: "out",
  backgroundColor: "#07070b",
  android: { allowMixedContent: false },
  ios: { contentInset: "always" },
};

export default config;
