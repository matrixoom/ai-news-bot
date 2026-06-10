import type {
  PushChannelOption,
  PushConfig,
  PushSourceModuleOption,
  PushStyleOption,
} from "../model/push-module.types";

type PushConfigFormProps = {
  draft: PushConfig;
  channelTypeOptions: PushChannelOption[];
  sourceModuleOptions: PushSourceModuleOption[];
  styleOptions: PushStyleOption[];
  isSaving: boolean;
  onDraftChange: (next: PushConfig) => void;
  onSave: () => void;
};

export function PushConfigForm({
  draft,
  channelTypeOptions,
  sourceModuleOptions,
  styleOptions,
  isSaving,
  onDraftChange,
  onSave,
}: PushConfigFormProps) {
  const busy = isSaving;

  return (
    <section className="workbench-panel space-y-5 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Configuration</p>
          <h3 className="mt-2 text-lg font-semibold text-ink">Delivery configuration</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Tune the active modules, report style, and SMTP delivery profile before saving.
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2 text-sm text-slate-700">
          <span className="font-medium text-slate-900">Report style</span>
          <select
            aria-label="Report style"
            className="workbench-input w-full"
            onChange={(event) => {
              onDraftChange({ ...draft, reportStyle: event.target.value });
            }}
            value={draft.reportStyle}
          >
            {styleOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-2 text-sm text-slate-700">
          <span className="font-medium text-slate-900">Primary channel</span>
          <select
            aria-label="Primary channel"
            className="workbench-input w-full"
            onChange={(event) => {
              const nextChannel = event.target.value;
              onDraftChange({
                ...draft,
                schedules: draft.schedules.map((schedule) => ({
                  ...schedule,
                  channelTypes: [nextChannel],
                })),
              });
            }}
            value={draft.schedules[0]?.channelTypes[0] ?? "email"}
          >
            {channelTypeOptions
              .filter((option) => option.enabled)
              .map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
          </select>
        </label>
      </div>

      <div className="space-y-3">
        <p className="text-sm font-medium text-slate-900">Included modules</p>
        <div className="grid gap-3 md:grid-cols-2">
          {sourceModuleOptions.map((option) => {
            const checked = draft.selectedModuleIds.includes(option.id);
            return (
              <label
                key={option.id}
                className={[
                  "flex items-start gap-3 rounded-control border px-4 py-3 text-sm",
                  option.enabled ? "border-line bg-surface-subtle text-ink" : "border-line bg-canvas text-muted",
                ].join(" ")}
              >
                <input
                  checked={checked}
                  disabled={!option.enabled}
                  onChange={(event) => {
                    const nextModuleIds = event.target.checked
                      ? Array.from(new Set([...draft.selectedModuleIds, option.id]))
                      : draft.selectedModuleIds.filter((item) => item !== option.id);

                    onDraftChange({
                      ...draft,
                      selectedModuleIds: nextModuleIds.length ? nextModuleIds : ["market"],
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
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <TextField
          label="SMTP server"
          value={draft.email.smtpServer}
          onChange={(nextValue) => {
            onDraftChange({ ...draft, email: { ...draft.email, smtpServer: nextValue } });
          }}
        />
        <NumberField
          label="SMTP port"
          value={draft.email.smtpPort}
          onChange={(nextValue) => {
            onDraftChange({ ...draft, email: { ...draft.email, smtpPort: nextValue } });
          }}
        />
        <TextField
          label="Username"
          value={draft.email.username}
          onChange={(nextValue) => {
            onDraftChange({ ...draft, email: { ...draft.email, username: nextValue } });
          }}
        />
        <TextField
          label="Password"
          type="password"
          value={draft.email.password}
          onChange={(nextValue) => {
            onDraftChange({
              ...draft,
              email: { ...draft.email, password: nextValue, passwordConfigured: nextValue.length > 0 },
            });
          }}
        />
        <TextField
          label="From address"
          value={draft.email.fromAddress}
          onChange={(nextValue) => {
            onDraftChange({ ...draft, email: { ...draft.email, fromAddress: nextValue } });
          }}
        />
        <TextField
          label="To addresses"
          value={draft.email.toAddresses}
          onChange={(nextValue) => {
            onDraftChange({ ...draft, email: { ...draft.email, toAddresses: nextValue } });
          }}
        />
      </div>

      <label className="flex items-start gap-3 rounded-control border border-line bg-surface-subtle px-4 py-3 text-sm text-ink">
        <input
          checked={draft.email.useTls}
          onChange={(event) => {
            onDraftChange({ ...draft, email: { ...draft.email, useTls: event.target.checked } });
          }}
          type="checkbox"
        />
        <span>
          <span className="block font-medium text-slate-900">Use TLS</span>
          <span className="mt-1 block text-slate-600">Keep transport security enabled for SMTP delivery.</span>
        </span>
      </label>

      <div className="flex flex-wrap gap-3">
        <button
          className="workbench-button-primary disabled:cursor-not-allowed disabled:opacity-40"
          disabled={busy}
          onClick={onSave}
          type="button"
        >
          {isSaving ? "Saving..." : "Save configuration"}
        </button>
      </div>
    </section>
  );
}

function TextField({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (nextValue: string) => void;
  type?: "text" | "password";
}) {
  return (
    <label className="space-y-2 text-sm text-slate-700">
      <span className="font-medium text-slate-900">{label}</span>
      <input
        aria-label={label}
        className="workbench-input w-full"
        onChange={(event) => onChange(event.target.value)}
        type={type}
        value={value}
      />
    </label>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (nextValue: number) => void;
}) {
  return (
    <label className="space-y-2 text-sm text-slate-700">
      <span className="font-medium text-slate-900">{label}</span>
      <input
        aria-label={label}
        className="workbench-input w-full"
        onChange={(event) => onChange(Number(event.target.value) || 587)}
        type="number"
        value={value}
      />
    </label>
  );
}
