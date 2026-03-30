import type {
  EventOfficialLinkView,
  EventWatchItemView,
  EventWindowSectionView,
  EventsModuleRawPayload,
  EventsModuleViewModel,
} from "./events-module.types";

export function adaptEventsModule(response: EventsModuleRawPayload): EventsModuleViewModel {
  const windowSections = response.module.details.map((detail) => {
    const section = detail.section;

    return {
      key: section.key,
      title: section.title,
      status: section.status,
      note: detail.note,
      itemCount: section.items.length,
      items: section.items.map((item) => ({
        title: item.title,
        region: item.region,
        expectedDate: item.expected_date,
        timeWindow: item.time_window,
        confidence: item.confidence,
        impactSummary: item.impact_summary,
        source: item.source,
      })),
      officialLinks: dedupeOfficialLinks(section.official_links).map((link) => ({
        region: link.region,
        label: link.label,
        url: link.url,
      })),
    } satisfies EventWindowSectionView;
  });

  const watchItems = windowSections
    .flatMap((section, windowIndex) =>
      section.items.map((item, itemIndex) => ({
        ...item,
        windowKey: section.key,
        windowTitle: section.title,
        sortKey: `${item.expectedDate}::${String(windowIndex).padStart(2, "0")}::${String(itemIndex).padStart(2, "0")}`,
      })),
    )
    .sort((left, right) => left.sortKey.localeCompare(right.sortKey))
    .slice(0, 6)
    .map(({ sortKey: _sortKey, ...item }) => item satisfies EventWatchItemView);

  const officialLinks = dedupeOfficialLinks(
    windowSections.flatMap((section) => section.officialLinks),
  ).map((link) => ({
    region: link.region,
    label: link.label,
    url: link.url,
  })) satisfies EventOfficialLinkView[];

  return {
    generatedAt: response.generated_at,
    pageTitle: "Events",
    pageDescription: response.module.description,
    moduleLabel: response.module.label,
    moduleNote: response.module.note,
    moduleStatus: response.module.status,
    moduleLoading: response.module.loading,
    windowSections,
    officialLinks,
    watchItems,
    totalItems: windowSections.reduce((sum, section) => sum + section.itemCount, 0),
  };
}

function dedupeOfficialLinks(
  links: Array<{
    region: string;
    label: string;
    url: string;
  }>,
) {
  const seen = new Set<string>();

  return links.filter((link) => {
    const key = `${link.region}::${link.label}::${link.url}`;

    if (seen.has(key)) {
      return false;
    }

    seen.add(key);
    return true;
  });
}
