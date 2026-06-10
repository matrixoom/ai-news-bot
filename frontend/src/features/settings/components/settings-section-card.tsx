import type { ReactNode } from "react";

type SettingsSectionCardProps = {
  title: string;
  description: string;
  children: ReactNode;
};

export function SettingsSectionCard({ title, description, children }: SettingsSectionCardProps) {
  return (
    <section className="border-b border-line pb-6">
      <p className="workbench-kicker">Settings</p>
      <h3 className="mt-2 text-lg font-semibold text-ink">{title}</h3>
      <p className="mt-1 text-sm leading-6 text-muted">{description}</p>
      <div className="mt-5">{children}</div>
    </section>
  );
}
