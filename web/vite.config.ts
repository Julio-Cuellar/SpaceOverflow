import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [
    react(),
    {
      name: "crew-dashboard-prototype-route",
      configureServer(server) {
        server.middlewares.use((req, _res, next) => {
          if (
            ["/dashboard-tripulation", "/dashboard-tripulation/"].includes(
              req.url?.split("?")[0] ?? "",
            )
          ) {
            req.url = "/index.html";
          }
          next();
        });
      },
    },
  ],
  server: {
    // The real assistant lives in the development backend (port 8000); this way CORS is not needed.
    proxy: {
      "/dev": {
        target: process.env.SPACEAPP_ASSISTANT_PROXY || "http://127.0.0.1:8000",
        changeOrigin: true,
        timeout: 150_000,
      },
      "/graphql": {
        target: process.env.SPACEAPP_API_PROXY || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: process.env.SPACEAPP_API_PROXY || "http://127.0.0.1:8000",
        ws: true,
      },
      "/health": {
        target: process.env.SPACEAPP_API_PROXY || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/ready": {
        target: process.env.SPACEAPP_API_PROXY || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/api/v1/voice": {
        target: process.env.SPACEAPP_ASSISTANT_PROXY || "http://127.0.0.1:8000",
        changeOrigin: true,
        timeout: 150_000,
      },
      "/api": {
        target: process.env.SPACEAPP_API_PROXY || "http://127.0.0.1:8000",
        changeOrigin: true,
        timeout: 150_000,
      },
    },
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      // main.tsx solo monta la app; lo verifica el build y la prueba en navegador.
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/test/**",
        "src/main.tsx",
        "src/data/graphql/generated/**",
      ],
      thresholds: { lines: 80, functions: 80, branches: 80, statements: 80 },
    },
  },
});
