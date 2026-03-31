import { useEffect } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { DEFAULT_NEWS_MODE_STORAGE_KEY } from "../lib/workbench-preferences";

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
  const { pathname } = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedMode = searchParams.get("news_mode");
  const newsMode = requestedMode ? resolveNewsMode(requestedMode) : readStoredNewsMode();

  useEffect(() => {
    try {
      window.localStorage.setItem(NEWS_MODE_STORAGE_KEY, newsMode);
    } catch {
      // Ignore storage failures and keep the URL as the source of truth.
    }
  }, [newsMode]);

  useEffect(() => {
    if (pathname === "/" || requestedMode || newsMode === "hybrid") {
      return;
    }

    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("news_mode", newsMode);
    setSearchParams(nextSearchParams, { replace: true });
  }, [newsMode, pathname, requestedMode, searchParams, setSearchParams]);

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

function readStoredNewsMode(): NewsMode {
  try {
    return resolveNewsMode(window.localStorage.getItem(NEWS_MODE_STORAGE_KEY));
  } catch {
      return "hybrid";
  }
}

const NEWS_MODE_STORAGE_KEY = DEFAULT_NEWS_MODE_STORAGE_KEY;

function resolveNewsMode(value: string | null): NewsMode {
  if (value === "api" || value === "upstream") {
    return value;
  }

  return "hybrid";
}

function getNewsModeLabel(value: NewsMode): string {
  return NEWS_MODE_OPTIONS.find((option) => option.value === value)?.label ?? value;
}
