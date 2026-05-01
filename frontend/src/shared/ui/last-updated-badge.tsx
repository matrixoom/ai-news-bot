import { formatLocalDateTime } from "../utils/format-local-date-time";

type LastUpdatedBadgeProps = {
  value: string;
  label?: string;
};

export function LastUpdatedBadge({ value, label = "Updated" }: LastUpdatedBadgeProps) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-slate-600">
      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</span>
      <time className="text-sm font-medium text-slate-800" dateTime={value}>
        {formatLocalDateTime(value)}
      </time>
    </div>
  );
}
