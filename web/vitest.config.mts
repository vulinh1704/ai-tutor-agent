import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Set up as in the Next.js testing guide (Vitest + React Testing Library + jsdom), with
// Vite's native tsconfig path resolution for the "@/..." imports.
export default defineConfig({
  plugins: [react()],
  resolve: { tsconfigPaths: true },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
