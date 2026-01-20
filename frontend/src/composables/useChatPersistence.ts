import { ref } from 'vue';
import type { Message } from '../components/ChatBox.vue';
import { getChatHistory } from '../services/api';

const PENDING_KEY = 'endstate_chat_pending';

export function useChatPersistence() {
  const messages = ref<Message[]>([]);
  const pendingMessage = ref<{ text: string; timestamp: number } | null>(null);
  const isLoading = ref(false);
  const hasError = ref(false);

  const loadState = async (sessionId: string) => {
    try {
      hasError.value = false;
      const response = await getChatHistory(sessionId);
      if (response.messages && response.messages.length > 0) {
        messages.value = response.messages.map((msg: any, index: number) => {
          let timestamp = new Date();
          if (msg.timestamp) {
            const parsed = new Date(msg.timestamp);
            if (!isNaN(parsed.getTime())) {
              timestamp = parsed;
            }
          }
          return {
            id: index,
            role: msg.role as "user" | "assistant",
            content: msg.content,
            timestamp,
          };
        });
      } else {
        messages.value = [
          {
            id: 0,
            role: "assistant",
            content: "Hello! I'm Endstate AI. What would you like to learn today?",
            timestamp: new Date(),
          },
        ];
      }
    } catch (e) {
      console.error('Failed to load chat history:', e);
      hasError.value = true;
      messages.value = [
        {
          id: 0,
          role: "assistant",
          content: "Unable to connect to server. Make sure the backend is running.",
          timestamp: new Date(),
        },
      ];
    }

    try {
      const savedPending = localStorage.getItem(PENDING_KEY);
      if (savedPending) {
        pendingMessage.value = JSON.parse(savedPending);
      }
    } catch (e) {
      console.error('Failed to load pending:', e);
    }
  };

  const savePending = (text: string | null) => {
    try {
      if (text) {
        localStorage.setItem(PENDING_KEY, JSON.stringify({ text, timestamp: Date.now() }));
      } else {
        localStorage.removeItem(PENDING_KEY);
      }
    } catch (e) {
      console.error('Failed to save pending:', e);
    }
  };

  const addMessage = (message: Message) => {
    messages.value.push(message);
  };

  const setLoading = (loading: boolean) => {
    isLoading.value = loading;
  };

  const setPending = (text: string | null) => {
    if (text) {
      pendingMessage.value = { text, timestamp: Date.now() };
    } else {
      pendingMessage.value = null;
    }
    savePending(text);
  };

  const clearPending = () => {
    pendingMessage.value = null;
    savePending(null);
  };

  const clearMessages = () => {
    messages.value = [
      {
        id: 0,
        role: "assistant",
        content: "Hello! I'm Endstate AI. What would you like to learn today?",
        timestamp: new Date(),
      },
    ];
  };

  const resetState = () => {
    messages.value = [];
    pendingMessage.value = null;
    isLoading.value = false;
    hasError.value = false;
    localStorage.removeItem(PENDING_KEY);
  };

  return {
    messages,
    pendingMessage,
    isLoading,
    hasError,
    loadState,
    addMessage,
    setLoading,
    setPending,
    clearPending,
    clearMessages,
    resetState,
  };
}
