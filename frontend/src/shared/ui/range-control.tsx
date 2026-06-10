import { useState } from "react";

type RangeSelection = {
  type: string;
  startDate?: string;
  endDate?: string;
};

type RangeOption = {
  value: string;
  label: string;
};

type FrequencyOption = {
  value: string;
  label: string;
};

type RangeControlProps = {
  options: RangeOption[];
  value: RangeSelection;
  onChange: (nextRange: RangeSelection) => void;
  frequencyOptions?: FrequencyOption[];
  frequency?: string;
  onFrequencyChange?: (next: string) => void;
};

export function RangeControl({
  options,
  value,
  onChange,
  frequencyOptions,
  frequency,
  onFrequencyChange,
}: RangeControlProps) {
  const [customOpen, setCustomOpen] = useState(value.type === "custom");
  const [startDate, setStartDate] = useState(value.startDate ?? "");
  const [endDate, setEndDate] = useState(value.endDate ?? "");
  const [error, setError] = useState("");

  function selectRange(nextType: string) {
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
      <div className="flex flex-wrap items-center gap-1.5" aria-label="图表时间范围">
        {options.map((option) => {
          const selected = option.value === value.type;

          return (
            <button
              key={option.value}
              className={[
                "inline-flex min-h-8 items-center rounded-control border px-2.5 text-xs font-medium",
                selected
                  ? "border-accent bg-accent text-white"
                  : "border-line bg-surface text-muted hover:border-accent/40 hover:bg-accent-soft hover:text-accent",
              ].join(" ")}
              onClick={() => selectRange(option.value)}
              type="button"
            >
              {option.label}
            </button>
          );
        })}

        {frequencyOptions && frequencyOptions.length > 0 && frequency ? (
          <div className="ml-auto flex overflow-hidden rounded-control border border-line bg-surface" aria-label="数据频率切换">
            {frequencyOptions.map((option, index) => {
              const selected = option.value === frequency;

              return (
                <button
                  key={option.value}
                  className={[
                    "inline-flex items-center px-2 py-1 text-xs font-medium transition",
                    selected
                      ? "border-accent bg-accent text-white"
                      : "border-transparent bg-surface text-muted hover:bg-accent-soft hover:text-accent",
                    index === 0 ? "border-r border-line" : "",
                  ].join(" ")}
                  onClick={() => onFrequencyChange?.(option.value)}
                  type="button"
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        ) : null}
      </div>

      {customOpen ? (
        <div className="grid gap-3 rounded-panel border border-line bg-surface-subtle p-3 md:grid-cols-[1fr_1fr_auto]">
          <label className="text-sm font-medium text-ink">
            起始日期
            <input
              className="workbench-input mt-1 w-full"
              onChange={(event) => setStartDate(event.target.value)}
              type="date"
              value={startDate}
            />
          </label>
          <label className="text-sm font-medium text-ink">
            结束日期
            <input
              className="workbench-input mt-1 w-full"
              onChange={(event) => setEndDate(event.target.value)}
              type="date"
              value={endDate}
            />
          </label>
          <button
            className="workbench-button-primary self-end"
            onClick={applyCustomRange}
            type="button"
          >
            应用自定义范围
          </button>
          {error ? <p className="text-sm text-negative md:col-span-3">{error}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
