import type { PageMeta } from "../shared/types/page-meta";

export function HeaderBar({ meta }: { meta: PageMeta }) {
  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-8 py-5">
      <div>
        <h2 className="text-2xl font-semibold text-slate-950">{meta.title}</h2>
        <p className="mt-1 text-sm text-slate-500">{meta.description}</p>
      </div>
      <div className="flex items-center gap-3 text-sm text-slate-500">
        <button className="rounded-lg border border-slate-200 px-3 py-2 text-slate-700">Refresh</button>
        <span>Freshness: live</span>
      </div>
    </header>
  );
}
