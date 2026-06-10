/**
 * News 页面已按需求清空。
 * @returns 空内容，避免触发 News 数据获取或渲染任何页面元素。
 */
export function NewsPage() {
  return <ProfessionalPlaceholder title="News" description="资讯聚合能力尚未开放，当前不展示模拟新闻内容。" />;
}
import { ProfessionalPlaceholder } from "../shared/ui/professional-placeholder";
