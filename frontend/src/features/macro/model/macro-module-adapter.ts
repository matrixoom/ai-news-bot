import type { MacroModuleRawPayload, MacroModuleViewModel } from "./macro-module.types";

/**
 * 将后端 Macro 模块 payload 转换为前端驼峰命名视图模型。
 * @param response 后端 `/api/frontend/modules/macro` 返回的原始 JSON。
 * @returns Macro 页面组件消费的稳定视图模型。
 */
export function adaptMacroModule(response: MacroModuleRawPayload): MacroModuleViewModel {
  const dataFactors = response.data_factors;
  const sourceMatrix = response.source_matrix;
  const dataModels = response.data_models;

  return {
    generatedAt: response.generated_at,
    pageTitle: "Macro",
    pageDescription: response.module.description,
    moduleLabel: response.module.label,
    moduleNote: response.module.note,
    moduleStatus: response.module.status,
    moduleLoading: response.module.loading,
    dataFactors: {
      status: dataFactors?.status ?? "unavailable",
      label: dataFactors?.label ?? "数据因子",
      defaultFactorCode: dataFactors?.default_factor_code ?? "housing_price",
      groups: dataFactors?.groups ?? [],
      factors: (dataFactors?.factors ?? []).map((factor) => ({
        factorCode: factor.factor_code,
        factorLabel: factor.factor_label,
        category: factor.category,
        description: factor.description,
        defaultUnit: factor.default_unit,
        frequency: factor.frequency,
        sourceKey: factor.source_key,
        storageTable: factor.storage_table,
        calculationMethod: factor.calculation_method,
        displayOrder: factor.display_order,
        status: factor.status,
      })),
      series: (dataFactors?.series ?? []).map((series) => ({
        factorCode: series.factor_code,
        label: series.label,
        unit: series.unit,
        frequency: series.frequency,
        status: series.status,
        sourceLabel: series.source_label,
        points: series.points.map((point) => ({
          periodEnd: point.period_end,
          periodLabel: point.period_label,
          value: point.value,
        })),
      })),
      tableRows: (dataFactors?.table_rows ?? []).map((row) => ({
        factorCode: row.factor_code,
        factorLabel: row.factor_label,
        periodLabel: row.period_label,
        dimension: row.dimension,
        value: row.value,
        unit: row.unit,
        sourceLabel: row.source_label,
        status: row.status,
        updatedAt: row.updated_at,
      })),
    },
    sourceMatrix: {
      status: sourceMatrix?.status ?? "unavailable",
      label: sourceMatrix?.label ?? "数据源矩阵",
      summary: {
        factorCount: sourceMatrix?.summary.factor_count ?? 0,
        sourceCount: sourceMatrix?.summary.source_count ?? 0,
        officialPrimaryCount: sourceMatrix?.summary.official_primary_count ?? 0,
        degradedCount: sourceMatrix?.summary.degraded_count ?? 0,
        unavailableCount: sourceMatrix?.summary.unavailable_count ?? 0,
        lastVerifiedAt: sourceMatrix?.summary.last_verified_at ?? "",
      },
      rows: (sourceMatrix?.rows ?? []).map((row) => ({
        matrixId: row.matrix_id,
        factorCode: row.factor_code,
        factorLabel: row.factor_label,
        sourceKey: row.source_key,
        sourceLabel: row.source_label,
        sourceRole: row.source_role,
        sourceType: row.source_type,
        availabilityStatus: row.availability_status,
        reliabilityLevel: row.reliability_level,
        coverageScope: row.coverage_scope,
        coverageStart: row.coverage_start,
        coverageEnd: row.coverage_end,
        frequency: row.frequency,
        accessMethod: row.access_method,
        fieldMappingStatus: row.field_mapping_status,
        parserStatus: row.parser_status,
        licenseNote: row.license_note,
        priorityOrder: row.priority_order,
        warningMessage: row.warning_message,
        lastVerifiedAt: row.last_verified_at,
      })),
    },
    dataModels: {
      status: dataModels?.status ?? "reserved",
      label: dataModels?.label ?? "数据模型",
      models: dataModels?.models ?? [],
    },
  };
}
