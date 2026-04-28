import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { previewPush } from "../features/push/api/preview-push";
import { triggerPush } from "../features/push/api/trigger-push";
import { updatePushConfig } from "../features/push/api/update-push-config";
import { PushConfigForm } from "../features/push/components/push-config-form";
import { PushPreviewPanel } from "../features/push/components/push-preview-panel";
import { PushRunHistory } from "../features/push/components/push-run-history";
import { PushSchedulesEditor } from "../features/push/components/push-schedules-editor";
import { usePushModuleQuery } from "../features/push/hooks/use-push-module-query";
import { adaptPushModule, adaptPushPreview, adaptPushRecentRun } from "../features/push/model/push-module-adapter";
import { PUSH_MODULE_TABS, type PushConfig, type PushModuleTab, type PushWorkspaceViewModel } from "../features/push/model/push-module.types";
import { buildModuleTabSearchParams, resolveModuleTab } from "../shared/lib/module-tabs";
import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { ModuleTabBar } from "../shared/ui/module-tab-bar";
import { EmptyPanelState, ErrorPanelState, LoadingPanelState } from "../shared/ui/panel-state";

type FlashState = { tone: "success" | "error" | "neutral"; message: string } | null;

export function PushPage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const activeTab = resolveModuleTab(searchParams.get("tab"), PUSH_MODULE_TABS, "overview");
  const queryClient = useQueryClient();
  const query = usePushModuleQuery(activeTab);
  const [draft, setDraft] = useState<PushConfig | null>(null);
  const [preview, setPreview] = useState<PushWorkspaceViewModel["preview"] | null>(null);
  const [recentRuns, setRecentRuns] = useState<PushWorkspaceViewModel["recentRuns"]>([]);
  const [flash, setFlash] = useState<FlashState>(null);

  useEffect(() => {
    if (!query.data) {
      return;
    }
    setDraft(query.data.config);
    setPreview(query.data.preview);
    setRecentRuns(query.data.recentRuns);
  }, [query.data]);

  const toolbar = (
    <ModuleTabBar
      activeTab={activeTab}
      ariaLabel="Push module tabs"
      pathname={location.pathname}
      searchParams={buildModuleTabSearchParams(searchParams, activeTab)}
      tabs={PUSH_MODULE_TABS}
    />
  );
  const loadingSide = activeTab === "history"
    ? null
    : <LoadingPanelState title="Preview loading" description="Waiting for the push payload to arrive." />;

  const saveMutation = useMutation({
    mutationFn: async () => updatePushConfig(mustDraft(draft)),
    onSuccess: (payload) => {
      const model = adaptPushModule(payload);
      syncWorkspaceState(model);
      setFlash({ tone: "success", message: `Saved to ${model.configPath}.` });
    },
    onError: (error) => {
      setFlash({ tone: "error", message: error instanceof Error ? error.message : "Configuration save failed." });
    },
  });

  const previewMutation = useMutation({
    mutationFn: async () => previewPush(mustDraft(draft)),
    onSuccess: (response) => {
      setPreview(adaptPushPreview(response.preview));
      setFlash({ tone: "success", message: "Preview refreshed." });
    },
    onError: (error) => {
      setFlash({ tone: "error", message: error instanceof Error ? error.message : "Preview refresh failed." });
    },
  });

  const triggerMutation = useMutation({
    mutationFn: async () => triggerPush(mustDraft(draft), preview),
    onSuccess: (response) => {
      setPreview(adaptPushPreview(response.preview));
      setRecentRuns(response.recent_runs.map(adaptPushRecentRun));
      setFlash({ tone: "success", message: "Manual push sent." });
    },
    onError: (error) => {
      setFlash({ tone: "error", message: error instanceof Error ? error.message : "Manual push failed." });
    },
  });

  const frameDescription = query.data?.pageDescription ?? "Configure delivery channels, preview reports, and manage schedules.";

  function syncWorkspaceState(model: PushWorkspaceViewModel) {
    setDraft(model.config);
    setPreview(model.preview);
    setRecentRuns(model.recentRuns);
    queryClient.setQueryData(["push-module", activeTab !== "history"], model);
  }

  if (query.isPending) {
    return (
      <ModulePageFrame
        description={frameDescription}
        lastUpdated={null}
        main={<LoadingPanelState title="Loading push workspace" description="Fetching the latest configuration, preview, and run history." />}
        side={loadingSide}
        title="Push Center"
        toolbar={toolbar}
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
            title="Push module unavailable"
            description="The push payload could not be loaded from the backend."
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
        side={loadingSide}
        title="Push Center"
        toolbar={toolbar}
      />
    );
  }

  if (!draft || !preview) {
    return (
      <ModulePageFrame
        description={query.data.pageDescription}
        lastUpdated={<LastUpdatedBadge value={query.data.generatedAt} />}
        main={<EmptyPanelState title="Push workspace empty" description="The backend returned an empty push payload." />}
        side={loadingSide}
        title={query.data.pageTitle}
        toolbar={toolbar}
      />
    );
  }

  const workspace = query.data;
  const showPreview = activeTab !== "history";
  const side = showPreview ? <PushPreviewPanel preview={preview} refreshAfterMs={workspace.refreshAfterMs} /> : null;
  const contentLayoutClassName = showPreview
    ? "grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]"
    : "grid gap-6";

  return (
    <ModulePageFrame
      contentLayoutClassName={contentLayoutClassName}
      description={workspace.pageDescription}
      lastUpdated={<LastUpdatedBadge value={workspace.generatedAt} />}
      main={renderPushTab(activeTab, {
        workspace,
        draft,
        recentRuns,
        flash,
        isPreviewing: previewMutation.isPending,
        isSaving: saveMutation.isPending,
        isSending: triggerMutation.isPending,
        onDraftChange: setDraft,
        onPreview: () => {
          void previewMutation.mutateAsync();
        },
        onSave: () => {
          void saveMutation.mutateAsync();
        },
        onSend: () => {
          void triggerMutation.mutateAsync();
        },
      })}
      side={side}
      title={workspace.pageTitle}
      toolbar={toolbar}
    />
  );
}

function renderPushTab(
  activeTab: PushModuleTab,
  props: {
    workspace: PushWorkspaceViewModel;
    draft: PushConfig;
    recentRuns: PushWorkspaceViewModel["recentRuns"];
    flash: FlashState;
    isSaving: boolean;
    isPreviewing: boolean;
    isSending: boolean;
    onDraftChange: (next: PushConfig) => void;
    onSave: () => void;
    onPreview: () => void;
    onSend: () => void;
  },
) {
  const { workspace, draft, flash, recentRuns, onDraftChange } = props;

  if (activeTab === "schedules") {
    return (
      <div className="space-y-6">
        <PushSchedulesEditor
          channelTypeOptions={workspace.options.channelTypeOptions}
          onSchedulesChange={(nextSchedules) => {
            onDraftChange({ ...draft, schedules: nextSchedules });
          }}
          schedules={draft.schedules}
          sourceModuleOptions={workspace.options.sourceModuleOptions}
        />
        <PushConfigForm
          channelTypeOptions={workspace.options.channelTypeOptions}
          configPath={workspace.configPath}
          draft={draft}
          flash={flash}
          isPreviewing={props.isPreviewing}
          isSaving={props.isSaving}
          isSending={props.isSending}
          onDraftChange={props.onDraftChange}
          onPreview={props.onPreview}
          onSave={props.onSave}
          onSend={props.onSend}
          sourceModuleOptions={workspace.options.sourceModuleOptions}
          styleOptions={workspace.options.styleOptions}
        />
      </div>
    );
  }

  if (activeTab === "history") {
    return (
      <div className="space-y-6">
        <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">History</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">Run controls</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Review the latest delivery attempts before sending another manual run.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              className="rounded-full border border-cyan-200 bg-cyan-50 px-4 py-2 text-sm font-medium text-cyan-700 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
              disabled={props.isSending}
              onClick={props.onSend}
              type="button"
            >
              {props.isSending ? "Sending..." : "Send now"}
            </button>
          </div>
        </section>
        {flash ? (
          <div
            className={[
              "rounded-2xl border px-4 py-3 text-sm",
              flash.tone === "success"
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : flash.tone === "error"
                  ? "border-rose-200 bg-rose-50 text-rose-700"
                  : "border-slate-200 bg-slate-50 text-slate-700",
            ].join(" ")}
          >
            {flash.message}
          </div>
        ) : null}
        <PushRunHistory runs={recentRuns} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PushConfigForm
        channelTypeOptions={workspace.options.channelTypeOptions}
        configPath={workspace.configPath}
        draft={draft}
        flash={flash}
        isPreviewing={props.isPreviewing}
        isSaving={props.isSaving}
        isSending={props.isSending}
        onDraftChange={props.onDraftChange}
        onPreview={props.onPreview}
        onSave={props.onSave}
        onSend={props.onSend}
        sourceModuleOptions={workspace.options.sourceModuleOptions}
        styleOptions={workspace.options.styleOptions}
      />
      <PushSchedulesEditor
        channelTypeOptions={workspace.options.channelTypeOptions}
        onSchedulesChange={(nextSchedules) => {
          onDraftChange({ ...draft, schedules: nextSchedules });
        }}
        schedules={draft.schedules}
        sourceModuleOptions={workspace.options.sourceModuleOptions}
      />
    </div>
  );
}

function mustDraft(draft: PushConfig | null): PushConfig {
  if (!draft) {
    throw new Error("push draft unavailable");
  }
  return draft;
}
