import { useQuery } from "@tanstack/react-query";
import { adaptMarketModule } from "../../features/market/model/market-module-adapter";
import { getMarketModule } from "../../features/market/api/get-market-module";
import type { MarketSignalCard } from "../../features/market/model/market-module.types";

type IndexTarget = {
  key: string;
  label: string;
  aliases: string[];
  sourceLabel: string;
};

const CORE_INDEX_TARGETS: IndexTarget[] = [
  {
    key: "csi-300",
    label: "沪深 300",
    aliases: ["沪深300", "沪深 300", "csi 300", "csi300"],
    sourceLabel: "AShare / 交易所",
  },
  {
    key: "csi-500",
    label: "中证 500",
    aliases: ["中证500", "中证 500", "csi 500", "csi500"],
    sourceLabel: "AShare / 交易所",
  },
  {
    key: "csi-1000",
    label: "中证 1000",
    aliases: ["中证1000", "中证 1000", "csi 1000", "csi1000"],
    sourceLabel: "AShare / 交易所",
  },
  {
    key: "sse-composite",
    label: "上证综指",
    aliases: ["上证综指", "上证指数", "sse", "shanghai composite"],
    sourceLabel: "AShare / 交易所",
  },
  {
    key: "hang-seng",
    label: "恒生指数",
    aliases: ["恒生指数", "恒生", "hang seng", "hsi"],
    sourceLabel: "HK / 交易所",
  },
  {
    key: "chinext",
    label: "创业板指",
    aliases: ["创业板指", "创业板", "chinext"],
    sourceLabel: "AShare / 交易所",
  },
];

export function useMarketTicker() {
  return useQuery({
    queryKey: ["market-module"],
    staleTime: 60_000,
    queryFn: ({ signal }) => getMarketModule(signal).then(adaptMarketModule),
    select: (model) => buildTickerItems(model.signalCards, model.generatedAt),
  });
}

function buildTickerItems(cards: MarketSignalCard[], generatedAt: string): MarketSignalCard[] {
  const normalized = cards.map((card) => ({
    card,
    normalizedLabel: normalizeText(card.label),
  }));

  const usedKeys = new Set<string>();

  const prioritized = CORE_INDEX_TARGETS.map((target) => {
    const matched = normalized.find(
      (entry) =>
        !usedKeys.has(entry.card.key) &&
        target.aliases.some((alias) => entry.normalizedLabel.includes(normalizeText(alias))),
    )?.card;

    if (matched) {
      usedKeys.add(matched.key);
      return matched;
    }

    return createPlaceholderTickerCard(target, generatedAt);
  });

  const remaining = cards.filter((card) => !usedKeys.has(card.key));
  return [...prioritized, ...remaining];
}

function createPlaceholderTickerCard(target: IndexTarget, generatedAt: string): MarketSignalCard {
  return {
    key: `${target.key}-placeholder`,
    label: target.label,
    status: "placeholder",
    closeValue: "--",
    ma20Value: "--",
    signal: "pending",
    deviationLabel: "n/a",
    tradeDate: toIsoDate(generatedAt),
    sourceLabel: target.sourceLabel,
    explanation: "Awaiting market payload for this index.",
    dataWindowLabel: "n/a",
    historyWarning: "",
    chartPoints: [],
  };
}

function toIsoDate(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toISOString().slice(0, 10);
}

function normalizeText(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}
