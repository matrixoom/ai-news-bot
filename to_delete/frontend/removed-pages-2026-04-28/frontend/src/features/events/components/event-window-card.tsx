import type { EventWindowSectionView } from "../model/events-module.types";

type EventWindowCardProps = {
  section: EventWindowSectionView;
};

export function EventWindowCard({ section }: EventWindowCardProps) {
  return (
    <article className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{section.note}</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">{section.title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">The window stays focused on the next official dates and the likely market-sensitive releases.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusPill value={section.status} />
          <CountPill value={`${section.itemCount} items`} />
        </div>
      </div>

      <div className="mt-5 grid gap-3">
        {section.items.map((item) => (
          <div key={`${section.key}-${item.title}-${item.expectedDate}`} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="max-w-2xl">
                <h4 className="text-base font-semibold text-slate-950">{item.title}</h4>
                <p className="mt-2 text-sm leading-6 text-slate-600">{item.impactSummary}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Chip>{formatDate(item.expectedDate)}</Chip>
                <Chip>{item.timeWindow}</Chip>
                <Chip>{item.confidence}</Chip>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-slate-500">
              <span>{item.region}</span>
              <span aria-hidden="true">|</span>
              <span>{item.source}</span>
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

function StatusPill({ value }: { value: string }) {
  return (
    <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-600">
      {value}
    </span>
  );
}

function CountPill({ value }: { value: string }) {
  return (
    <span className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
      {value}
    </span>
  );
}

function Chip({ children }: { children: string }) {
  return <span className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600">{children}</span>;
}

function formatDate(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}
