import type { NewsHeadlineView } from "../model/news-module.types";

type NewsFeedListProps = {
  headlines: NewsHeadlineView[];
};

export function NewsFeedList({ headlines }: NewsFeedListProps) {
  return (
    <ol className="space-y-3">
      {headlines.map((headline) => (
        <li key={`${headline.channelId}-${headline.rank}-${headline.title}`} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.16em] text-slate-500">
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 font-semibold text-slate-600">#{headline.rank}</span>
              <span>{headline.channelTitle}</span>
              <span aria-hidden="true">/</span>
              <span>{headline.source}</span>
              <span aria-hidden="true">/</span>
              <time dateTime={headline.publishedAt}>{formatPublishedAt(headline.publishedAt)}</time>
            </div>
            <a className="text-base font-medium text-slate-950 hover:underline" href={headline.url}>
              {headline.rank}. {headline.title}
            </a>
            {headline.summary ? <p className="text-sm leading-6 text-slate-600">{headline.summary}</p> : null}
          </div>
        </li>
      ))}
    </ol>
  );
}

function formatPublishedAt(value: string): string {
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
