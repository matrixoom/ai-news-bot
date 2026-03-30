import type { NewsChannelSummary } from "../model/news-module.types";

type NewsChannelCardProps = {
  channel: NewsChannelSummary;
};

export function NewsChannelCard({ channel }: NewsChannelCardProps) {
  return (
    <article className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h4 className="text-lg font-semibold text-slate-950">{channel.title}</h4>
          <p className="mt-2 text-sm leading-6 text-slate-600">{channel.description}</p>
        </div>
        <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
          {channel.status}
        </span>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-sm text-slate-600">
        <span>{channel.itemCount} stories</span>
        {channel.note ? <span aria-hidden="true">/</span> : null}
        {channel.note ? <span>{channel.note}</span> : null}
      </div>

      {channel.topHeadline ? (
        <p className="mt-4 text-sm leading-6 text-slate-700">
          <span className="font-medium text-slate-900">Top headline: </span>
          {channel.topHeadline}
        </p>
      ) : null}
    </article>
  );
}
