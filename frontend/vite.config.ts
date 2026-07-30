import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173
  },
  test: {
    environment: "jsdom",
    exclude: ["node_modules", "dist", "tests/ui/**"],
    setupFiles: ["./src/test/setup.ts"],
    globals: true
  }
});
