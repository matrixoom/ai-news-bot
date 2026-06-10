import type { PushChannelOption, PushSchedule, PushSourceModuleOption } from "../model/push-module.types";

type PushSchedulesEditorProps = {
  schedules: PushSchedule[];
  channelTypeOptions: PushChannelOption[];
  sourceModuleOptions: PushSourceModuleOption[];
  onSchedulesChange: (nextSchedules: PushSchedule[]) => void;
};

export function PushSchedulesEditor({
  schedules,
  channelTypeOptions,
  sourceModuleOptions,
  onSchedulesChange,
}: PushSchedulesEditorProps) {
  const enabledChannels = channelTypeOptions.filter((option) => option.enabled);
  const enabledModules = sourceModuleOptions.filter((option) => option.enabled);

  function updateSchedule(scheduleId: string, updater: (schedule: PushSchedule) => PushSchedule) {
    onSchedulesChange(schedules.map((schedule) => (schedule.id === scheduleId ? updater(schedule) : schedule)));
  }

  return (
    <section className="workbench-panel space-y-5 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Schedules</p>
          <h3 className="mt-2 text-lg font-semibold text-ink">Schedule editor</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Keep the recurring delivery windows aligned with your default report profile.
          </p>
        </div>
        <button
          className="workbench-button"
          onClick={() => {
            onSchedulesChange([
              ...schedules,
              {
                id: `schedule-${schedules.length + 1}`,
                name: `Schedule ${schedules.length + 1}`,
                enabled: true,
                moduleIds: ["market"],
                channelTypes: ["email"],
                times: ["08:00"],
                timezone: "Asia/Shanghai",
              },
            ]);
          }}
          type="button"
        >
          Add schedule
        </button>
      </div>

      <div className="space-y-4">
        {schedules.map((schedule) => (
          <article key={schedule.id} className="rounded-panel border border-line bg-surface-subtle p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h4 className="text-base font-semibold text-ink">{schedule.name}</h4>
                <p className="mt-1 text-sm text-slate-500">{schedule.id}</p>
              </div>
              <button
                className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm text-slate-600"
                onClick={() => {
                  onSchedulesChange(schedules.filter((item) => item.id !== schedule.id));
                }}
                type="button"
              >
                Remove
              </button>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="space-y-2 text-sm text-slate-700">
                <span className="font-medium text-slate-900">Name</span>
                <input
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3"
                  onChange={(event) => {
                    updateSchedule(schedule.id, (current) => ({ ...current, name: event.target.value }));
                  }}
                  type="text"
                  value={schedule.name}
                />
              </label>

              <label className="space-y-2 text-sm text-slate-700">
                <span className="font-medium text-slate-900">Times</span>
                <input
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3"
                  onChange={(event) => {
                    updateSchedule(schedule.id, (current) => ({
                      ...current,
                      times: event.target.value
                        .split(",")
                        .map((value) => value.trim())
                        .filter(Boolean),
                    }));
                  }}
                  type="text"
                  value={schedule.times.join(", ")}
                />
              </label>

              <label className="space-y-2 text-sm text-slate-700">
                <span className="font-medium text-slate-900">Timezone</span>
                <input
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3"
                  onChange={(event) => {
                    updateSchedule(schedule.id, (current) => ({ ...current, timezone: event.target.value }));
                  }}
                  type="text"
                  value={schedule.timezone}
                />
              </label>

              <label className="space-y-2 text-sm text-slate-700">
                <span className="font-medium text-slate-900">Primary channel</span>
                <select
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3"
                  onChange={(event) => {
                    updateSchedule(schedule.id, (current) => ({ ...current, channelTypes: [event.target.value] }));
                  }}
                  value={schedule.channelTypes[0] ?? "email"}
                >
                  {enabledChannels.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-4 grid gap-3">
              {enabledModules.map((option) => {
                const checked = schedule.moduleIds.includes(option.id);
                return (
                  <label key={`${schedule.id}-${option.id}`} className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
                    <input
                      checked={checked}
                      onChange={(event) => {
                        updateSchedule(schedule.id, (current) => {
                          const nextModuleIds = event.target.checked
                            ? Array.from(new Set([...current.moduleIds, option.id]))
                            : current.moduleIds.filter((item) => item !== option.id);
                          return { ...current, moduleIds: nextModuleIds.length ? nextModuleIds : ["market"] };
                        });
                      }}
                      type="checkbox"
                    />
                    <span>
                      <span className="block font-medium text-slate-900">{option.label}</span>
                      <span className="mt-1 block text-slate-600">{option.description}</span>
                    </span>
                  </label>
                );
              })}
            </div>

            <label className="mt-4 flex items-start gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
              <input
                checked={schedule.enabled}
                onChange={(event) => {
                  updateSchedule(schedule.id, (current) => ({ ...current, enabled: event.target.checked }));
                }}
                type="checkbox"
              />
              <span>
                <span className="block font-medium text-slate-900">Enabled</span>
                <span className="mt-1 block text-slate-600">Allow this schedule to run when its local time window arrives.</span>
              </span>
            </label>
          </article>
        ))}
      </div>
    </section>
  );
}
