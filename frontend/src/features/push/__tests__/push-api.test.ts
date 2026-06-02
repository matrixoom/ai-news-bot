import { afterEach, describe, expect, it, vi } from "vitest";
import { previewPush } from "../api/preview-push";
import { adaptPushConfig } from "../model/push-module-adapter";
import type { PushConfigRaw } from "../model/push-module.types";

const rawConfig = {
  selected_module_ids: ["market"],
  report_style: "newspaper",
  market_chart_range: "2y",
  email: {
    enabled: true,
    label: "Primary Email",
    smtp_server: "smtp.example.com",
    smtp_port: 587,
    use_tls: true,
    username: "",
    password: "",
    from_address: "",
    to_addresses: "",
  },
  schedules: [],
} satisfies PushConfigRaw;

describe("previewPush", () => {
  afterEach(() => vi.restoreAllMocks());

  it("requests a local redraw without refreshing external data", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        generated_at: "2026-06-01T00:00:00Z",
        config: rawConfig,
        preview: {
          ok: true,
          generated_at: "2026-06-01T00:00:00Z",
          subject: "Market Daily",
          text_body: "",
          html_body: "<p>preview</p>",
          style: "newspaper",
          market_chart_range: "2y",
          selected_module_ids: ["market"],
        },
      }), { status: 200, headers: { "Content-Type": "application/json" } }),
    );

    await previewPush(adaptPushConfig(rawConfig), { refreshData: false });

    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toMatchObject({
      config: { market_chart_range: "2y" },
      refresh_data: false,
    });
  });
});
