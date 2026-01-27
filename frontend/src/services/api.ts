const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS) || 30000;
const LLM_TIMEOUT_MS = Number(import.meta.env.VITE_LLM_TIMEOUT_MS) || 120000; // 2 minutes for LLM operations

function getHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const getValue = (key: string): string | null => {
    const val = localStorage.getItem(key);
    if (!val) return null;
    const trimmed = val.trim();
    // Ignore empty strings or literal "null"/"undefined" strings
    if (trimmed === '' || trimmed === 'null' || trimmed === 'undefined') return null;
    return trimmed;
  };

  const geminiKey = getValue('endstate_gemini_api_key');
  const openrouterKey = getValue('endstate_openrouter_api_key') || geminiKey;
  const neo4jUri = getValue('endstate_neo4j_uri');
  const neo4jUser = getValue('endstate_neo4j_user');
  const neo4jPass = getValue('endstate_neo4j_password');
  const llmProvider = getValue('endstate_llm_provider');

  if (llmProvider) headers['X-LLM-Provider'] = llmProvider;
  if (openrouterKey) headers['X-OpenRouter-API-Key'] = openrouterKey;
  if (geminiKey) headers['X-Gemini-API-Key'] = geminiKey;
  if (neo4jUri) headers['X-Neo4j-URI'] = neo4jUri;
  if (neo4jUser) headers['X-Neo4j-User'] = neo4jUser;
  if (neo4jPass) headers['X-Neo4j-Password'] = neo4jPass;

  return headers;
}

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        ...getHeaders(),
        ...options?.headers,
      },
      signal: controller.signal,
    });

    const contentType = response.headers.get('content-type') || '';
    const hasJson = contentType.includes('application/json');

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      if (hasJson) {
        const errorBody = await response.json().catch(() => null);
        detail = errorBody?.detail || errorBody?.message || detail;
      } else {
        const text = await response.text().catch(() => '');
        if (text) detail = text;
      }
      throw new Error(detail);
    }

    if (!hasJson) {
      return {} as T;
    }

    return response.json();
  } catch (e: any) {
    if (e?.name === 'AbortError') {
      throw new Error('Request timed out');
    }
    throw e;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function requestJsonAllowNotFound<T>(path: string, notFoundValue: T, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        ...getHeaders(),
        ...options?.headers,
      },
      signal: controller.signal,
    });

    if (response.status === 404) {
      return notFoundValue;
    }

    const contentType = response.headers.get('content-type') || '';
    const hasJson = contentType.includes('application/json');

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      if (hasJson) {
        const errorBody = await response.json().catch(() => null);
        detail = errorBody?.detail || errorBody?.message || detail;
      } else {
        const text = await response.text().catch(() => '');
        if (text) detail = text;
      }
      throw new Error(detail);
    }

    if (!hasJson) {
      return notFoundValue;
    }

    return response.json();
  } catch (e: any) {
    if (e?.name === 'AbortError') {
      throw new Error('Request timed out');
    }
    throw e;
  } finally {
    clearTimeout(timeoutId);
  }
}

export interface ApiNode {
  id: string;
  labels: string[];
  properties: Record<string, any>;
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
  filtered_project_id?: string | null;
}

export interface GraphStats {
  nodes: Record<string, number>;
  relationships: Record<string, number>;
  total_nodes: number;
  total_relationships: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
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
  messages: ChatMessage[];
}

export interface ProjectProposal {
  id: string;
  title: string;
  description: string;
  difficulty: string;
  tags: string[];
}

export interface ProjectSummary {
  session_id: string;
  created_at: string;
  updated_at: string;
  project_status?: string;
  started_at?: string;
  capstone?: {
    status?: string;
    last_score?: number;
    passed?: boolean;
    completed_at?: string;
    attempts?: number;
    last_submission_id?: string;
  };
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

export interface ProjectLesson {
  id: string;
  node_id: string;
  title: string;
  explanation: string;
  task: string;
  created_at?: string;
  archived?: boolean;
  archived_at?: string;
}

export interface ProjectAssessment {
  id: string;
  lesson_id: string;
  prompt: string;
  status?: string;
  feedback?: string;
  created_at?: string;
  updated_at?: string;
  archived?: boolean;
  archived_at?: string;
}

export interface ProjectSubmission {
  id: string;
  project_id: string;
  content: string;
  attempt_number: number;
  status: string;
  score?: number;
  passed?: boolean;
  feedback?: string;
  submitted_at?: string;
  evaluated_at?: string;
}

export interface SubmissionEvaluation {
  id: string;
  score: number;
  rubric?: Record<string, any>;
  skill_evidence?: Record<string, string>;
  overall_feedback?: string;
  suggestions?: string[];
  passed?: boolean;
  model_used?: string;
  evaluated_at?: string;
}

export interface ProjectListItem {
  id: string;
  name: string;
  created_at: string;
  interests: string[];
  capstone_passed?: boolean;
}

export interface GraphProjectsResponse {
  projects: Array<{ id: string; name: string; created_at: string; is_default: boolean }>;
  most_recent_project_id: string | null;
}

export async function fetchGraphData(projectId?: string): Promise<GraphData> {
  const params = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
  return requestJson<GraphData>(`/api/graph${params}`);
}

export async function fetchGraphProjects(): Promise<GraphProjectsResponse> {
  return requestJson<GraphProjectsResponse>('/api/graph/projects');
}

export async function fetchGraphStats(): Promise<GraphStats> {
  return requestJson<GraphStats>('/api/graph/stats');
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  return requestJson<DashboardStats>('/api/stats/dashboard');
}

export async function fetchHealth(): Promise<{ database: boolean; llm: boolean; database_error?: string; llm_error?: string }> {
  return requestJson('/api/health');
}

export async function deleteNode(nodeId: string): Promise<{ deleted_node_id: string; relationships_deleted: number }> {
  return requestJson(`/api/graph/nodes/${encodeURIComponent(nodeId)}`, {
    method: 'DELETE',
  });
}

export async function deleteRelationship(sourceId: string, targetId: string, relType: string): Promise<{ deleted: boolean }> {
  const params = new URLSearchParams({
    source_id: sourceId,
    target_id: targetId,
    rel_type: relType,
  });
  return requestJson(`/api/graph/relationships?${params}`, {
    method: 'DELETE',
  });
}

export async function getNodeConnections(nodeId: string): Promise<{ node_id: string; connections: Array<{ id: string; labels: string[]; rel_type: string }> }> {
  return requestJson(`/api/graph/node/${encodeURIComponent(nodeId)}/connections`);
}

export async function getChatHistory(sessionId: string): Promise<{ messages: Array<{ role: string; content: string; timestamp: string }>; is_locked?: boolean }> {
  return requestJson(`/api/chat/${sessionId}/messages`);
}

export async function checkSessionLocked(sessionId: string): Promise<{ locked: boolean }> {
  return requestJson(`/api/chat/${sessionId}/locked`);
}

export async function deleteChatSession(sessionId: string): Promise<{ message: string }> {
  return requestJson(`/api/chat/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  });
}

export async function resetChatSession(sessionId: string): Promise<{ message: string }> {
  return requestJson(`/api/chat/${encodeURIComponent(sessionId)}/reset`, {
    method: 'POST',
  });
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

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
  if (signal) {
    if (signal.aborted) {
      controller.abort();
    } else {
      signal.addEventListener('abort', () => controller.abort(), { once: true });
    }
  }

  try {
    const response = await fetch(endpoint, {
      ...init,
      headers: {
        ...getHeaders(),
        ...init.headers,
      },
      signal: controller.signal,
    });
    if (!response.ok) {
      const errorBody = await response.json().catch(() => null);
      const detail = errorBody?.detail || errorBody?.message || `HTTP ${response.status}`;
      throw new Error(detail);
    }
    return response.json();
  } catch (e: any) {
    if (e?.name === 'AbortError') {
      throw new Error('Request timed out');
    }
    throw e;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function getChatProposals(sessionId: string): Promise<{ proposals: ProjectProposal[] }> {
  return requestJson(`/api/chat/${encodeURIComponent(sessionId)}/proposals`);
}

export async function suggestChatProjects(sessionId: string, count: number = 3): Promise<{ status: string; proposals?: ProjectProposal[] }> {
  return requestJson(`/api/chat/${encodeURIComponent(sessionId)}/proposals`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ count }),
  });
}

export async function suggestProjects(payload: { sessionId: string; history: { role: string; content: string }[]; count?: number }): Promise<{ projects: ProjectProposal[] }> {
  return requestJson(`/api/suggest-projects`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: payload.sessionId,
      history: payload.history,
      count: payload.count ?? 3,
    }),
  });
}

export async function acceptSuggestedProject(payload: { sessionId: string; option: ProjectProposal }): Promise<{ project_id: string; project_name: string }> {
  return requestJson(`/api/suggest-projects/accept`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: payload.sessionId,
      option: payload.option,
    }),
  });
}

export async function acceptChatProposal(sessionId: string, proposalId: string): Promise<{ project_id: string; project_name: string }> {
  return requestJson(`/api/chat/${encodeURIComponent(sessionId)}/proposals/${encodeURIComponent(proposalId)}/accept`, {
    method: 'POST',
  });
}

export async function rejectChatProposals(sessionId: string): Promise<{ status: string }> {
  return requestJson(`/api/chat/${encodeURIComponent(sessionId)}/proposals/reject`, {
    method: 'POST',
  });
}

export async function extractFromText(text: string): Promise<{ message: string; documents_count: number }> {
  return requestJson('/api/extract/sample', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  });
}

export async function cleanGraph(label?: string): Promise<{ message: string }> {
  const params = label ? `?label=${encodeURIComponent(label)}` : '';
  return requestJson(`/api/clean${params}`, {
    method: 'POST',
  });
}

export async function mergeDuplicates(label: string, matchProperty: string = 'id'): Promise<{ message: string; merged_count: number }> {
  return requestJson(`/api/merge?label=${encodeURIComponent(label)}&match_property=${encodeURIComponent(matchProperty)}`, {
    method: 'POST',
  });
}

export async function listProjects(limit: number = 50): Promise<{ projects: ProjectListItem[] }> {
  const params = new URLSearchParams({ limit: String(limit) });
  return requestJson(`/api/projects?${params}`);
}

export async function getProject(projectId: string): Promise<ProjectSummary> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}`);
}

export async function deleteProject(projectId: string): Promise<{ message: string }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}`, {
    method: 'DELETE',
  });
}

export async function renameProject(projectId: string, name: string): Promise<{ id: string; name: string; updated_at?: string }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/name`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name }),
  });
}

export async function startProject(projectId: string): Promise<{ status?: string; job_id?: string; message?: string; project_id?: string; user_profile?: ProjectSummary['user_profile']; nodes_added?: number; relationships_added?: number; project_status?: string; started_at?: string }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/start`, {
    method: 'POST',
  });
}

export async function generateNodeLesson(nodeId: string, projectId?: string): Promise<{ node_id: string; lesson_id?: string; explanation: string; task: string }> {
  return requestJson(`/api/graph/nodes/${encodeURIComponent(nodeId)}/lesson`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ project_id: projectId }),
  });
}

export async function listProjectLessons(projectId: string): Promise<{ lessons: ProjectLesson[] }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/lessons`);
}

export async function queueProjectLesson(projectId: string, nodeId: string): Promise<{ status: string; job_id?: string; lesson?: ProjectLesson }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/lessons/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ node_id: nodeId }),
  });
}

export async function generateNodeLessons(nodeId: string): Promise<{ status: string; jobs: Array<{ project_id: string; job_id: string }>; skipped: Array<{ project_id: string; lesson_id: string; created_at?: string }> }> {
  return requestJson(`/api/graph/nodes/${encodeURIComponent(nodeId)}/lessons/generate`, {
    method: 'POST',
  });
}

export async function listProjectAssessments(projectId: string): Promise<{ assessments: ProjectAssessment[] }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/assessments`);
}

export async function updateProjectProfile(
  projectId: string,
  profile: Partial<ProjectSummary['user_profile']>,
): Promise<{ project_id: string; user_profile: ProjectSummary['user_profile'] }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/profile`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(profile),
  });
}

export async function createProjectAssessment(projectId: string, lessonId: string): Promise<{ status: string; job_id?: string }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/assessments`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ lesson_id: lessonId }),
  });
}

export async function submitProjectAssessment(
  projectId: string,
  assessmentId: string,
  answer: string,
): Promise<{ status: string; job_id: string }> {
  // Assessment evaluation is now an async job
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_URL}/api/projects/${encodeURIComponent(projectId)}/assessments/${encodeURIComponent(assessmentId)}/submit`, {
      method: 'POST',
      headers: {
        ...getHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ answer }),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => null);
      const detail = errorBody?.detail || errorBody?.message || `HTTP ${response.status}`;
      throw new Error(detail);
    }

    return response.json();
  } catch (e: any) {
    if (e?.name === 'AbortError') {
      throw new Error('Assessment evaluation timed out. Please try again.');
    }
    throw e;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function archiveProjectLesson(projectId: string, lessonId: string): Promise<{ lesson_id: string; archived: boolean }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/lessons/${encodeURIComponent(lessonId)}/archive`, {
    method: 'POST',
  });
}

export async function deleteProjectLesson(projectId: string, lessonId: string): Promise<{ lesson_id: string; deleted: boolean }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/lessons/${encodeURIComponent(lessonId)}`, {
    method: 'DELETE',
  });
}

export async function archiveProjectAssessment(projectId: string, assessmentId: string): Promise<{ assessment_id: string; archived: boolean }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/assessments/${encodeURIComponent(assessmentId)}/archive`, {
    method: 'POST',
  });
}

export async function deleteProjectAssessment(projectId: string, assessmentId: string): Promise<{ assessment_id: string; deleted: boolean }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/assessments/${encodeURIComponent(assessmentId)}`, {
    method: 'DELETE',
  });
}

export async function getJobStatus(jobId: string): Promise<{ job_id: string; project_id: string; kind: string; status: string; result?: any; error?: string }> {
  return requestJson(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export async function cancelJob(jobId: string): Promise<{ job_id: string; status: string }> {
  return requestJson(`/api/jobs/${encodeURIComponent(jobId)}`, {
    method: 'DELETE',
  });
}

export async function listProjectJobs(
  projectId: string,
  options: { kind?: string; nodeId?: string } = {},
): Promise<{ jobs: Array<{ job_id: string; project_id: string; kind: string; status: string; meta?: any; created_at?: string; updated_at?: string }> }> {
  const params = new URLSearchParams();
  if (options.kind) params.set('kind', options.kind);
  if (options.nodeId) params.set('node_id', options.nodeId);
  const query = params.toString();
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/jobs${query ? `?${query}` : ''}`);
}

export async function getProjectChat(projectId: string): Promise<{ messages: ChatMessage[] }> {
  return requestJsonAllowNotFound(`/api/projects/${encodeURIComponent(projectId)}/chat`, { messages: [] });
}

export async function listProjectNodes(projectId: string): Promise<{ nodes: ApiNode[] }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/nodes`);
}

export async function submitCapstone(projectId: string, content: string): Promise<{ status: string; job_id: string; submission_id: string; attempt: number }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
}

export async function listProjectSubmissions(projectId: string): Promise<{ submissions: ProjectSubmission[] }> {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/submissions`);
}

export async function getSubmission(submissionId: string): Promise<{ submission: ProjectSubmission; evaluations: SubmissionEvaluation[] }> {
  return requestJson(`/api/submissions/${encodeURIComponent(submissionId)}`);
}

export interface RemediationResult {
  status?: string;
  job_id?: string;
  action?: string;
  diagnosis?: {
    diagnosis: string;
    missing_concepts: string[];
    severity: string;
    recommended_action?: string;
  };
  remediation_node_id?: string;
  remediation_content?: {
    title: string;
    description: string;
    explanation: string;
  };
  error?: string;
}

export async function triggerRemediation(
  projectId: string,
  assessmentId: string,
): Promise<{ status: string; job_id: string }> {
  // Use longer timeout for LLM-based remediation
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), LLM_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_URL}/api/projects/${encodeURIComponent(projectId)}/assessments/${encodeURIComponent(assessmentId)}/remediate`, {
      method: 'POST',
      headers: getHeaders(),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => null);
      const detail = errorBody?.detail || errorBody?.message || `HTTP ${response.status}`;
      throw new Error(detail);
    }

    return response.json();
  } catch (e: any) {
    if (e?.name === 'AbortError') {
      throw new Error('Remediation generation timed out. Please try again.');
    }
    throw e;
  } finally {
    clearTimeout(timeoutId);
  }
}
