import { ArrowDownTrayIcon, PlusIcon } from "@heroicons/react/24/outline";
import { useEffect, useState } from "react";
import { formatLocalDateTime } from "../../../shared/utils/format-local-date-time";
import { useEventGraphQuery } from "../hooks/use-event-graph-query";
import { EventInsightShell, InsightBadge, InsightPanel } from "./event-insight-shell";

const EDGE_CLASSES = { cause: "bg-blue-600", parallel: "bg-violet-600", risk: "border-t-2 border-dashed border-rose-600", follow: "bg-emerald-600" };

/** 渲染事件关系图工作台，返回可选择节点的真实画布。 */
export function EventGraphWorkspace() {
  const topicId = 1;
  const graphQuery = useEventGraphQuery(topicId);
  const graph = graphQuery.data;
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const selectedNode = graph?.nodes.find((node) => node.id === selectedId) ?? graph?.nodes[0];
  const relationSummary = graph?.edges.find((edge) => edge.sourceNodeId === selectedNode?.id || edge.targetNodeId === selectedNode?.id)?.summary;

  useEffect(() => {
    if (graph?.selectedNodeId) {
      setSelectedId((current) => current ?? graph.selectedNodeId ?? undefined);
    }
  }, [graph?.selectedNodeId]);

  return (
    <EventInsightShell
      title="事件关系图"
      description="查看事件之间的因果、并行、风险与跟随关系，在图谱上快速定位关键节点和需要补证的推断。"
      actions={<><button className="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700" type="button"><PlusIcon aria-hidden="true" className="mr-1 inline h-4 w-4" />新增关系</button><button className="rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white" type="button"><ArrowDownTrayIcon aria-hidden="true" className="mr-1 inline h-4 w-4" />保存视图</button></>}
    >
      {graphQuery.isLoading ? <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-500">正在加载事件关系图...</div> : null}
      {graphQuery.isError ? <div className="rounded-lg border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">事件关系图加载失败，请检查主题或关系数据。</div> : null}
      {graph ? <>
      <div className="flex flex-wrap gap-2 rounded-lg border border-slate-200 bg-white p-3">
        <input aria-label="搜索图谱节点" className="h-9 w-64 rounded-md border border-slate-300 px-3 text-xs" placeholder="搜索事件、实体或主题" />
        <select aria-label="关系图主题" className="h-9 rounded-md border border-slate-300 px-3 text-xs"><option>主题 #1</option></select>
        <select aria-label="关系图时间范围" className="h-9 rounded-md border border-slate-300 px-3 text-xs"><option>最近 90 天</option></select>
      </div>
      <div className="grid min-h-[650px] gap-3 xl:grid-cols-[208px_minmax(0,1fr)_300px]">
        <InsightPanel className="p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">关系类型</h3>
          {["因果关系", "并行关系", "风险关系", "跟随关系"].map((item) => <label className="mt-3 flex items-center gap-2 text-xs text-slate-700" key={item}><input defaultChecked type="checkbox" />{item}</label>)}
          <h3 className="mt-6 border-t border-slate-200 pt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">节点可信度</h3>
          {["高可信", "中可信", "低可信"].map((item, index) => <label className="mt-3 flex items-center gap-2 text-xs text-slate-700" key={item}><input defaultChecked={index < 2} type="checkbox" />{item}</label>)}
        </InsightPanel>
        <InsightPanel className="relative min-h-[650px] bg-slate-50" >
          <div aria-label="事件关系图画布" className="absolute inset-0 overflow-hidden bg-[radial-gradient(circle_at_1px_1px,_#cbd5e1_1px,_transparent_0)] [background-size:18px_18px]">
            {graph.edges.map((edge) => <i aria-label={edge.summary || edge.id} className={`absolute h-0.5 origin-left ${EDGE_CLASSES[edge.type]}`} key={edge.id} style={{ left: edge.left, top: edge.top, width: edge.width, transform: `rotate(${edge.rotate})` }} />)}
            {graph.nodes.length === 0 ? <p className="m-4 rounded-md border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">暂无可展示节点。</p> : null}
            {graph.nodes.map((node) => <button aria-label={`查看节点 ${node.title}`} className={`absolute w-40 rounded-md border bg-white p-3 text-left shadow-md ${selectedNode?.id === node.id ? "border-blue-600 ring-4 ring-blue-100" : "border-slate-300"}`} key={node.id} onClick={() => setSelectedId(node.id)} style={{ left: node.left, top: node.top }} type="button"><span className="text-[10px] text-slate-500">{node.kind}</span><strong className="mt-1 block text-xs leading-5 text-slate-950">{node.title}</strong><small className="mt-1 block text-[10px] text-slate-400">{formatLocalDateTime(node.happenedAt)}</small></button>)}
          </div>
        </InsightPanel>
        <InsightPanel title="节点详情">
          <div className="space-y-4 p-4">
            {selectedNode ? <>
            <h4 className="text-base font-semibold leading-6 text-slate-950">{selectedNode.title}</h4>
            <p className="text-xs leading-6 text-slate-600">{selectedNode.summary}</p>
            <InsightBadge tone={selectedNode.confidenceTone}>{selectedNode.confidence}</InsightBadge>
            <dl className="grid grid-cols-[72px_1fr] gap-y-2 border-t border-slate-200 pt-3 text-xs leading-5">
              <dt className="text-slate-500">节点类型</dt><dd className="text-slate-700">{selectedNode.kind}</dd>
              <dt className="text-slate-500">发生时间</dt><dd className="text-slate-700">{formatLocalDateTime(selectedNode.happenedAt)}</dd>
              <dt className="text-slate-500">关系概览</dt><dd className="text-slate-700">{relationSummary || "暂无关系摘要"}</dd>
            </dl>
            </> : <p className="text-sm text-slate-500">请选择一个节点查看详情。</p>}
          </div>
        </InsightPanel>
      </div>
      </> : null}
    </EventInsightShell>
  );
}
