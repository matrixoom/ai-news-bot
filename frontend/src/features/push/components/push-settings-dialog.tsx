import { XMarkIcon } from "@heroicons/react/24/outline";
import type {
  PushChannelOption,
  PushConfig,
  PushSourceModuleOption,
  PushStyleOption,
} from "../model/push-module.types";
import { PushConfigForm } from "./push-config-form";
import { PushFlashMessage } from "./push-flash-message";
import { PushSchedulesEditor } from "./push-schedules-editor";

type PushSettingsDialogProps = {
  draft: PushConfig;
  channelTypeOptions: PushChannelOption[];
  sourceModuleOptions: PushSourceModuleOption[];
  styleOptions: PushStyleOption[];
  flash: { tone: "success" | "error" | "neutral"; message: string } | null;
  isSaving: boolean;
  onClose: () => void;
  onDraftChange: (next: PushConfig) => void;
  onSave: () => void;
};

/** 收纳 Push Center 计划任务和投递配置，关闭时保留页面草稿。 */
export function PushSettingsDialog(props: PushSettingsDialogProps) {
  return (
    <div
      aria-labelledby="push-settings-title"
      aria-modal="true"
      className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/40 p-4"
      role="dialog"
    >
      <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-3xl bg-slate-50 p-5 shadow-xl sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Configuration</p>
            <h3 className="mt-2 text-xl font-semibold text-slate-950" id="push-settings-title">推送设置</h3>
          </div>
          <button aria-label="关闭推送设置" className="rounded-full border border-slate-200 bg-white p-2 text-slate-600" onClick={props.onClose} type="button">
            <XMarkIcon aria-hidden="true" className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-5"><PushFlashMessage flash={props.flash} /></div>
        <div className="mt-5 space-y-6">
          <PushSchedulesEditor
            channelTypeOptions={props.channelTypeOptions}
            onSchedulesChange={(schedules) => props.onDraftChange({ ...props.draft, schedules })}
            schedules={props.draft.schedules}
            sourceModuleOptions={props.sourceModuleOptions}
          />
          <PushConfigForm
            channelTypeOptions={props.channelTypeOptions}
            draft={props.draft}
            isSaving={props.isSaving}
            onDraftChange={props.onDraftChange}
            onSave={props.onSave}
            sourceModuleOptions={props.sourceModuleOptions}
            styleOptions={props.styleOptions}
          />
        </div>
      </div>
    </div>
  );
}
