import type { ModuleTabDefinition } from "../../../shared/lib/module-tabs";

export type MacroModuleTab = "data_factors" | "source_matrix" | "data_models";

export const MACRO_MODULE_TABS: readonly ModuleTabDefinition<MacroModuleTab>[] = [
  { value: "data_factors", label: "数据因子" },
  { value: "source_matrix", label: "数据源矩阵" },
  { value: "data_models", label: "数据模型" },
];

export type MacroFactorDefinition = {
  factorCode: string;
  factorLabel: string;
  category: string;
  description: string;
  defaultUnit: string;
  frequency: string;
  sourceKey: string;
  storageTable: string;
  calculationMethod: string;
  displayOrder: number;
  status: string;
};

export type MacroFactorSeriesPoint = {
  periodEnd: string;
  periodLabel: string;
  value: number;
};

export type MacroFactorSeries = {
  factorCode: string;
  label: string;
  unit: string;
  frequency: string;
  status: string;
  sourceLabel: string;
  points: MacroFactorSeriesPoint[];
};

export type MacroFactorTableRow = {
  factorCode: string;
  factorLabel: string;
  periodLabel: string;
  dimension: string;
  value: string;
  unit: string;
  sourceLabel: string;
  status: string;
  updatedAt: string;
};

export type MacroSourceMatrixSummary = {
  factorCount: number;
  sourceCount: number;
  officialPrimaryCount: number;
  degradedCount: number;
  unavailableCount: number;
  lastVerifiedAt: string;
};

export type MacroSourceMatrixRow = {
  matrixId: string;
  factorCode: string;
  factorLabel: string;
  sourceKey: string;
  sourceLabel: string;
  sourceRole: string;
  sourceType: string;
  availabilityStatus: string;
  reliabilityLevel: string;
  coverageScope: string;
  coverageStart: string;
  coverageEnd: string;
  frequency: string;
  accessMethod: string;
  fieldMappingStatus: string;
  parserStatus: string;
  licenseNote: string;
  priorityOrder: number;
  warningMessage: string;
  lastVerifiedAt: string;
};

export type MacroModuleRawPayload = {
  generated_at: string;
  module: {
    id: "macro";
    label: string;
    note: string;
    description: string;
    status: string;
    loading: boolean;
    details: unknown[];
  };
  data_factors?: {
    status: string;
    label: string;
    default_factor_code: string;
    groups: Array<{ value: string; label: string }>;
    factors: Array<{
      factor_code: string;
      factor_label: string;
      category: string;
      description: string;
      default_unit: string;
      frequency: string;
      source_key: string;
      storage_table: string;
      calculation_method: string;
      display_order: number;
      status: string;
    }>;
    series: Array<{
      factor_code: string;
      label: string;
      unit: string;
      frequency: string;
      status: string;
      source_label: string;
      points: Array<{
        period_end: string;
        period_label: string;
        value: number;
      }>;
    }>;
    table_rows: Array<{
      factor_code: string;
      factor_label: string;
      period_label: string;
      dimension: string;
      value: string;
      unit: string;
      source_label: string;
      status: string;
      updated_at: string;
    }>;
    sources: unknown[];
  };
  source_matrix?: {
    status: string;
    label: string;
    summary: {
      factor_count: number;
      source_count: number;
      official_primary_count: number;
      degraded_count: number;
      unavailable_count: number;
      last_verified_at: string;
    };
    rows: Array<{
      matrix_id: string;
      factor_code: string;
      factor_label: string;
      source_key: string;
      source_label: string;
      source_role: string;
      source_type: string;
      availability_status: string;
      reliability_level: string;
      coverage_scope: string;
      coverage_start: string;
      coverage_end: string;
      frequency: string;
      access_method: string;
      field_mapping_status: string;
      parser_status: string;
      license_note: string;
      priority_order: number;
      warning_message: string;
      last_verified_at: string;
    }>;
  };
  data_models?: {
    status: string;
    label: string;
    models: unknown[];
  };
};

export type MacroModuleViewModel = {
  generatedAt: string;
  pageTitle: string;
  pageDescription: string;
  moduleLabel: string;
  moduleNote: string;
  moduleStatus: string;
  moduleLoading: boolean;
  dataFactors: {
    status: string;
    label: string;
    defaultFactorCode: string;
    groups: Array<{ value: string; label: string }>;
    factors: MacroFactorDefinition[];
    series: MacroFactorSeries[];
    tableRows: MacroFactorTableRow[];
  };
  sourceMatrix: {
    status: string;
    label: string;
    summary: MacroSourceMatrixSummary;
    rows: MacroSourceMatrixRow[];
  };
  dataModels: {
    status: string;
    label: string;
    models: unknown[];
  };
};
