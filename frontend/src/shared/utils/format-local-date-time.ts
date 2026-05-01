const LOCAL_DATE_TIME_FORMATTER = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZoneName: "short",
});

/**
 * 将后端时间戳格式化为浏览器本地时区时间。
 *
 * @param value 后端返回的 ISO 时间戳或可被 Date 解析的时间字符串。
 * @returns 本地时区时间文本；无法解析时返回原始值，避免界面空白。
 */
export function formatLocalDateTime(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return LOCAL_DATE_TIME_FORMATTER.format(parsed);
}
