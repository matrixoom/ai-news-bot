import { ModulePageFrame } from "../shared/ui/module-page-frame";
import { ProfessionalPlaceholder } from "../shared/ui/professional-placeholder";

export function NotesPage() {
  return (
    <ModulePageFrame
      contentLayoutClassName="grid gap-6"
      description="Workspace notes."
      main={<ProfessionalPlaceholder title="Notes" description="研究笔记模块正在整理信息结构，暂不新增未定义能力。" />}
      title="Notes"
    />
  );
}
