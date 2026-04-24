import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("Frontend document title", () => {
  it("uses Trend Insight as the browser tab title", () => {
    const html = readFileSync(resolve(process.cwd(), "index.html"), "utf-8");

    expect(html).toContain("<title>Trend Insight</title>");
    expect(html).not.toContain("<title>AI News Bot</title>");
  });
});
