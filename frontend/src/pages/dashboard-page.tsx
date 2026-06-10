/**
 * Dashboard 页面已按需求清空。
 * @returns 空内容，避免触发 Dashboard 数据获取或渲染任何页面元素。
 */
export function DashboardPage() {
  return <ProfessionalPlaceholder title="Dashboard" description="综合看板尚未开放，现有研究模块可通过侧栏直接访问。" />;
}
import { ProfessionalPlaceholder } from "../shared/ui/professional-placeholder";
