export type LlmProviderConfig = {
  id: number;
  name: string;
  providerType: string;
  baseUrl: string;
  modelName: string;
  timeoutSeconds: number;
  supportsStructuredOutput: boolean;
  supportsEmbeddings: boolean;
  enabled: boolean;
  apiKeyConfigured: boolean;
  apiKeyPreview: string;
  updatedAt?: string;
};

export type LlmTaskConfig = {
  taskType: string;
  providerId: number;
  providerName: string;
  providerType: string;
  modelName: string;
  temperature: number;
  maxTokens: number;
  enabled: boolean;
};

export type LlmProviderPayload = {
  name: string;
  providerType: string;
  baseUrl: string;
  modelName: string;
  apiKey?: string;
  timeoutSeconds: number;
};

export type RssSourceConfig = {
  id: number;
  name: string;
  url: string;
  language: string;
  category: string;
  enabled: boolean;
  fetchTime: string;
  maxItems: number;
  lastFetchedAt?: string | null;
  updatedAt?: string;
};

export type RssSchedulerConfig = {
  enabled: boolean;
  timezone: string;
  dailyFetchTime: string;
  updatedAt?: string;
};

export type RssSourcePayload = {
  name: string;
  url: string;
  language: string;
  category: string;
  enabled: boolean;
  fetchTime: string;
  maxItems: number;
};
