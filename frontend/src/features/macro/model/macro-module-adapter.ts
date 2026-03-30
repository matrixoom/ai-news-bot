import type {
  MacroComparisonSection,
  MacroIndicatorView,
  MacroModuleRawPayload,
  MacroModuleViewModel,
  MacroSourceReference,
} from "./macro-module.types";

export function adaptMacroModule(response: MacroModuleRawPayload): MacroModuleViewModel {
  const comparisonSections = response.module.details.map((detail) => {
    const section = detail.section;

    return {
      key: section.key,
      title: section.title,
      status: section.status,
      description: section.description,
      summary: section.summary,
      primary: mapIndicator(section.primary),
      secondary: section.secondary ? mapIndicator(section.secondary) : null,
      deltaLabel: section.delta_label,
      deltaPoints: section.delta_points.map((point) => ({
        periodEnd: point.period_end,
        periodLabel: point.period_label,
        value: point.value,
      })),
      sources: uniqueSources(section.sources).map((source) => ({
        label: source.label,
        url: source.url,
      })),
    } satisfies MacroComparisonSection;
  });

  const indicators = dedupeIndicators(comparisonSections);
  const sources = dedupeSources(comparisonSections);

  return {
    generatedAt: response.generated_at,
    pageTitle: "Macro",
    pageDescription: response.module.description,
    moduleLabel: response.module.label,
    moduleNote: response.module.note,
    moduleStatus: response.module.status,
    moduleLoading: response.module.loading,
    comparisonSections,
    indicators,
    sources,
  };
}

function mapIndicator(indicator: MacroModuleRawPayload["module"]["details"][number]["section"]["primary"]): MacroIndicatorView {
  return {
    key: indicator.key,
    label: indicator.label,
    status: indicator.status,
    latestValue: indicator.latest_value,
    previousValue: indicator.previous_value,
    changeLabel: indicator.change_label,
    trend: indicator.trend,
    frequency: indicator.frequency,
    sourceLabel: indicator.source_label,
    sourceUrl: indicator.source_url,
    updatedAt: indicator.updated_at,
    periodLabel: indicator.period_label,
    context: indicator.context,
    unit: indicator.unit,
    points: indicator.points.map((point) => ({
      periodEnd: point.period_end,
      periodLabel: point.period_label,
      value: point.value,
    })),
  };
}

function dedupeIndicators(sections: MacroComparisonSection[]): MacroIndicatorView[] {
  const indicators = new Map<string, MacroIndicatorView>();

  for (const section of sections) {
    if (!indicators.has(section.primary.key)) {
      indicators.set(section.primary.key, section.primary);
    }
    if (section.secondary && !indicators.has(section.secondary.key)) {
      indicators.set(section.secondary.key, section.secondary);
    }
  }

  return Array.from(indicators.values());
}

function dedupeSources(sections: MacroComparisonSection[]): MacroSourceReference[] {
  const sourceMap = new Map<string, MacroSourceReference>();

  for (const section of sections) {
    for (const source of section.sources) {
      const key = `${source.label}::${source.url}`;
      const existing = sourceMap.get(key);

      if (!existing) {
        sourceMap.set(key, {
          label: source.label,
          url: source.url,
          sectionTitles: [section.title],
        });
        continue;
      }

      if (!existing.sectionTitles.includes(section.title)) {
        existing.sectionTitles.push(section.title);
      }
    }
  }

  return Array.from(sourceMap.values());
}

function uniqueSources(sources: Array<{ label: string; url: string }>): Array<{ label: string; url: string }> {
  const seen = new Set<string>();
  const normalized: Array<{ label: string; url: string }> = [];

  for (const source of sources) {
    const key = `${source.label}::${source.url}`;

    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    normalized.push(source);
  }

  return normalized;
}
