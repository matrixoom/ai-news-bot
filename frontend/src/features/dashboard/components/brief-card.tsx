type BriefCardProps = {
  title: string;
  summary: string;
  ctaLabel: string;
  ctaHref: string;
};

export function BriefCard({ title, summary, ctaLabel, ctaHref }: BriefCardProps) {
  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-sm font-medium uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className="mt-4 text-base leading-7 text-slate-700">{summary}</p>
      <a
        className="mt-6 inline-flex items-center rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white"
        href={ctaHref}
      >
        {ctaLabel}
      </a>
    </article>
  );
}
