import type { ModuleTabDefinition } from "../../../shared/lib/module-tabs";

export type PushModuleRawPayload = {
  generated_at: string;
  refresh_after_ms?: number;
  module: {
    id: "push";
    label: string;
    note: string;
    description: string;
    status: string;
    loading: boolean;
    details: Array<{
      id: string;
      label: string;
      kind: "push";
      note: string;
      section: PushWorkspaceRawSection;
    }>;
  };
};

export type PushWorkspaceRawSection = {
  channel_type_options: PushChannelOption[];
  source_module_options: PushSourceModuleOption[];
  style_options: PushStyleOption[];
  config_path: string;
  config: PushConfigRaw;
  preview: PushPreviewRaw;
  recent_runs: PushRecentRunRaw[];
  scheduler: PushSchedulerInfoRaw;
};

export type PushChannelOption = {
  id: string;
  label: string;
  enabled: boolean;
  description: string;
};

export type PushSourceModuleOption = {
  id: string;
  label: string;
  enabled: boolean;
  push_ready: boolean;
  description: string;
};

export type PushStyleOption = {
  id: string;
  label: string;
  recommended: boolean;
  description: string;
};

export type PushEmailConfigRaw = {
  enabled: boolean;
  label: string;
  smtp_server: string;
  smtp_port: number;
  use_tls: boolean;
  username: string;
  password: string;
  password_configured?: boolean;
  from_address: string;
  to_addresses: string;
};

export type PushScheduleRaw = {
  id: string;
  name: string;
  enabled: boolean;
  module_ids: string[];
  channel_types: string[];
  times: string[];
  timezone: string;
};

export type PushConfigRaw = {
  selected_module_ids: string[];
  report_style: string;
  email: PushEmailConfigRaw;
  schedules: PushScheduleRaw[];
};

export type PushPreviewRaw = {
  ok: boolean;
  generated_at: string;
  subject: string;
  text_body: string;
  html_body: string;
  style: string;
  selected_module_ids: string[];
  error?: string;
};

export type PushRecentRunRaw = {
  executed_at: string;
  timezone: string;
  trigger: string;
  job_name: string;
  status: string;
  detail: string;
  subject: string;
  channel_types: string[];
  module_ids: string[];
};

export type PushSchedulerInfoRaw = {
  enabled: boolean;
  check_interval_seconds: number;
};

export type PushEmailConfig = {
  enabled: boolean;
  label: string;
  smtpServer: string;
  smtpPort: number;
  useTls: boolean;
  username: string;
  password: string;
  passwordConfigured: boolean;
  fromAddress: string;
  toAddresses: string;
};

export type PushSchedule = {
  id: string;
  name: string;
  enabled: boolean;
  moduleIds: string[];
  channelTypes: string[];
  times: string[];
  timezone: string;
};

export type PushConfig = {
  selectedModuleIds: string[];
  reportStyle: string;
  email: PushEmailConfig;
  schedules: PushSchedule[];
};

export type PushPreview = {
  ok: boolean;
  generatedAt: string;
  subject: string;
  textBody: string;
  htmlBody: string;
  style: string;
  selectedModuleIds: string[];
  error: string;
};

export type PushRecentRun = {
  executedAt: string;
  timezone: string;
  trigger: string;
  jobName: string;
  status: string;
  detail: string;
  subject: string;
  channelTypes: string[];
  moduleIds: string[];
};

export type PushSchedulerInfo = {
  enabled: boolean;
  checkIntervalSeconds: number;
};

export type PushWorkspaceViewModel = {
  generatedAt: string;
  refreshAfterMs: number;
  pageTitle: string;
  pageDescription: string;
  moduleNote: string;
  moduleStatus: string;
  moduleLoading: boolean;
  configPath: string;
  config: PushConfig;
  preview: PushPreview;
  recentRuns: PushRecentRun[];
  scheduler: PushSchedulerInfo;
  options: {
    channelTypeOptions: PushChannelOption[];
    sourceModuleOptions: PushSourceModuleOption[];
    styleOptions: PushStyleOption[];
  };
};

export type PushPreviewResponseRaw = {
  generated_at: string;
  config: PushConfigRaw;
  preview: PushPreviewRaw;
};

export type TriggerPushResponseRaw = {
  ok: boolean;
  preview: PushPreviewRaw;
  recent_runs: PushRecentRunRaw[];
  result: {
    status: string;
    executed_at: string;
    timezone: string;
    trigger: string;
    job_name: string;
    sent: string[];
    failed: string[];
    detail: string;
  };
};

export type PushModuleTab = "overview" | "schedules" | "history";

export const PUSH_MODULE_TABS: readonly ModuleTabDefinition<PushModuleTab>[] = [
  { value: "overview", label: "Overview" },
  { value: "schedules", label: "Schedules" },
  { value: "history", label: "History" },
];
