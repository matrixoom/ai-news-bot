import type { DashboardRawPayload, DashboardViewModel } from "./dashboard.types";

export function adaptDashboard(response: DashboardRawPayload): DashboardViewModel {
  const firstHighlight = response.highlights[0] ?? response.subtitle;

  return {
    hero: {
      eyebrow: `Generated ${formatGeneratedAt(response.generated_at)}`,
      title: response.title,
      summary: response.subtitle,
    },
    stats: response.data_status.map((item) => ({
      id: item.key,
      label: item.label,
      value: formatStatus(item.status),
      change: item.detail,
    })),
    brief: {
      title: "Today Brief",
      summary: firstHighlight,
      ctaLabel: "Read Brief",
      ctaHref: "/news",
    },
    moduleSectionTitle: "Module snapshots",
    modules: [
      {
        id: "news",
        title: "News",
        summary: response.news_sections[0]?.description ?? response.coverage_note,
        ctaLabel: "Open News",
        ctaHref: "/news",
        status: response.news_sections[0]?.status ?? "unknown",
      },
      {
        id: "macro",
        title: "Macro",
        summary: response.macro_sections[0]?.summary ?? "Macro comparisons are loading.",
        ctaLabel: "Open macro",
        ctaHref: "/macro",
        status: response.macro_sections[0]?.status ?? "unknown",
      },
      {
        id: "market",
        title: "Market",
        summary: response.market_sections[0]?.signal ?? "Market model signals are loading.",
        ctaLabel: "Open market",
        ctaHref: "/market",
        status: response.market_sections[0]?.status ?? "unknown",
      },
      {
        id: "events",
        title: "Events",
        summary: response.event_sections[0]?.items[0]?.impact_summary ?? "Event windows are loading.",
        ctaLabel: "Open events",
        ctaHref: "/events",
        status: response.event_sections[0]?.status ?? "unknown",
      },
    ],
  };
}

function formatGeneratedAt(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

function formatStatus(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
