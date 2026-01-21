import { ref, onMounted, onUnmounted } from 'vue';
import type { Message } from '../components/ChatBox.vue';

const SESSION_ID_KEY = 'endstate_chat_session_id';
const GREETING = "Hello! I'm Endstate AI. What would you like to learn today?";

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
  const status = ref<'idle' | 'connecting' | 'ready' | 'sending'>('idle');
  const error = ref<string | null>(null);
  const messages = ref<Message[]>([]);
  const isLocked = ref(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  let eventSource: EventSource | null = null;
  let reconnectAttempts = 0;
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

  const FETCH_TIMEOUT = 10000; // 10 seconds

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

  const fetchMessages = async () => {
    try {
      const response = await fetchWithTimeout(`${API_URL}/api/chat/${sessionId.value}/messages`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      isLocked.value = data.is_locked || false;
      
      if (data.messages.length === 0) {
        messages.value = [{
          role: 'assistant',
          content: GREETING,
          timestamp: new Date(),
        }];
      } else {
        messages.value = data.messages.map((m: any) => ({
          role: m.role as 'user' | 'assistant',
          content: m.content,
          timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
        }));
      }
    } catch (e: any) {
      console.error('Fetch messages error:', e);
      error.value = e.message || 'Failed to load messages';
      // If already showing messages, don't replace them with greeting on error
      if (messages.value.length === 0) {
        messages.value = [{
          role: 'assistant',
          content: GREETING,
          timestamp: new Date(),
        }];
      }
    }
  };

  const disconnect = () => {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    reconnectAttempts = 0;
  };

  const connectSSE = () => {
    status.value = 'connecting';
    disconnect(); // Clean up any existing connection
    
    try {
      eventSource = new EventSource(`${API_URL}/api/chat/${sessionId.value}/stream`);
      
      eventSource.onopen = () => {
        console.log('[Chat] SSE connected');
        reconnectAttempts = 0; // Reset reconnect counter on successful connection
      };
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.event === 'initial_messages') {
            isLocked.value = data.locked || false;
            
            if (data.messages.length === 0) {
              messages.value = [{
                role: 'assistant',
                content: GREETING,
                timestamp: new Date(),
              }];
            } else {
              messages.value = data.messages.map((m: any) => ({
                role: m.role as 'user' | 'assistant',
                content: m.content,
                timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
              }));
            }
            status.value = 'ready';
          } else if (data.event === 'message_added') {
            messages.value.push({
              role: data.role as 'user' | 'assistant',
              content: data.content,
              timestamp: new Date(),
            });
          } else if (data.event === 'processing_complete') {
            isLocked.value = false;
          } else if (data.event === 'processing_started') {
            isLocked.value = true;
          } else if (data.event === 'error') {
            error.value = data.message || 'An error occurred';
            console.error('[Chat] Server error:', data.message);
            // Don't reconnect on server error - just show error and let user refresh
            eventSource?.close();
            eventSource = null;
            reconnectAttempts = 5; // Prevent further reconnect attempts
          } else if (data.event === 'heartbeat') {
            // Silent heartbeat - just keep connection alive
          }
        } catch (e) {
          console.error('[Chat] SSE parse error:', e);
        }
      };
      
      eventSource.onerror = () => {
        console.log('[Chat] SSE connection error');
        eventSource?.close();
        eventSource = null;
        
        reconnectAttempts++;
        
        if (reconnectAttempts >= 5) {
          console.log('[Chat] Max reconnect attempts reached');
          status.value = 'ready';
          error.value = 'Connection lost. Please refresh the page.';
          return;
        }
        
        // Exponential backoff: 1s, 2s, 4s, 8s
        const delay = Math.pow(2, reconnectAttempts - 1) * 1000;
        console.log(`[Chat] Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/5)`);
        status.value = 'connecting';
        reconnectTimeout = setTimeout(connectSSE, delay);
      };
    } catch (e) {
      console.error('[Chat] Failed to create SSE connection:', e);
      status.value = 'ready';
      fetchMessages();
    }
  };

  const sendMessage = async (content: string) => {
    if (status.value === 'sending') return;
    if (isLocked.value) {
      error.value = 'Chat is processing. Please wait.';
      return;
    }
    
    status.value = 'sending';
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
      status.value = 'ready';
    }
  };

  const resetChat = async () => {
    if (status.value === 'sending') return;
    
    try {
      await fetchWithTimeout(`${API_URL}/api/chat/${sessionId.value}/reset`, { method: 'POST' });
      messages.value = [{
        role: 'assistant',
        content: GREETING,
        timestamp: new Date(),
      }];
      isLocked.value = false;
      error.value = null;
    } catch (e: any) {
      error.value = e.message || 'Failed to reset chat';
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
    status,
    isLocked,
    error,
    sendMessage,
    resetChat,
    loadMessages: fetchMessages,
  };
}
