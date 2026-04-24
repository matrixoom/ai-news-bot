import type {
  PushConfig,
  PushConfigRaw,
  PushModuleRawPayload,
  PushPreview,
  PushPreviewRaw,
  PushRecentRun,
  PushRecentRunRaw,
  PushWorkspaceViewModel,
} from "./push-module.types";

const DEFAULT_CONFIG: PushConfig = {
  selectedModuleIds: ["market"],
  reportStyle: "newspaper",
  email: {
    enabled: true,
    label: "Primary Email",
    smtpServer: "",
    smtpPort: 587,
    useTls: true,
    username: "",
    password: "",
    passwordConfigured: false,
    fromAddress: "",
    toAddresses: "",
  },
  schedules: [],
};

export function adaptPushModule(response: PushModuleRawPayload): PushWorkspaceViewModel {
  const section = response.module.details[0]?.section;

  return {
    generatedAt: response.generated_at,
    refreshAfterMs: response.refresh_after_ms ?? 30_000,
    pageTitle: response.module.label,
    pageDescription: response.module.description,
    moduleNote: response.module.note,
    moduleStatus: response.module.status,
    moduleLoading: response.module.loading,
    configPath: section?.config_path ?? ".data/push_center.json",
    config: section ? adaptPushConfig(section.config) : DEFAULT_CONFIG,
    preview: section ? adaptPushPreview(section.preview) : emptyPreview(response.generated_at),
    recentRuns: (section?.recent_runs ?? []).map(adaptPushRecentRun),
    scheduler: {
      enabled: section?.scheduler.enabled ?? false,
      checkIntervalSeconds: section?.scheduler.check_interval_seconds ?? 20,
    },
    options: {
      channelTypeOptions: section?.channel_type_options ?? [],
      sourceModuleOptions: section?.source_module_options ?? [],
      styleOptions: section?.style_options ?? [],
    },
  };
}

export function adaptPushConfig(config: PushConfigRaw): PushConfig {
  return {
    selectedModuleIds: config.selected_module_ids ?? ["market"],
    reportStyle: config.report_style ?? "newspaper",
    email: {
      enabled: Boolean(config.email?.enabled),
      label: config.email?.label ?? "Primary Email",
      smtpServer: config.email?.smtp_server ?? "",
      smtpPort: config.email?.smtp_port ?? 587,
      useTls: config.email?.use_tls ?? true,
      username: config.email?.username ?? "",
      password: config.email?.password ?? "",
      passwordConfigured: Boolean(config.email?.password_configured),
      fromAddress: config.email?.from_address ?? "",
      toAddresses: config.email?.to_addresses ?? "",
    },
    schedules: (config.schedules ?? []).map((schedule) => ({
      id: schedule.id,
      name: schedule.name,
      enabled: schedule.enabled,
      moduleIds: schedule.module_ids,
      channelTypes: schedule.channel_types,
      times: schedule.times,
      timezone: schedule.timezone,
    })),
  };
}

export function toPushConfigRaw(config: PushConfig): PushConfigRaw {
  return {
    selected_module_ids: config.selectedModuleIds,
    report_style: config.reportStyle,
    email: {
      enabled: config.email.enabled,
      label: config.email.label,
      smtp_server: config.email.smtpServer,
      smtp_port: config.email.smtpPort,
      use_tls: config.email.useTls,
      username: config.email.username,
      password: config.email.password,
      password_configured: config.email.passwordConfigured,
      from_address: config.email.fromAddress,
      to_addresses: config.email.toAddresses,
    },
    schedules: config.schedules.map((schedule) => ({
      id: schedule.id,
      name: schedule.name,
      enabled: schedule.enabled,
      module_ids: schedule.moduleIds,
      channel_types: schedule.channelTypes,
      times: schedule.times,
      timezone: schedule.timezone,
    })),
  };
}

export function toPushPreviewRaw(preview: PushPreview): PushPreviewRaw {
  return {
    ok: preview.ok,
    generated_at: preview.generatedAt,
    subject: preview.subject,
    text_body: preview.textBody,
    html_body: preview.htmlBody,
    style: preview.style,
    selected_module_ids: preview.selectedModuleIds,
    error: preview.error,
  };
}

export function adaptPushPreview(preview: PushPreviewRaw): PushPreview {
  return {
    ok: preview.ok,
    generatedAt: preview.generated_at,
    subject: preview.subject,
    textBody: preview.text_body,
    htmlBody: preview.html_body,
    style: preview.style,
    selectedModuleIds: preview.selected_module_ids,
    error: preview.error ?? "",
  };
}

export function adaptPushRecentRun(run: PushRecentRunRaw): PushRecentRun {
  return {
    executedAt: run.executed_at,
    timezone: run.timezone,
    trigger: run.trigger,
    jobName: run.job_name,
    status: run.status,
    detail: run.detail,
    subject: run.subject,
    channelTypes: run.channel_types,
    moduleIds: run.module_ids,
  };
}

function emptyPreview(generatedAt: string): PushPreview {
  return {
    ok: false,
    generatedAt,
    subject: "",
    textBody: "",
    htmlBody: "",
    style: "newspaper",
    selectedModuleIds: ["market"],
    error: "preview_unavailable",
  };
}
