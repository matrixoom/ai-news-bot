import type { ReactNode } from "react";

type PanelStateTone = "neutral" | "loading" | "error";

type PanelStateProps = {
  tone: PanelStateTone;
  title: string;
  description: string;
  action?: ReactNode;
};

const toneStyles: Record<PanelStateTone, string> = {
  neutral: "border-line bg-surface text-ink",
  loading: "border-line bg-surface text-muted",
  error: "border-negative/30 bg-negative/5 text-negative",
};

function PanelState({ tone, title, description, action }: PanelStateProps) {
  return (
    <section className={`rounded-panel border p-5 shadow-panel ${toneStyles[tone]}`} aria-live="polite">
      <p className="workbench-kicker">{tone === "error" ? "异常" : "状态"}</p>
      <h3 className="mt-2 text-base font-semibold text-ink">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
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
