import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    // The api from `docker compose -f compose.yaml -f compose.dev.yaml up` (or `uv run astrocat serve`).
    proxy: { "/api": "http://localhost:8000" },
  },
  build: { target: "es2022" },
  test: { environment: "node" },
});
