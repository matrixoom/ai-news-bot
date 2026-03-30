import type { ReactNode } from "react";

type PanelStateTone = "neutral" | "loading" | "error";

type PanelStateProps = {
  tone: PanelStateTone;
  title: string;
  description: string;
  action?: ReactNode;
};

const toneStyles: Record<PanelStateTone, string> = {
  neutral: "border-slate-200 bg-white text-slate-700",
  loading: "border-slate-200 bg-white text-slate-500",
  error: "border-rose-200 bg-rose-50 text-rose-700",
};

function PanelState({ tone, title, description, action }: PanelStateProps) {
  return (
    <section className={`rounded-[1.75rem] border p-6 shadow-sm ${toneStyles[tone]}`} aria-live="polite">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{tone === "error" ? "Problem" : "Status"}</p>
      <h3 className="mt-3 text-lg font-semibold text-slate-950">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </section>
  );
}

export function LoadingPanelState({ title, description }: Omit<PanelStateProps, "tone">) {
  return <PanelState tone="loading" title={title} description={description} />;
}

export function EmptyPanelState({ title, description, action }: Omit<PanelStateProps, "tone">) {
  return <PanelState tone="neutral" title={title} description={description} action={action} />;
}

export function ErrorPanelState({ title, description, action }: Omit<PanelStateProps, "tone">) {
  return <PanelState tone="error" title={title} description={description} action={action} />;
}
