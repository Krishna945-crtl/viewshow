import type { NextConfig } from "next";

// Static export so the same build ships to the web, Android and iOS (Capacitor).
// Dynamic data (movie id, show id...) lives in query params instead of route segments.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
