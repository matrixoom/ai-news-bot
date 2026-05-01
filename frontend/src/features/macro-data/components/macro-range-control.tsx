import { useState } from "react";
import type { MacroDataRangeSelection, MacroRangeOption } from "../model/macro-data.types";

type MacroRangeControlProps = {
  options: MacroRangeOption[];
  value: MacroDataRangeSelection;
  onChange: (nextRange: MacroDataRangeSelection) => void;
};

export function MacroRangeControl({ options, value, onChange }: MacroRangeControlProps) {
  const [customOpen, setCustomOpen] = useState(value.type === "custom");
  const [startDate, setStartDate] = useState(value.startDate ?? "");
  const [endDate, setEndDate] = useState(value.endDate ?? "");
  const [error, setError] = useState("");

  function selectRange(nextType: MacroDataRangeSelection["type"]) {
    setError("");
    if (nextType === "custom") {
      setCustomOpen(true);
      return;
    }
    setCustomOpen(false);
    onChange({ type: nextType });
  }

  function applyCustomRange() {
    if (!startDate || !endDate) {
      setError("请选择起始日期和结束日期。");
      return;
    }
    if (startDate > endDate) {
      setError("起始日期不能晚于结束日期。");
      return;
    }
    setError("");
    onChange({ type: "custom", startDate, endDate });
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2" aria-label="图表时间范围">
        {options.map((option) => {
          const selected = option.value === value.type;

          return (
            <button
              key={option.value}
              className={[
                "inline-flex items-center rounded-full border px-3 py-1.5 text-sm font-medium transition",
                selected
                  ? "border-slate-900 bg-slate-900 text-white"
                  : "border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300 hover:text-slate-950",
              ].join(" ")}
              onClick={() => selectRange(option.value)}
              type="button"
            >
              {option.label}
            </button>
          );
        })}
      </div>

      {customOpen ? (
        <div className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 md:grid-cols-[1fr_1fr_auto]">
          <label className="text-sm font-medium text-slate-700">
            起始日期
            <input
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900"
              onChange={(event) => setStartDate(event.target.value)}
              type="date"
              value={startDate}
            />
          </label>
          <label className="text-sm font-medium text-slate-700">
            结束日期
            <input
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900"
              onChange={(event) => setEndDate(event.target.value)}
              type="date"
              value={endDate}
            />
          </label>
          <button
            className="self-end rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white"
            onClick={applyCustomRange}
            type="button"
          >
            应用自定义范围
          </button>
          {error ? <p className="text-sm text-rose-600 md:col-span-3">{error}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
