import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { previewPush } from "../features/push/api/preview-push";
import { getPushMarketChartRefresh, startPushMarketChartRefresh } from "../features/push/api/refresh-push-market-charts";
import { triggerPush } from "../features/push/api/trigger-push";
import { updatePushConfig } from "../features/push/api/update-push-config";
import { PushPreviewPanel } from "../features/push/components/push-preview-panel";
import { PushRunHistory } from "../features/push/components/push-run-history";
import { PushSettingsDialog } from "../features/push/components/push-settings-dialog";
import { usePushModuleQuery } from "../features/push/hooks/use-push-module-query";
import { adaptPushMarketChartRefreshJob, adaptPushModule, adaptPushPreview, adaptPushRecentRun } from "../features/push/model/push-module-adapter";
import { PUSH_MODULE_TABS, type PushConfig, type PushMarketChartRefreshJobRaw, type PushWorkspaceViewModel } from "../features/push/model/push-module.types";
import { resolveModuleTab } from "../shared/lib/module-tabs";
import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { EmptyPanelState, ErrorPanelState, LoadingPanelState } from "../shared/ui/panel-state";

type FlashState = { tone: "success" | "error" | "neutral"; message: string } | null;

export function PushPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = resolveModuleTab(searchParams.get("tab"), PUSH_MODULE_TABS, "schedules");
  const queryClient = useQueryClient();
  const query = usePushModuleQuery(activeTab);
  const [draft, setDraft] = useState<PushConfig | null>(null);
  const [preview, setPreview] = useState<PushWorkspaceViewModel["preview"] | null>(null);
  const [recentRuns, setRecentRuns] = useState<PushWorkspaceViewModel["recentRuns"]>([]);
  const [flash, setFlash] = useState<FlashState>(null);
  const [chartRefreshJob, setChartRefreshJob] = useState<ReturnType<typeof adaptPushMarketChartRefreshJob> | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  useEffect(() => {
    if (!query.data) {
      return;
    }
    setDraft(query.data.config);
    setPreview(query.data.preview);
    setRecentRuns(query.data.recentRuns);
  }, [query.data]);

  useEffect(() => {
    if (searchParams.get("tab") === activeTab) {
      return;
    }

    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("tab", activeTab);
    setSearchParams(nextSearchParams, { replace: true });
  }, [activeTab, searchParams, setSearchParams]);

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
    mutationFn: async ({ config, refreshData }: { config: PushConfig; refreshData: boolean }) => previewPush(config, { refreshData }),
    onSuccess: (response) => {
      setPreview(adaptPushPreview(response.preview));
      setFlash({ tone: "success", message: "Preview refreshed." });
    },
    onError: (error) => {
      setFlash({ tone: "error", message: error instanceof Error ? error.message : "Preview refresh failed." });
    },
  });

  const chartRefreshMutation = useMutation({
    mutationFn: async () => startPushMarketChartRefresh(mustDraft(draft)),
    onSuccess: (response) => {
      applyChartRefreshJob(response.job);
    },
    onError: (error) => {
      setFlash({ tone: "error", message: error instanceof Error ? error.message : "Chart refresh failed." });
    },
  });

  useEffect(() => {
    if (!chartRefreshJob || isTerminalChartRefreshStatus(chartRefreshJob.status)) {
      return;
    }
    const timer = window.setTimeout(() => {
      void getPushMarketChartRefresh(chartRefreshJob.id)
        .then((response) => {
          applyChartRefreshJob(response.job);
        })
        .catch((error) => {
          const message = error instanceof Error ? error.message : "Chart refresh status failed.";
          setChartRefreshJob((current) => current ? {
            ...current,
            status: "failed",
            message,
            errors: [message],
          } : current);
        });
    }, 350);
    return () => {
      window.clearTimeout(timer);
    };
  }, [chartRefreshJob]);

  useEffect(() => {
    if (chartRefreshJob?.status !== "completed") {
      return;
    }
    const timer = window.setTimeout(() => {
      setChartRefreshJob(null);
    }, 900);
    return () => {
      window.clearTimeout(timer);
    };
  }, [chartRefreshJob?.status]);

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

  function applyChartRefreshJob(rawJob: PushMarketChartRefreshJobRaw) {
    const nextJob = adaptPushMarketChartRefreshJob(rawJob);
    setChartRefreshJob(nextJob);
    if (!isTerminalChartRefreshStatus(nextJob.status)) {
      return;
    }
    if (nextJob.preview) {
      setPreview(nextJob.preview);
    }
    setFlash({
      tone: nextJob.status === "completed" ? "success" : "neutral",
      message: nextJob.message,
    });
  }

  if (query.isPending) {
    return (
      <ModulePageFrame
        description={frameDescription}
        main={<LoadingPanelState title="Loading push workspace" description="Fetching the latest configuration, preview, and run history." />}
        contentLayoutClassName="grid gap-6"
        showHeader={false}
        side={null}
        title="Push Center"
      />
    );
  }

  if (query.isError || !query.data) {
    return (
      <ModulePageFrame
        description={frameDescription}
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
        contentLayoutClassName="grid gap-6"
        showHeader={false}
        side={null}
        title="Push Center"
      />
    );
  }

  if (!draft || !preview) {
    return (
      <ModulePageFrame
        description={query.data.pageDescription}
        main={<EmptyPanelState title="Push workspace empty" description="The backend returned an empty push payload." />}
        contentLayoutClassName="grid gap-6"
        showHeader={false}
        side={null}
        title={query.data.pageTitle}
      />
    );
  }

  const workspace = query.data;
  const showPreview = activeTab !== "history";
  const main = showPreview ? (
    <PushPreviewPanel
      chartRefreshJob={chartRefreshJob}
      flash={isSettingsOpen ? null : flash}
      isPreviewing={previewMutation.isPending}
      isSending={triggerMutation.isPending}
      marketChartRange={draft.marketChartRange}
      onDismissChartRefresh={() => setChartRefreshJob(null)}
      onMarketChartRangeChange={(marketChartRange) => {
        const nextDraft = { ...draft, marketChartRange };
        setDraft(nextDraft);
        void previewMutation.mutateAsync({ config: nextDraft, refreshData: false });
      }}
      onOpenSettings={() => setIsSettingsOpen(true)}
      onPreview={() => {
        void previewMutation.mutateAsync({ config: draft, refreshData: true });
      }}
      onRefreshCharts={() => {
        setFlash(null);
        void chartRefreshMutation.mutateAsync();
      }}
      onSend={() => {
        void triggerMutation.mutateAsync();
      }}
      preview={preview}
      refreshAfterMs={workspace.refreshAfterMs}
    />
  ) : <PushRunHistory runs={recentRuns} />;

  return (
    <>
      <ModulePageFrame
        contentLayoutClassName="grid gap-6"
        description={workspace.pageDescription}
        main={main}
        side={null}
        showHeader={false}
        title={workspace.pageTitle}
      />
      {activeTab === "schedules" && isSettingsOpen ? (
        <PushSettingsDialog
          channelTypeOptions={workspace.options.channelTypeOptions}
          draft={draft}
          flash={flash}
          isSaving={saveMutation.isPending}
          onClose={() => setIsSettingsOpen(false)}
          onDraftChange={setDraft}
          onSave={() => {
            void saveMutation.mutateAsync();
          }}
          sourceModuleOptions={workspace.options.sourceModuleOptions}
          styleOptions={workspace.options.styleOptions}
        />
      ) : null}
    </>
  );
}

function mustDraft(draft: PushConfig | null): PushConfig {
  if (!draft) {
    throw new Error("push draft unavailable");
  }
  return draft;
}

function isTerminalChartRefreshStatus(status: ReturnType<typeof adaptPushMarketChartRefreshJob>["status"]): boolean {
  return status === "completed" || status === "completed_with_warnings" || status === "failed";
}
