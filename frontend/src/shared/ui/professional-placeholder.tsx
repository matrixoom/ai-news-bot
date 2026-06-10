import { BeakerIcon } from "@heroicons/react/24/outline";

type ProfessionalPlaceholderProps = {
  title: string;
  description: string;
};

/** 渲染未开放模块的专业占位态，不虚构业务能力或示例数据。 */
export function ProfessionalPlaceholder({ title, description }: ProfessionalPlaceholderProps) {
  return (
    <section className="workbench-panel flex min-h-72 items-center justify-center p-8">
      <div className="max-w-md text-center">
        <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-control bg-accent-soft text-accent">
          <BeakerIcon aria-hidden="true" className="h-6 w-6" />
        </div>
        <h3 className="mt-4 text-lg font-semibold text-ink">{title}</h3>
        <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
      </div>
    </section>
  );
}
