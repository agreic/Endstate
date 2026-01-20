const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ApiNode {
  node: {
    id: string;
    name?: string;
    description?: string;
    labels?: string[];
    [key: string]: any;
  };
}

export interface ApiRelationship {
  source: string;
  target: string;
  type: string;
  properties?: Record<string, any>;
}

export interface GraphData {
  nodes: ApiNode[];
  relationships: ApiRelationship[];
  total_nodes: number;
  total_relationships: number;
}

export interface GraphStats {
  nodes: Record<string, number>;
  relationships: Record<string, number>;
  total_nodes: number;
  total_relationships: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  content: string;
  sources?: Array<{
    title: string;
    url: string;
  }>;
}

export interface DashboardStats {
  total_nodes: number;
  total_relationships: number;
  conversations?: number;
  insights?: number;
}

export async function fetchGraphData(): Promise<GraphData> {
  const response = await fetch(`${API_URL}/api/graph`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function fetchGraphStats(): Promise<GraphStats> {
  const response = await fetch(`${API_URL}/api/graph/stats`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const response = await fetch(`${API_URL}/api/stats/dashboard`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function fetchHealth(): Promise<{ database: boolean; llm: boolean; database_error?: string; llm_error?: string }> {
  const response = await fetch(`${API_URL}/api/health`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function sendChatMessage(message: string, history: ChatMessage[], enableSearch: boolean = false): Promise<ChatResponse> {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      history,
      enable_web_search: enableSearch,
    }),
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function extractFromText(text: string): Promise<{ message: string; documents_count: number }> {
  const response = await fetch(`${API_URL}/api/extract`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function cleanGraph(label?: string): Promise<{ message: string }> {
  const params = label ? `?label=${encodeURIComponent(label)}` : '';
  const response = await fetch(`${API_URL}/api/clean${params}`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function mergeDuplicates(label: string, matchProperty: string = 'id'): Promise<{ message: string; merged_count: number }> {
  const response = await fetch(`${API_URL}/api/merge?label=${encodeURIComponent(label)}&match_property=${encodeURIComponent(matchProperty)}`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}
