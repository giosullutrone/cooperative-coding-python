import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    root: ".",
    include: ["tests/**/*.test.ts"],
  },
  resolve: {
    alias: {
      obsidian: "./tests/__mocks__/obsidian.ts",
    },
  },
});
