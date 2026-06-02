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
  happenedAt: string;
  title: string;
  summary: string;
};

export type GraphNode = {
  id: string;
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
  type: "cause" | "parallel" | "risk" | "follow";
  left: string;
  top: string;
  width: string;
  rotate: string;
};
