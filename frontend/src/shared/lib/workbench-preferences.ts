export const DEFAULT_ROUTE_STORAGE_KEY = "dashboard-default-route";
export const DEFAULT_NEWS_MODE_STORAGE_KEY = "dashboard-default-news-mode";
export const SHOW_MARKET_TICKER_STORAGE_KEY = "dashboard-show-market-ticker";
export const SIDEBAR_COLLAPSED_STORAGE_KEY = "dashboard-sidebar-collapsed";
export const MACRO_CHART_RANGES_KEY = "macro-chart-ranges";
export const MACRO_CHART_FREQUENCIES_KEY = "macro-chart-frequencies";
export const MARKET_CHART_RANGES_KEY = "market-chart-ranges";
export const MARKET_CHART_FREQUENCIES_KEY = "market-chart-frequencies";

const WORKBENCH_PREFERENCE_EVENT = "workbench-preference-change";

/**
 * 读取字符串类型的工作台偏好设置。
 * @param key 本地存储键名。
 * @param fallback 读取失败或未配置时使用的默认值。
 * @returns 当前字符串偏好值。
 */
export function readStringPreference(key: string, fallback: string): string {
  try {
    return window.localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

/**
 * 读取布尔类型的工作台偏好设置。
 * @param key 本地存储键名。
 * @param fallback 读取失败或值无效时使用的默认值。
 * @returns 当前布尔偏好值。
 */
export function readBooleanPreference(key: string, fallback: boolean): boolean {
  const rawValue = readStringPreference(key, fallback ? "true" : "false");
  if (rawValue === "true") {
    return true;
  }
  if (rawValue === "false") {
    return false;
  }
  return fallback;
}

/**
 * 写入字符串或布尔类型的工作台偏好设置，并通知当前页面订阅者。
 * @param key 本地存储键名。
 * @param value 需要持久化的偏好值。
 * @returns 无返回值。
 */
export function writePreference(key: string, value: string | boolean) {
  const normalized = String(value);
  try {
    window.localStorage.setItem(key, normalized);
  } catch {
    return;
  }

  window.dispatchEvent(
    new CustomEvent(WORKBENCH_PREFERENCE_EVENT, {
      detail: { key, value: normalized },
    }),
  );
}

/**
 * 读取 JSON 类型的工作台偏好设置。
 * @param key 本地存储键名。
 * @param fallback 读取失败、未配置或解析失败时使用的默认值。
 * @returns 当前 JSON 偏好值。
 */
export function readJSONPreference<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

/**
 * 写入 JSON 类型的工作台偏好设置，并通知当前页面订阅者。
 * @param key 本地存储键名。
 * @param value 需要持久化的 JSON 偏好值。
 * @returns 无返回值。
 */
export function writeJSONPreference<T>(key: string, value: T) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    return;
  }
  window.dispatchEvent(
    new CustomEvent(WORKBENCH_PREFERENCE_EVENT, {
      detail: { key, value: JSON.stringify(value) },
    }),
  );
}

/**
 * 订阅指定工作台偏好设置的变更事件。
 * @param key 需要监听的本地存储键名。
 * @param onChange 偏好变化后的回调函数。
 * @returns 用于取消订阅的清理函数。
 */
export function subscribeToPreference(
  key: string,
  onChange: (value: string) => void,
): () => void {
  function handleStorage(event: StorageEvent) {
    if (event.key === key && typeof event.newValue === "string") {
      onChange(event.newValue);
    }
  }

  function handleCustomEvent(event: Event) {
    const detail = (event as CustomEvent<{ key?: string; value?: string }>).detail;
    if (detail?.key === key && typeof detail.value === "string") {
      onChange(detail.value);
    }
  }

  window.addEventListener("storage", handleStorage);
  window.addEventListener(WORKBENCH_PREFERENCE_EVENT, handleCustomEvent as EventListener);

  return () => {
    window.removeEventListener("storage", handleStorage);
    window.removeEventListener(WORKBENCH_PREFERENCE_EVENT, handleCustomEvent as EventListener);
  };
}
