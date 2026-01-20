import { ref, reactive, onMounted, onUnmounted } from 'vue';
import type { Message } from '../components/ChatBox.vue';
import { getChatHistory, sendChatMessage, resetChatSession } from '../services/api';

const SESSION_ID_KEY = 'endstate_chat_session_id';
const REQUEST_ID_KEY = 'endstate_last_request_id';

function getSessionId(): string {
  let sessionId = localStorage.getItem(SESSION_ID_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem(SESSION_ID_KEY, sessionId);
  }
  return sessionId;
}

export type ChatStatus = 'idle' | 'loading' | 'processing' | 'error';

interface ChatState {
  status: ChatStatus;
  messages: Message[];
  error: string | null;
  isLocked: boolean;
}

export function useChat() {
  const sessionId = ref(getSessionId());
  const state = reactive<ChatState>({
    status: 'idle',
    messages: [],
    error: null,
    isLocked: false,
  });
  
  let eventSource: EventSource | null = null;
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  
  const getLastRequestId = (): string | null => {
    return localStorage.getItem(REQUEST_ID_KEY);
  };
  
  const setLastRequestId = (id: string): void => {
    localStorage.setItem(REQUEST_ID_KEY, id);
  };
  
  const connectEventStream = (): void => {
    if (eventSource) {
      eventSource.close();
    }
    
    eventSource = new EventSource(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/chat/${sessionId.value}/stream`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.event) {
          case 'initial_messages':
            state.messages = (data.messages || []).map((msg: any, index: number) => ({
              id: index,
              role: msg.role as 'user' | 'assistant',
              content: msg.content,
              timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
            }));
            state.isLocked = data.locked || false;
            if (state.isLocked) {
              state.status = 'processing';
            } else if (state.status === 'processing') {
              state.status = 'idle';
            }
            break;
            
          case 'message_added':
            const newMessage: Message = {
              id: state.messages.length,
              role: data.role as 'user' | 'assistant',
              content: data.content,
              timestamp: new Date(),
            };
            state.messages.push(newMessage);
            break;
            
          case 'processing_started':
            state.status = 'processing';
            state.isLocked = true;
            break;
            
          case 'processing_complete':
          case 'processing_cancelled':
            state.status = 'idle';
            state.isLocked = false;
            break;
        }
      } catch (e) {
        console.error('Error parsing SSE message:', e);
      }
    };
    
    eventSource.onerror = () => {
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
      
      reconnectTimeout = setTimeout(() => {
        connectEventStream();
      }, 3000);
    };
  };
  
  const loadMessages = async (): Promise<void> => {
    try {
      const response = await getChatHistory(sessionId.value);
      state.messages = (response.messages || []).map((msg: any, index: number) => ({
        id: index,
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
      }));
      state.isLocked = response.is_locked || false;
      if (state.isLocked) {
        state.status = 'processing';
      } else {
        state.status = 'idle';
      }
      state.error = null;
    } catch (e) {
      console.error('Failed to load messages:', e);
      state.error = 'Failed to connect to server';
      state.status = 'error';
    }
  };
  
  const sendMessage = async (content: string): Promise<void> => {
    if (state.status !== 'idle') return;
    
    state.status = 'loading';
    state.error = null;
    
    const requestId = crypto.randomUUID();
    setLastRequestId(requestId);
    
    try {
      const response = await sendChatMessage(content, false, sessionId.value, requestId);
      
      if (response.already_processed) {
        await loadMessages();
        return;
      }
      
      if (response.is_processing) {
        state.status = 'processing';
        state.isLocked = true;
      } else {
        state.status = 'idle';
        await loadMessages();
      }
    } catch (e: any) {
      console.error('Failed to send message:', e);
      state.status = 'error';
      state.error = e.message || 'Failed to send message';
    }
  };
  
  const resetChat = async (): Promise<void> => {
    if (state.status === 'loading') return;
    
    try {
      await resetChatSession(sessionId.value);
      state.messages = [{
        id: 0,
        role: 'assistant',
        content: "Hello! I'm Endstate AI. What would you like to learn today?",
        timestamp: new Date(),
      }];
      state.status = 'idle';
      state.error = null;
      state.isLocked = false;
    } catch (e) {
      console.error('Failed to reset chat:', e);
      state.error = 'Failed to reset chat';
    }
  };
  
  onMounted(() => {
    loadMessages();
    connectEventStream();
  });
  
  onUnmounted(() => {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }
  });
  
  return {
    sessionId,
    state,
    sendMessage,
    resetChat,
    loadMessages,
  };
}
