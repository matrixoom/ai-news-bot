export type ModuleTabDefinition<TValue extends string = string> = {
  value: TValue;
  label: string;
  description?: string;
};

export function resolveModuleTab<TValue extends string>(
  requestedTab: string | null | undefined,
  tabs: readonly ModuleTabDefinition<TValue>[],
  fallbackTab: TValue,
): TValue {
  const allowedTabs = new Set(tabs.map((tab) => tab.value));

  if (requestedTab && allowedTabs.has(requestedTab as TValue)) {
    return requestedTab as TValue;
  }

  return fallbackTab;
}

export function buildModuleTabSearchParams(
  currentSearchParams: URLSearchParams,
  tabValue: string,
  queryKey = "tab",
): URLSearchParams {
  const nextSearchParams = new URLSearchParams(currentSearchParams);
  nextSearchParams.set(queryKey, tabValue);
  return nextSearchParams;
}

export function buildModuleTabHref(
  pathname: string,
  currentSearchParams: URLSearchParams,
  tabValue: string,
  queryKey = "tab",
): string {
  const nextSearchParams = buildModuleTabSearchParams(currentSearchParams, tabValue, queryKey);
  const query = nextSearchParams.toString();

  return query ? `${pathname}?${query}` : pathname;
}
