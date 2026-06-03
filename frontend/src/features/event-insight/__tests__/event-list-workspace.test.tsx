import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EventListWorkspace } from "../components/event-list-workspace";

const listPayload = {
  traceId: "event-insight-events-test",
  page: 1,
  pageSize: 20,
  total: 2,
  items: [
    {
      id: 1,
      title: "存储芯片报价上调",
      summary: "DRAM 合约价上涨，AI 服务器需求支撑内存涨价。",
      eventTime: "2026-05-16T10:30:00+08:00",
      eventType: "price_change",
      confidenceScore: 0.82,
      manualStatus: "active",
      analysisStatus: "extracted",
      graphStatus: "pending",
      sourceMethod: "manual",
      evidenceLevel: "B",
      topics: [{ id: 1, name: "内存涨价", roleInTopic: "key_catalyst" }],
    },
    {
      id: 2,
      title: "CPO 光模块订单增加",
      summary: "海外云厂商资本开支上修。",
      eventTime: "2026-05-20T10:30:00+08:00",
      eventType: "supply_demand",
      confidenceScore: 0.76,
      manualStatus: "active",
      analysisStatus: "extracted",
      graphStatus: "pending",
      sourceMethod: "manual",
      evidenceLevel: "C",
      topics: [],
    },
  ],
};

const detailPayload = {
  traceId: "event-insight-event-test",
  event: {
    ...listPayload.items[1],
    evidence: [
      {
        id: 11,
        excerpt: "海外云厂商资本开支上修，光模块订单增加。",
        sourceTitle: "光模块跟踪",
        sourceUrl: "https://example.com/cpo",
        evidenceLevel: "B",
        role: "primary",
      },
    ],
    topics: [],
  },
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("EventListWorkspace", () => {
  it("loads event list from API and fetches detail when selecting another row", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = resolveRequestUrl(input);
      if (url.pathname === "/api/frontend/modules/event-insight/events") {
        return jsonResponse(listPayload);
      }
      if (url.pathname === "/api/frontend/modules/event-insight/events/2") {
        return jsonResponse(detailPayload);
      }
      if (url.pathname === "/api/frontend/modules/event-insight/events/1") {
        return jsonResponse({ traceId: "event-insight-event-first", event: { ...listPayload.items[0], evidence: [], topics: listPayload.items[0].topics } });
      }
      throw new Error(`Unexpected request ${url.pathname}`);
    });

    renderWithQueryClient(<EventListWorkspace />);

    expect(await screen.findByText("存储芯片报价上调")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/frontend/modules/event-insight/events?"), expect.any(Object));

    fireEvent.click(screen.getByRole("button", { name: "查看 CPO 光模块订单增加" }));

    expect(await screen.findByRole("heading", { name: "CPO 光模块订单增加" })).toBeInTheDocument();
    expect(screen.getByText("海外云厂商资本开支上修，光模块订单增加。")).toBeInTheDocument();
  });

  it("shows a loading state while the list request is pending", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => undefined));

    renderWithQueryClient(<EventListWorkspace />);

    expect(screen.getByText("正在加载事件列表...")).toBeInTheDocument();
  });

  it("shows an empty state when API returns no events", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ ...listPayload, items: [], total: 0 }));

    renderWithQueryClient(<EventListWorkspace />);

    expect(await screen.findByText("暂无事件，先导入材料或调整筛选条件。")).toBeInTheDocument();
  });
});

function renderWithQueryClient(children: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(<QueryWrapper queryClient={queryClient}>{children}</QueryWrapper>);
}

function QueryWrapper({ children, queryClient }: PropsWithChildren<{ queryClient: QueryClient }>) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function resolveRequestUrl(input: RequestInfo | URL) {
  if (typeof input === "string") {
    return new URL(input, window.location.origin);
  }
  if (input instanceof URL) {
    return input;
  }
  return new URL(input.url, window.location.origin);
}
