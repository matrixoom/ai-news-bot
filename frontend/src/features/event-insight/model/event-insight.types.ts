export type InsightTone = "blue" | "green" | "amber" | "rose" | "violet" | "slate";

export type EventInsightEvidence = {
  id: string;
  source: string;
  excerpt: string;
};

export type EventInsightEvent = {
  id: string;
  title: string;
  sourceSummary: string;
  type: string;
  typeTone: InsightTone;
  confidence: string;
  confidenceTone: InsightTone;
  topic: string;
  happenedAt: string;
  status: string;
  statusTone: InsightTone;
  summary: string;
  entities: string[];
  analysisTask: string;
  evidence: EventInsightEvidence[];
};

export type EventInsightTopic = {
  id: number;
  name: string;
  summary?: string;
  lifecycleStage?: string;
  heatScore?: number;
  roleInTopic?: string;
  relevanceScore?: number;
  manualLocked?: boolean;
};

export type EventInsightApiEvidence = {
  id: number;
  rawDocumentId?: number;
  excerpt: string;
  role?: string;
  evidenceLevel?: string;
  sourceTitle?: string;
  sourceUrl?: string;
  startOffset?: number;
  endOffset?: number;
};

export type EventInsightApiEntity = {
  id: number;
  name: string;
  entityType?: string;
  canonicalName?: string;
  role?: string;
  relevanceScore?: number;
};

export type EventInsightApiEvent = {
  id: number;
  title: string;
  summary: string;
  eventTime: string;
  publishedAt?: string | null;
  eventType: string;
  importanceScore?: number;
  noveltyScore?: number;
  marketRelevanceScore?: number;
  confidenceScore: number;
  evidenceLevel?: string;
  analysisStatus?: string;
  graphStatus?: string;
  manualStatus: string;
  sourceMethod?: string;
  createdAt?: string;
  updatedAt?: string;
  topics?: EventInsightTopic[];
  evidence?: EventInsightApiEvidence[];
  entities?: EventInsightApiEntity[];
};

export type EventInsightEventsPayload = {
  traceId: string;
  items: EventInsightApiEvent[];
  page: number;
  pageSize: number;
  total: number;
};

export type EventInsightEventDetailPayload = {
  traceId: string;
  event: EventInsightApiEvent;
};

export type EventInsightEventsQuery = {
  keyword?: string;
  status?: "active" | "ignored" | "archived" | "all";
  topicId?: number;
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
};

export type EventInsightBatchActionPayload = {
  eventIds: number[];
  action: "ignore" | "link_topic";
  params?: Record<string, unknown>;
};

export type EventInsightBatchActionResult = {
  traceId: string;
  succeededEventIds: number[];
  failedItems: Array<{ eventId: number; error: string }>;
};

export type EventInsightTopicsPayload = {
  traceId: string;
  items: EventInsightTopic[];
  total: number;
};

export type TopicTraceMetric = {
  label: string;
  value: string;
  note: string;
  noteTone: InsightTone;
};

export type TopicTraceStage = {
  id: string;
  label: string;
  title: string;
  active?: boolean;
};

export type TopicTimelineEntry = {
  id: string;
  eventId?: number;
  happenedAt: string;
  title: string;
  summary: string;
  roleInTopic?: string;
  relevanceScore?: number;
  evidenceCount?: number;
  evidence?: EventInsightApiEvidence[];
};

export type TopicTracePayload = {
  traceId: string;
  topic: EventInsightTopic;
  metrics: TopicTraceMetric[];
  stages: TopicTraceStage[];
  timeline: TopicTimelineEntry[];
  currentJudgement: {
    title: string;
    summary: string;
    clues: string[];
  };
};

export type GraphNode = {
  id: string;
  eventId?: number;
  kind: string;
  title: string;
  happenedAt: string;
  confidence: string;
  confidenceTone: InsightTone;
  summary: string;
  left: string;
  top: string;
};

export type GraphEdge = {
  id: string;
  sourceNodeId?: string;
  targetNodeId?: string;
  type: "cause" | "parallel" | "risk" | "follow";
  summary?: string;
  strengthScore?: number;
  confidenceScore?: number;
  left: string;
  top: string;
  width: string;
  rotate: string;
};

export type EventGraphPayload = {
  traceId: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId?: string | null;
};
