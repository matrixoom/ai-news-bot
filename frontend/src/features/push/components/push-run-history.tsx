import type { PushRecentRun } from "../model/push-module.types";

type PushRunHistoryProps = {
  runs: PushRecentRun[];
};

export function PushRunHistory({ runs }: PushRunHistoryProps) {
  return (
    <section className="space-y-6 rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">History</p>
        <h3 className="mt-2 text-xl font-semibold text-slate-950">Manual runs and scheduled deliveries</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">Review the latest executions across manual sends and scheduler-triggered jobs.</p>
      </div>

      {!runs.length ? (
        <p className="text-sm text-slate-500">No push runs yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead>
              <tr className="text-slate-500">
                <th className="pb-3 pr-4 font-medium">Executed</th>
                <th className="pb-3 pr-4 font-medium">Status</th>
                <th className="pb-3 pr-4 font-medium">Trigger</th>
                <th className="pb-3 pr-4 font-medium">Job</th>
                <th className="pb-3 font-medium">Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {runs.map((run) => (
                <tr key={`${run.executedAt}-${run.jobName}`}>
                  <td className="py-3 pr-4 font-mono text-xs text-slate-600">{run.executedAt}</td>
                  <td className="py-3 pr-4 text-slate-700">{run.status}</td>
                  <td className="py-3 pr-4 text-slate-700">{run.trigger}</td>
                  <td className="py-3 pr-4 text-slate-900">{run.jobName}</td>
                  <td className="py-3 text-slate-600">{run.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
