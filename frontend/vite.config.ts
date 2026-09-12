/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Offline is not a stretch feature here — it is the thesis (CLAUDE.md:
    // "reasoning runs onshore, answers survive offshore"). The service worker
    // caches the app shell and static assets; shared/offline/db.ts (Dexie)
    // separately persists the codebook, recent capsules and cached field
    // readings, which is the data a boat actually needs with zero network.
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icon.svg"],
      manifest: {
        name: "DHRUVA — Marine Advisory",
        short_name: "DHRUVA",
        description:
          "Deep-sea Hazard, Routing & Understanding via Vernacular Agents — ISRO PS 26176",
        theme_color: "#0b3d5c",
        background_color: "#0b3d5c",
        display: "standalone",
        icons: [{ src: "icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any maskable" }],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,ico}"],
        // Map tiles for the coastal demo window are cached at runtime rather
        // than pre-cached — the boat surface only needs the window it has
        // actually been shown, per IMPLEMENTATION.md Phase 5.
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/demotiles\.maplibre\.org\/.*/i,
            handler: "CacheFirst",
            options: {
              cacheName: "dhruva-map-tiles",
              expiration: { maxEntries: 400, maxAgeSeconds: 60 * 60 * 24 * 14 },
            },
          },
        ],
      },
    }),
  ],
  // maplibre-gl ships its own web worker bundle; letting esbuild's dev-mode
  // dependency pre-bundling touch it breaks that worker's module resolution
  // (a documented maplibre-gl/Vite interaction, not a bug in our code) —
  // the map silently never fires "load" and no tile request is ever made.
  optimizeDeps: {
    exclude: ["maplibre-gl"],
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    css: false,
  },
});
