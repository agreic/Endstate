const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface GraphNode {
  node: {
    id: string;
    [key: string]: any;
  };
  labels?: string[];
}

export interface GraphRelationship {
  source: string;
  target: string;
  type: string;
  properties?: Record<string, any>;
}

export interface GraphData {
  nodes: GraphNode[];
  relationships: GraphRelationship[];
  total_nodes: number;
  total_relationships: number;
}

export interface GraphStats {
  nodes: Record<string, number>;
  relationships: Record<string, number>;
  total_nodes: number;
  total_relationships: number;
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

export async function fetchHealth(): Promise<{ database: boolean; llm: boolean; database_error?: string; llm_error?: string }> {
  const response = await fetch(`${API_URL}/api/health`);
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
