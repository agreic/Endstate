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
  role: string;
  content: string;
}

export interface ChatResponse {
  success: boolean;
  content?: string;
  already_processed?: boolean;
  is_processing?: boolean;
}

export interface DashboardStats {
  total_nodes: number;
  total_relationships: number;
  conversations?: number;
  insights?: number;
}

export interface ChatHistoryResponse {
  messages: Array<{
    role: string;
    content: string;
    timestamp: string;
  }>;
}

export interface ProjectSummary {
  session_id: string;
  created_at: string;
  updated_at: string;
  user_profile: {
    interests: string[];
    skill_level: string;
    time_available: string;
    learning_style: string;
  };
  agreed_project: {
    name: string;
    description: string;
    timeline: string;
    milestones: string[];
  };
  topics: string[];
  skills: string[];
  concepts: string[];
}

export interface ProjectListItem {
  id: string;
  name: string;
  created_at: string;
  interests: string[];
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

export async function deleteNode(nodeId: string): Promise<{ deleted_node_id: string; relationships_deleted: number }> {
  const response = await fetch(`${API_URL}/api/graph/nodes/${encodeURIComponent(nodeId)}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete node' }));
    throw new Error(error.detail || 'Failed to delete node');
  }
  return response.json();
}

export async function deleteRelationship(sourceId: string, targetId: string, relType: string): Promise<{ deleted: boolean }> {
  const params = new URLSearchParams({
    source_id: sourceId,
    target_id: targetId,
    rel_type: relType,
  });
  const response = await fetch(`${API_URL}/api/graph/relationships?${params}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete relationship' }));
    throw new Error(error.detail || 'Failed to delete relationship');
  }
  return response.json();
}

export async function getNodeConnections(nodeId: string): Promise<{ node_id: string; connections: Array<{ id: string; labels: string[]; rel_type: string }> }> {
  const response = await fetch(`${API_URL}/api/graph/node/${encodeURIComponent(nodeId)}/connections`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function getChatHistory(sessionId: string): Promise<{ messages: Array<{ role: string; content: string; timestamp: string }>; is_locked?: boolean }> {
  const response = await fetch(`${API_URL}/api/chat/${sessionId}/messages`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function checkSessionLocked(sessionId: string): Promise<{ locked: boolean }> {
  const response = await fetch(`${API_URL}/api/chat/${sessionId}/locked`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function deleteChatSession(sessionId: string): Promise<{ message: string }> {
  const response = await fetch(`${API_URL}/api/chat/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function resetChatSession(sessionId: string): Promise<{ message: string }> {
  const response = await fetch(`${API_URL}/api/chat/${encodeURIComponent(sessionId)}/reset`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function sendChatMessage(
  message: string,
  enableSearch: boolean = false,
  sessionId?: string,
  requestId?: string,
  signal?: AbortSignal
): Promise<ChatResponse> {
  const endpoint = sessionId 
    ? `${API_URL}/api/chat/${sessionId}/messages`
    : `${API_URL}/api/chat`;
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (requestId) {
    headers['X-Request-ID'] = requestId;
  }
  
  const init: RequestInit = {
    method: 'POST',
    headers,
    body: JSON.stringify({
      message,
      enable_web_search: enableSearch,
    }),
  };
  
  if (signal) {
    init.signal = signal;
  }
  
  const response = await fetch(endpoint, init);
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

export async function listProjects(): Promise<{ projects: ProjectListItem[] }> {
  const response = await fetch(`${API_URL}/api/projects`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function getProject(projectId: string): Promise<ProjectSummary> {
  const response = await fetch(`${API_URL}/api/projects/${encodeURIComponent(projectId)}`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export async function deleteProject(projectId: string): Promise<{ message: string }> {
  const response = await fetch(`${API_URL}/api/projects/${encodeURIComponent(projectId)}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}
