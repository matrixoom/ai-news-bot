import { describe, expect, it } from "vitest";
import { adaptPushConfig, toPushConfigRaw } from "../model/push-module-adapter";
import type { PushConfigRaw } from "../model/push-module.types";

const legacyConfig: PushConfigRaw = {
  selected_module_ids: ["market"],
  report_style: "newspaper",
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
};

describe("push module adapter", () => {
  it("defaults old push config payloads to one year", () => {
    expect(adaptPushConfig(legacyConfig).marketChartRange).toBe("1y");
  });

  it("serializes the selected push chart range", () => {
    const config = { ...adaptPushConfig(legacyConfig), marketChartRange: "2y" as const };
    expect(toPushConfigRaw(config).market_chart_range).toBe("2y");
  });
});
