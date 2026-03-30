import type { StatusModuleRawPayload, StatusModuleViewModel } from "./status-module.types";

export function adaptStatusModule(response: StatusModuleRawPayload): StatusModuleViewModel {
  return {
    generatedAt: response.generated_at,
    pageTitle: "Status",
    pageDescription: response.module.description,
    coverageNote: response.coverage_note,
    moduleLabel: response.module.label,
    moduleNote: response.module.note,
    moduleStatus: response.module.status,
    moduleLoading: response.module.loading,
    statusItems: response.module.details.map((detail) => ({
      id: detail.section.key,
      label: detail.section.label,
      status: detail.section.status,
      detail: detail.section.detail,
    })),
  };
}
