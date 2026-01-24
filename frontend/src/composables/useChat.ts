import { ref, computed, onMounted, onUnmounted } from 'vue';
import type { ChatMessage } from '../types/chat';
import type { ProjectProposal } from '../services/api';

const SESSION_ID_KEY = 'endstate_chat_session_id';

function getSessionId(): string {
  let sessionId = localStorage.getItem(SESSION_ID_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem(SESSION_ID_KEY, sessionId);
  }
  return sessionId;
}

export function useChat() {
  const sessionId = ref(getSessionId());
  const connectionStatus = ref<'idle' | 'connecting' | 'ready'>('idle');
  const isSending = ref(false);
  const error = ref<string | null>(null);
  const messages = ref<ChatMessage[]>([]);
  const isLocked = ref(false);
  const processingMode = ref<'chat' | 'summary' | 'proposal' | null>(null);
  const pendingProposals = ref<ProjectProposal[]>([]);
  const isChatBlocked = computed(() => isLocked.value || pendingProposals.value.length > 0);
  const messageKeys = new Set<string>();

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  let eventSource: EventSource | null = null;
  let reconnectAttempts = 0;
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  let proposalPollTimeout: ReturnType<typeof setTimeout> | null = null;

  const FETCH_TIMEOUT = Number(import.meta.env.VITE_CHAT_TIMEOUT_MS) || 120000; // 120 seconds default

  const fetchWithTimeout = async (url: string, options?: RequestInit): Promise<Response> => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
    
    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      return response;
    } catch (e: any) {
      clearTimeout(timeoutId);
      if (e.name === 'AbortError') {
        throw new Error('Request timed out');
      }
      throw e;
    }
  };

  const parseTimestamp = (timestamp?: string | null): Date => {
    if (!timestamp) return new Date();
    const parsed = new Date(timestamp);
    return isNaN(parsed.getTime()) ? new Date() : parsed;
  };

  const messageKey = (message: ChatMessage): string => {
    if (message.requestId) {
      return `req:${message.requestId}`;
    }
    return `msg:${message.role}:${message.content}:${message.timestamp.toISOString()}`;
  };

  const setMessages = (nextMessages: ChatMessage[]) => {
    messageKeys.clear();
    const deduped: ChatMessage[] = [];
    for (const message of nextMessages) {
      const key = messageKey(message);
      if (messageKeys.has(key)) continue;
      messageKeys.add(key);
      deduped.push(message);
    }
    messages.value = deduped;
  };

  const appendMessage = (message: ChatMessage) => {
    const key = messageKey(message);
    if (messageKeys.has(key)) return;
    messageKeys.add(key);
    messages.value.push(message);
  };

  const fetchMessages = async () => {
    try {
      const response = await fetchWithTimeout(`${API_URL}/api/chat/${sessionId.value}/messages`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      isLocked.value = data.is_locked || false;
      pendingProposals.value = Array.isArray(data.proposals) ? data.proposals : [];
      const mapped = (data.messages || []).map((m: any) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
        timestamp: parseTimestamp(m.timestamp),
        requestId: m.request_id ?? null,
      }));
      setMessages(mapped);
    } catch (e: any) {
      console.error('Fetch messages error:', e);
      error.value = e.message || 'Failed to load messages';
    }
  };

  const disconnect = () => {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }
    if (proposalPollTimeout) {
      clearTimeout(proposalPollTimeout);
      proposalPollTimeout = null;
    }
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    reconnectAttempts = 0;
  };

  const pollProposals = () => {
    if (proposalPollTimeout) {
      clearTimeout(proposalPollTimeout);
      proposalPollTimeout = null;
    }
    if (pendingProposals.value.length > 0) return;
    proposalPollTimeout = setTimeout(async () => {
      try {
        const response = await fetchWithTimeout(`${API_URL}/api/chat/${sessionId.value}/proposals`);
        if (response.ok) {
          const data = await response.json();
          pendingProposals.value = Array.isArray(data.proposals) ? data.proposals : [];
          if (pendingProposals.value.length > 0) {
            isLocked.value = false;
            processingMode.value = null;
            return;
          }
        }
      } catch {
        // ignore polling errors
      }
      pollProposals();
    }, 2000);
  };

  const applyInitialMessages = (payload: any) => {
    isLocked.value = payload.locked || false;
    if (isLocked.value && !processingMode.value) {
      processingMode.value = 'chat';
    }
    pendingProposals.value = Array.isArray(payload.proposals) ? payload.proposals : [];
    if (payload.error) {
      error.value = payload.error;
    }
    const mapped = (payload.messages || []).map((m: any) => ({
      role: m.role as 'user' | 'assistant',
      content: m.content,
      timestamp: parseTimestamp(m.timestamp),
      requestId: m.request_id ?? null,
    }));
    setMessages(mapped);
    connectionStatus.value = 'ready';
  };

  const applyMessageAdded = (payload: any) => {
    if (!payload?.content || !payload?.role) return;
    appendMessage({
      role: payload.role as 'user' | 'assistant',
      content: payload.content,
      timestamp: parseTimestamp(payload.timestamp),
      requestId: payload.request_id ?? null,
    });
  };

  const applyLegacyEvent = (payload: any) => {
    if (!payload?.event) return;
    if (payload.event === 'initial_messages') {
      applyInitialMessages(payload);
    } else if (payload.event === 'message_added') {
      applyMessageAdded(payload);
    } else if (payload.event === 'processing_complete') {
      isLocked.value = false;
      processingMode.value = null;
    } else if (payload.event === 'processing_started') {
      isLocked.value = true;
      processingMode.value = payload.reason === 'summary' ? 'summary' : 'chat';
    } else if (payload.event === 'processing_cancelled') {
      isLocked.value = false;
      processingMode.value = null;
    } else if (payload.event === 'proposals_updated') {
      pendingProposals.value = Array.isArray(payload.proposals) ? payload.proposals : [];
      if (proposalPollTimeout) {
        clearTimeout(proposalPollTimeout);
        proposalPollTimeout = null;
      }
    } else if (payload.event === 'proposals_cleared') {
      pendingProposals.value = [];
      if (proposalPollTimeout) {
        clearTimeout(proposalPollTimeout);
        proposalPollTimeout = null;
      }
    } else if (payload.event === 'session_reset') {
      setMessages([]);
      isLocked.value = false;
      processingMode.value = null;
      pendingProposals.value = [];
    } else if (payload.event === 'error') {
      error.value = payload.message || 'An error occurred';
      console.error('[Chat] Server error:', payload.message);
    }
  };

  const connectSSE = () => {
    connectionStatus.value = 'connecting';
    disconnect(); // Clean up any existing connection
    
    // Timeout fallback - if SSE doesn't connect within 5s, use fetch
    const connectionTimeout = setTimeout(() => {
      if (connectionStatus.value === 'connecting') {
        console.log('[Chat] SSE connection timeout, falling back to fetch');
        eventSource?.close();
        eventSource = null;
        fetchMessages().finally(() => {
          if (connectionStatus.value === 'connecting') {
            connectionStatus.value = 'ready';
          }
        });
      }
    }, 5000);
    
    try {
      eventSource = new EventSource(`${API_URL}/api/chat/${sessionId.value}/stream`);
      
      eventSource.onopen = () => {
        console.log('[Chat] SSE connected');
        clearTimeout(connectionTimeout);
        reconnectAttempts = 0; // Reset reconnect counter on successful connection
      };
      
      eventSource.addEventListener('initial_messages', (event) => {
        clearTimeout(connectionTimeout);
        try {
          const data = JSON.parse((event as MessageEvent).data);
          applyInitialMessages(data);
          if (data.error) {
            reconnectAttempts = 5; // Stop reconnecting on server error
          }
        } catch (e) {
          console.error('[Chat] SSE parse error:', e);
        }
      });

      eventSource.addEventListener('message_added', (event) => {
        clearTimeout(connectionTimeout);
        try {
          const data = JSON.parse((event as MessageEvent).data);
          applyMessageAdded(data);
        } catch (e) {
          console.error('[Chat] SSE parse error:', e);
        }
      });

      eventSource.addEventListener('proposals_updated', (event) => {
        clearTimeout(connectionTimeout);
        try {
          const data = JSON.parse((event as MessageEvent).data);
          pendingProposals.value = Array.isArray(data.proposals) ? data.proposals : [];
          if (proposalPollTimeout) {
            clearTimeout(proposalPollTimeout);
            proposalPollTimeout = null;
          }
        } catch (e) {
          console.error('[Chat] SSE parse error:', e);
        }
      });

      eventSource.addEventListener('proposals_cleared', () => {
        pendingProposals.value = [];
        if (proposalPollTimeout) {
          clearTimeout(proposalPollTimeout);
          proposalPollTimeout = null;
        }
      });

      eventSource.addEventListener('processing_complete', () => {
        isLocked.value = false;
        processingMode.value = null;
      });

      eventSource.addEventListener('processing_started', (event) => {
        isLocked.value = true;
        try {
          const data = JSON.parse((event as MessageEvent).data);
          processingMode.value = data.reason === 'summary'
            ? 'summary'
            : data.reason === 'proposal'
              ? 'proposal'
              : 'chat';
        } catch (e) {
          processingMode.value = 'chat';
          console.error('[Chat] SSE parse error:', e);
        }
      });

      eventSource.addEventListener('processing_cancelled', () => {
        isLocked.value = false;
        processingMode.value = null;
      });

      eventSource.addEventListener('session_reset', () => {
        setMessages([]);
        isLocked.value = false;
        processingMode.value = null;
      });

      eventSource.addEventListener('error', (event) => {
        clearTimeout(connectionTimeout);
        try {
          const data = JSON.parse((event as MessageEvent).data);
          error.value = data.message || 'An error occurred';
        } catch (e) {
          error.value = 'An error occurred';
          console.error('[Chat] SSE parse error:', e);
        }
      });

      eventSource.onmessage = (event) => {
        clearTimeout(connectionTimeout);
        try {
          const data = JSON.parse(event.data);
          applyLegacyEvent(data);
        } catch (e) {
          console.error('[Chat] SSE parse error:', e);
        }
      };
      
      eventSource.onerror = () => {
        clearTimeout(connectionTimeout);
        console.log('[Chat] SSE connection error');
        eventSource?.close();
        eventSource = null;
        
        reconnectAttempts++;
        
        if (reconnectAttempts >= 5) {
          console.log('[Chat] Max reconnect attempts reached');
          connectionStatus.value = 'ready';
          error.value = 'Connection lost. Please refresh the page.';
          return;
        }
        
        const delay = Math.pow(2, reconnectAttempts - 1) * 1000;
        console.log(`[Chat] Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/5)`);
        connectionStatus.value = 'connecting';
        reconnectTimeout = setTimeout(connectSSE, delay);
      };
    } catch (e) {
      clearTimeout(connectionTimeout);
      console.error('[Chat] Failed to create SSE connection:', e);
      connectionStatus.value = 'ready';
      fetchMessages();
    }
  };

  const sendMessage = async (content: string) => {
    if (isSending.value) return;
    if (pendingProposals.value.length > 0) {
      error.value = 'Choose a project or reject all before continuing the chat.';
      return;
    }
    if (isLocked.value) {
      error.value = 'Chat is processing. Please wait.';
      return;
    }
    
    isSending.value = true;
    error.value = null;
    
    try {
      const requestId = crypto.randomUUID();
      const response = await fetchWithTimeout(`${API_URL}/api/chat/${sessionId.value}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': requestId,
        },
        body: JSON.stringify({ message: content }),
      });
      
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }
      
      // SSE will deliver the new message automatically
      // If SSE is not connected, fallback to fetch
      if (!eventSource || eventSource.readyState !== EventSource.OPEN) {
        await fetchMessages();
      }
    } catch (e: any) {
      console.error('Send error:', e);
      error.value = e.message || 'Failed to send message';
    } finally {
      isSending.value = false;
    }
  };

  const resetChat = async () => {
    if (isSending.value) return;
    
    try {
      await fetchWithTimeout(`${API_URL}/api/chat/${sessionId.value}/reset`, { method: 'POST' });
      setMessages([]);
      isLocked.value = false;
      pendingProposals.value = [];
      error.value = null;
    } catch (e: any) {
      error.value = e.message || 'Failed to reset chat';
    }
  };

  const requestProjectSuggestions = async (count: number = 3) => {
    if (isLocked.value || pendingProposals.value.length > 0) return;
    error.value = null;
    isLocked.value = true;
    processingMode.value = 'proposal';
    try {
      const response = await fetchWithTimeout(`${API_URL}/api/suggest-projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId.value,
          history: messages.value.map((message) => ({
            role: message.role,
            content: message.content,
          })),
          count,
        }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }
      const data = await response.json();
      if (Array.isArray(data.projects)) {
        pendingProposals.value = data.projects;
        isLocked.value = false;
        processingMode.value = null;
      } else if (data.status === 'queued') {
        pollProposals();
      } else if (data.status === 'busy') {
        throw new Error('Suggest projects is already running. Please wait.');
      }
    } catch (e: any) {
      error.value = e.message || 'Failed to suggest projects';
      isLocked.value = false;
      processingMode.value = null;
    }
  };

  const acceptProposal = async (proposal: ProjectProposal) => {
    error.value = null;
    try {
      const response = await fetchWithTimeout(`${API_URL}/api/suggest-projects/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId.value,
          option: proposal,
        }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }
      pendingProposals.value = [];
      if (proposalPollTimeout) {
        clearTimeout(proposalPollTimeout);
        proposalPollTimeout = null;
      }
    } catch (e: any) {
      error.value = e.message || 'Failed to accept proposal';
    }
  };

  const rejectProposals = async () => {
    error.value = null;
    try {
      const response = await fetchWithTimeout(`${API_URL}/api/chat/${sessionId.value}/proposals/reject`, {
        method: 'POST',
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }
      pendingProposals.value = [];
      if (proposalPollTimeout) {
        clearTimeout(proposalPollTimeout);
        proposalPollTimeout = null;
      }
    } catch (e: any) {
      error.value = e.message || 'Failed to reject proposals';
    }
  };

  onMounted(() => {
    connectSSE();
  });

  onUnmounted(() => {
    disconnect();
  });

  return {
    sessionId,
    messages,
    connectionStatus,
    isSending,
    isLocked,
    isChatBlocked,
    pendingProposals,
    processingMode,
    error,
    sendMessage,
    resetChat,
    requestProjectSuggestions,
    acceptProposal,
    rejectProposals,
    loadMessages: fetchMessages,
  };
}

export type ChatStore = ReturnType<typeof useChat>;
