import { ref, reactive, onMounted } from 'vue';
import type { Message } from '../components/ChatBox.vue';

const SESSION_ID_KEY = 'endstate_chat_session_id';

function getSessionId(): string {
  let sessionId = localStorage.getItem(SESSION_ID_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem(SESSION_ID_KEY, sessionId);
    console.log('[Chat] Created new session ID:', sessionId);
  } else {
    console.log('[Chat] Using existing session ID:', sessionId);
  }
  return sessionId;
}

export function useChat() {
  const sessionId = ref(getSessionId());
  const isLoading = ref(false);
  const isProcessing = ref(false);
  const error = ref<string | null>(null);
  const messages = ref<Message[]>([]);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const loadMessages = async () => {
    console.log('[Chat] Loading messages for session:', sessionId.value);
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await fetch(`${API_URL}/api/chat/${sessionId.value}/messages`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      console.log('[Chat] Got response:', data);
      const msgs = data.messages || [];
      
      if (msgs.length === 0) {
        // Show greeting
        messages.value = [{
          id: 0,
          role: 'assistant',
          content: "Hello! I'm Endstate AI. What would you like to learn today?",
          timestamp: new Date(),
        }];
      } else {
        messages.value = msgs.map((m: any, i: number) => ({
          id: i,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
        }));
      }
      
      isProcessing.value = data.is_locked || false;
    } catch (e: any) {
      console.error('Load error:', e);
      error.value = e.message;
      // Still show greeting on error
      messages.value = [{
        id: 0,
        role: 'assistant',
        content: "Hello! I'm Endstate AI. What would you like to learn today?",
        timestamp: new Date(),
      }];
    } finally {
      isLoading.value = false;
    }
  };

  const sendMessage = async (content: string) => {
    if (isLoading.value || isProcessing.value) return;
    
    isLoading.value = true;
    error.value = null;
    
    // Optimistically add user message
    messages.value.push({
      id: messages.value.length,
      role: 'user',
      content,
      timestamp: new Date(),
    });
    
    try {
      const requestId = crypto.randomUUID();
      const response = await fetch(`${API_URL}/api/chat/${sessionId.value}/messages`, {
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
      
      const data = await response.json();
      
      if (data.is_processing) {
        isProcessing.value = true;
      } else {
        // Reload messages from backend
        await loadMessages();
      }
    } catch (e: any) {
      console.error('Send error:', e);
      error.value = e.message;
    } finally {
      isLoading.value = false;
    }
  };

  const resetChat = async () => {
    if (isLoading.value) return;
    
    try {
      await fetch(`${API_URL}/api/chat/${sessionId.value}/reset`, { method: 'POST' });
      messages.value = [{
        id: 0,
        role: 'assistant',
        content: "Hello! I'm Endstate AI. What would you like to learn today?",
        timestamp: new Date(),
      }];
      isProcessing.value = false;
      error.value = null;
    } catch (e: any) {
      error.value = e.message;
    }
  };

  onMounted(() => {
    loadMessages();
  });

  return {
    sessionId,
    messages,
    isLoading,
    isProcessing,
    error,
    sendMessage,
    resetChat,
    loadMessages,
  };
}
