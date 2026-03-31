import { useMemo, useState } from "react";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { SettingsSectionCard } from "../features/settings/components/settings-section-card";
import { buildSettingsViewModel } from "../features/settings/model/settings-view-model";
import {
  DEFAULT_NEWS_MODE_STORAGE_KEY,
  DEFAULT_ROUTE_STORAGE_KEY,
  SHOW_MARKET_TICKER_STORAGE_KEY,
} from "../shared/lib/workbench-preferences";
import {
  useBooleanWorkbenchPreference,
  useStringWorkbenchPreference,
} from "../shared/hooks/use-workbench-preference";

export function SettingsPage() {
  const defaultRoute = useStringWorkbenchPreference(DEFAULT_ROUTE_STORAGE_KEY, "/dashboard");
  const defaultNewsMode = useStringWorkbenchPreference(DEFAULT_NEWS_MODE_STORAGE_KEY, "hybrid");
  const showMarketTicker = useBooleanWorkbenchPreference(SHOW_MARKET_TICKER_STORAGE_KEY, true);
  const [draft, setDraft] = useState({
    defaultRoute: defaultRoute.value,
    defaultNewsMode: defaultNewsMode.value,
    showMarketTicker: showMarketTicker.value,
  });
  const [flash, setFlash] = useState<string | null>(null);

  const model = useMemo(() => buildSettingsViewModel(draft), [draft]);

  return (
    <ModulePageFrame
      description={model.pageDescription}
      main={
        <div className="space-y-6">
          <SettingsSectionCard title="Workspace preferences" description={model.sections[0].description}>
            <form
              className="space-y-6"
              onSubmit={(event) => {
                event.preventDefault();
                defaultRoute.setValue(draft.defaultRoute);
                defaultNewsMode.setValue(draft.defaultNewsMode);
                showMarketTicker.setValue(draft.showMarketTicker);
                setFlash("Preferences saved.");
              }}
            >
              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-700">
                  <span className="font-medium text-slate-900">Default landing page</span>
                  <select
                    aria-label="Default landing page"
                    className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
                    onChange={(event) => {
                      setDraft((current) => ({ ...current, defaultRoute: event.target.value }));
                    }}
                    value={draft.defaultRoute}
                  >
                    {model.defaultRouteOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-2 text-sm text-slate-700">
                  <span className="font-medium text-slate-900">Default news mode</span>
                  <select
                    aria-label="Default news mode"
                    className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
                    onChange={(event) => {
                      setDraft((current) => ({ ...current, defaultNewsMode: event.target.value }));
                    }}
                    value={draft.defaultNewsMode}
                  >
                    {model.newsModeOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <label className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-700">
                <input
                  aria-label="Show market ticker"
                  checked={draft.showMarketTicker}
                  className="mt-1"
                  onChange={(event) => {
                    setDraft((current) => ({ ...current, showMarketTicker: event.target.checked }));
                  }}
                  type="checkbox"
                />
                <span>
                  <span className="block font-medium text-slate-900">Show market ticker</span>
                  <span className="mt-1 block text-slate-600">Hide or restore the compact market strip in the shell header.</span>
                </span>
              </label>

              <div className="flex items-center gap-4">
                <button className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white" type="submit">
                  Save preferences
                </button>
                {flash ? <p className="text-sm text-emerald-600">{flash}</p> : null}
              </div>
            </form>
          </SettingsSectionCard>
        </div>
      }
      side={
        <SettingsSectionCard title="Current defaults" description={model.sections[1].description}>
          <div className="space-y-3">
            {model.summaryRows.map((row) => (
              <div key={row.label} className="flex items-start justify-between gap-4 border-b border-slate-100 pb-3 last:border-b-0 last:pb-0">
                <span className="text-sm text-slate-500">{row.label}</span>
                <span className="text-sm font-medium text-slate-950">{row.value}</span>
              </div>
            ))}
          </div>
        </SettingsSectionCard>
      }
      title={model.pageTitle}
    />
  );
}
