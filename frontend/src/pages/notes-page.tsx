import { ModulePageFrame } from "../shared/ui/module-page-frame";

export function NotesPage() {
  return (
    <ModulePageFrame
      contentLayoutClassName="grid gap-6"
      description="Workspace notes."
      main={<div className="min-h-80 rounded-lg border border-slate-200 bg-white" />}
      title="Notes"
    />
  );
}
