import { ErrorPanelState, EmptyPanelState, LoadingPanelState } from "../shared/ui/panel-state";
import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { useStatusModuleQuery } from "../features/status/hooks/use-status-module-query";

export function StatusPage() {
  const query = useStatusModuleQuery();
  const frameDescription = query.data?.pageDescription ?? "Freshness and source health for the shell and routes.";

  if (query.isPending) {
    return (
      <ModulePageFrame
        description={frameDescription}
        lastUpdated={null}
        main={<LoadingPanelState title="Loading status snapshot" description="Fetching the latest freshness and source health data." />}
        side={<LoadingPanelState title="Status summary loading" description="Waiting for the status payload to arrive." />}
        title="Status"
      />
    );
  }

  if (query.isError || !query.data) {
    return (
      <ModulePageFrame
        description={frameDescription}
        lastUpdated={null}
        main={
          <ErrorPanelState
            title="Status module unavailable"
            description="The status payload could not be loaded from the backend."
            action={
              <button
                className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white"
                onClick={() => {
                  void query.refetch();
                }}
                type="button"
              >
                Retry
              </button>
            }
          />
        }
        side={<LoadingPanelState title="Status summary loading" description="Waiting for the status payload to arrive." />}
        title="Status"
      />
    );
  }

  const data = query.data;

  if (!data.statusItems.length) {
    return (
      <ModulePageFrame
        description={data.pageDescription}
        lastUpdated={<LastUpdatedBadge value={data.generatedAt} />}
        main={
          <EmptyPanelState
            title="No status items yet"
            description="The backend returned an empty status payload."
            action={
              <button
                className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white"
                onClick={() => {
                  void query.refetch();
                }}
                type="button"
              >
                Retry
              </button>
            }
          />
        }
        side={<StatusSummaryPanel generatedAt={data.generatedAt} moduleNote={data.moduleNote} moduleStatus={data.moduleStatus} moduleLabel={data.moduleLabel} />}
        title={data.pageTitle}
      />
    );
  }

  return (
    <ModulePageFrame
      description={data.pageDescription}
      lastUpdated={<LastUpdatedBadge value={data.generatedAt} />}
      main={<StatusOverviewPanel coverageNote={data.coverageNote} items={data.statusItems} />}
      side={<StatusSummaryPanel generatedAt={data.generatedAt} moduleNote={data.moduleNote} moduleStatus={data.moduleStatus} moduleLabel={data.moduleLabel} />}
      title={data.pageTitle}
    />
  );
}

function StatusOverviewPanel({
  coverageNote,
  items,
}: {
  coverageNote: string;
  items: Array<{
    id: string;
    label: string;
    status: string;
    detail: string;
  }>;
}) {
  return (
    <div className="space-y-6">
      <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Coverage note</p>
        <h3 className="mt-2 text-xl font-semibold text-slate-950">Freshness snapshot</h3>
        <p className="mt-3 text-sm leading-6 text-slate-600">{coverageNote || "No coverage note was returned."}</p>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {items.map((item) => (
          <article key={item.id} className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{item.status}</p>
            <h4 className="mt-2 text-lg font-semibold text-slate-950">{item.label}</h4>
            <p className="mt-3 text-sm leading-6 text-slate-600">{item.detail}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

function StatusSummaryPanel({
  generatedAt,
  moduleLabel,
  moduleNote,
  moduleStatus,
}: {
  generatedAt: string;
  moduleLabel: string;
  moduleNote: string;
  moduleStatus: string;
}) {
  return (
    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Status summary</p>
      <h3 className="mt-3 text-lg font-semibold text-slate-950">{moduleLabel}</h3>
      <div className="mt-5 space-y-3">
        <SummaryRow label="Module state" value={moduleStatus} />
        <SummaryRow label="Module note" value={moduleNote} />
        <SummaryRow label="Updated" value={generatedAt} />
      </div>
    </section>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-3 last:border-b-0 last:pb-0">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-950">{value}</span>
    </div>
  );
}
