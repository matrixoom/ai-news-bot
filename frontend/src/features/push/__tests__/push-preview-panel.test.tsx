import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PushPreviewPanel } from "../components/push-preview-panel";

describe("PushPreviewPanel", () => {
  it("expands the iframe height to fit the rendered report content", async () => {
    render(
      <PushPreviewPanel
        preview={{
          ok: true,
          generatedAt: "2026-04-14T08:00:00Z",
          subject: "Market Daily",
          textBody: "",
          htmlBody: "<html><body><div style='height: 1600px;'>preview</div></body></html>",
          style: "newspaper",
          selectedModuleIds: ["market"],
          error: "",
        }}
        refreshAfterMs={30000}
      />,
    );

    const iframe = screen.getByTitle("Push preview");
    Object.defineProperty(iframe, "contentDocument", {
      configurable: true,
      value: {
        body: { scrollHeight: 1580 },
        documentElement: { scrollHeight: 1624 },
      },
    });

    fireEvent.load(iframe);

    await waitFor(() => {
      expect(iframe).toHaveStyle({ height: "1648px" });
    });
  });
});
