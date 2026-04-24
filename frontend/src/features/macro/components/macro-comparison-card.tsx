import type { MacroComparisonSection } from "../model/macro-module.types";
import { MacroComparisonChart } from "./macro-comparison-chart";

type MacroComparisonCardProps = {
  section: MacroComparisonSection;
};

export function MacroComparisonCard({ section }: MacroComparisonCardProps) {
  const latestDelta = section.deltaPoints[section.deltaPoints.length - 1];

  return (
    <article className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Pair study</p>
          <h3 className="mt-2 text-xl font-semibold text-slate-950">{section.title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{section.description}</p>
        </div>
        <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
          {section.status}
        </span>
      </div>

      <p className="mt-4 text-sm leading-6 text-slate-700">{section.summary}</p>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <IndicatorTile indicator={section.primary} tone="primary" />
        {section.secondary ? <IndicatorTile indicator={section.secondary} tone="secondary" /> : null}
      </div>

      <div className="mt-5">
        <MacroComparisonChart section={section} />
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
          {section.deltaLabel}
          {latestDelta ? `: ${formatDeltaValue(latestDelta.value)}` : ""}
        </span>
        {section.sources.map((source) => (
          <a
            key={`${source.label}-${source.url}`}
            className="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-950"
            href={source.url}
          >
            {source.label}
          </a>
        ))}
      </div>
    </article>
  );
}

function IndicatorTile({
  indicator,
  tone,
}: {
  indicator: MacroComparisonSection["primary"];
  tone: "primary" | "secondary";
}) {
  return (
    <div
      className={[
        "rounded-2xl border p-4",
        tone === "primary" ? "border-slate-200 bg-slate-50" : "border-slate-200 bg-white",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{tone === "primary" ? "Primary" : "Secondary"}</p>
          <h4 className="mt-2 text-base font-semibold text-slate-950">{indicator.label}</h4>
        </div>
        <span className="rounded-full bg-slate-950 px-2.5 py-1 text-xs font-medium text-white">{indicator.frequency}</span>
      </div>

      <p className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{indicator.latestValue}</p>
      <p className="mt-2 text-sm text-slate-600">{indicator.changeLabel}</p>
      <p className="mt-3 text-sm leading-6 text-slate-600">{indicator.context}</p>
      <a
        className="mt-4 inline-flex text-sm font-medium text-slate-950 underline decoration-slate-300 underline-offset-4 hover:decoration-slate-950"
        href={indicator.sourceUrl}
      >
        {indicator.sourceLabel}
      </a>
    </div>
  );
}

function formatDeltaValue(value: number): string {
  return Number.isInteger(value) ? value.toString() : value.toFixed(1);
}
