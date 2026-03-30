import { BriefCard } from "../features/dashboard/components/brief-card";
import { DashboardSkeleton } from "../features/dashboard/components/dashboard-skeleton";
import { ModuleSnapshotCard } from "../features/dashboard/components/module-snapshot-card";
import { StatCard } from "../features/dashboard/components/stat-card";
import { useDashboardQuery } from "../features/dashboard/hooks/use-dashboard-query";

export function DashboardPage() {
  const { data, error, isLoading, retry } = useDashboardQuery();

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error || !data) {
    return (
      <section className="rounded-[2rem] border border-rose-200 bg-rose-50 p-8 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-[0.16em] text-rose-600">Dashboard unavailable</p>
        <h2 className="mt-3 text-2xl font-semibold text-slate-950">We could not load the latest overview.</h2>
        <p className="mt-3 text-sm leading-6 text-slate-600">Try refreshing the dashboard data and loading the page again.</p>
        <button
          className="mt-6 rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white"
          onClick={retry}
          type="button"
        >
          Retry
        </button>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">{data.hero.eyebrow}</p>
        <h2 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950">{data.hero.title}</h2>
        <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">{data.hero.summary}</p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {data.stats.map((stat) => (
          <StatCard key={stat.id} label={stat.label} value={stat.value} change={stat.change} />
        ))}
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1.4fr)]">
        <BriefCard
          title={data.brief.title}
          summary={data.brief.summary}
          ctaLabel={data.brief.ctaLabel}
          ctaHref={data.brief.ctaHref}
        />

        <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-950">{data.moduleSectionTitle}</h2>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {data.modules.map((moduleSnapshot) => (
              <ModuleSnapshotCard
                key={moduleSnapshot.id}
                title={moduleSnapshot.title}
                summary={moduleSnapshot.summary}
                ctaLabel={moduleSnapshot.ctaLabel}
                ctaHref={moduleSnapshot.ctaHref}
              />
            ))}
          </div>
        </section>
      </div>

      <p className="sr-only">Module page coming in the next slice.</p>
    </div>
  );
}
