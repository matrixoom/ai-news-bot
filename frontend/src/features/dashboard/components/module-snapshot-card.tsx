type ModuleSnapshotCardProps = {
  title: string;
  summary: string;
  ctaLabel: string;
  ctaHref: string;
};

export function ModuleSnapshotCard({ title, summary, ctaLabel, ctaHref }: ModuleSnapshotCardProps) {
  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-950">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">{summary}</p>
      <a className="mt-5 inline-flex text-sm font-medium text-slate-900 underline underline-offset-4" href={ctaHref}>
        {ctaLabel}
      </a>
    </article>
  );
}
