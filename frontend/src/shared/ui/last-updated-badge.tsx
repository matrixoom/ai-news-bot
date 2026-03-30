type LastUpdatedBadgeProps = {
  value: string;
  label?: string;
};

export function LastUpdatedBadge({ value, label = "Updated" }: LastUpdatedBadgeProps) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-slate-600">
      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</span>
      <time className="text-sm font-medium text-slate-800" dateTime={value}>
        {formatLastUpdated(value)}
      </time>
    </div>
  );
}

function formatLastUpdated(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  }).format(parsed);
}
