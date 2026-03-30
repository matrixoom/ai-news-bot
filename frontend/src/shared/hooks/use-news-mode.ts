import { useSearchParams } from "react-router-dom";

export type NewsMode = "hybrid" | "api" | "upstream";

export type NewsModeOption = {
  value: NewsMode;
  label: string;
};

export const NEWS_MODE_OPTIONS: readonly NewsModeOption[] = [
  { value: "hybrid", label: "Hybrid" },
  { value: "api", label: "API" },
  { value: "upstream", label: "Upstream" },
];

export function useNewsMode() {
  const [searchParams, setSearchParams] = useSearchParams();
  const newsMode = resolveNewsMode(searchParams.get("news_mode"));

  function setNewsMode(nextMode: NewsMode) {
    if (nextMode === newsMode) {
      return;
    }

    const nextSearchParams = new URLSearchParams(searchParams);
    if (nextMode === "hybrid") {
      nextSearchParams.delete("news_mode");
    } else {
      nextSearchParams.set("news_mode", nextMode);
    }
    setSearchParams(nextSearchParams, { replace: true });
  }

  return {
    newsMode,
    newsModeLabel: getNewsModeLabel(newsMode),
    newsModeOptions: NEWS_MODE_OPTIONS,
    setNewsMode,
  };
}

function resolveNewsMode(value: string | null): NewsMode {
  if (value === "api" || value === "upstream") {
    return value;
  }

  return "hybrid";
}

function getNewsModeLabel(value: NewsMode): string {
  return NEWS_MODE_OPTIONS.find((option) => option.value === value)?.label ?? value;
}
