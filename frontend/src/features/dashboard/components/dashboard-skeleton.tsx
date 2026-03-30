export function DashboardSkeleton() {
  return (
    <section aria-label="Dashboard loading" className="space-y-6">
      <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm">
        <div className="h-4 w-24 animate-pulse rounded bg-slate-200" />
        <div className="mt-4 h-10 w-64 animate-pulse rounded bg-slate-200" />
        <div className="mt-4 h-5 w-full max-w-2xl animate-pulse rounded bg-slate-200" />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="h-36 animate-pulse rounded-3xl bg-slate-200" />
        ))}
      </div>
      <p className="sr-only">Dashboard overview loading.</p>
    </section>
  );
}
