import { ref, watch } from 'vue';
import type { Message } from '../components/ChatBox.vue';

const MESSAGES_KEY = 'endstate_chat_messages';
const PENDING_KEY = 'endstate_chat_pending';
const LOADING_KEY = 'endstate_chat_loading';

export function useChatPersistence() {
  const messages = ref<Message[]>([]);
  const pendingMessage = ref<{ text: string; timestamp: number } | null>(null);
  const isLoading = ref(false);

  const loadState = () => {
    try {
      const savedMessages = localStorage.getItem(MESSAGES_KEY);
      if (savedMessages) {
        messages.value = JSON.parse(savedMessages).map((m: any) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        }));
      }

      const savedPending = localStorage.getItem(PENDING_KEY);
      if (savedPending) {
        pendingMessage.value = JSON.parse(savedPending);
      }

      const savedLoading = localStorage.getItem(LOADING_KEY);
      if (savedLoading) {
        isLoading.value = savedLoading === 'true';
      }
    } catch (e) {
      console.error('Failed to load chat state:', e);
    }
  };

  const saveMessages = () => {
    try {
      localStorage.setItem(MESSAGES_KEY, JSON.stringify(messages.value));
    } catch (e) {
      console.error('Failed to save messages:', e);
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

  const saveLoading = (loading: boolean) => {
    try {
      localStorage.setItem(LOADING_KEY, String(loading));
    } catch (e) {
      console.error('Failed to save loading:', e);
    }
  };

  const addMessage = (message: Message) => {
    messages.value.push(message);
    saveMessages();
  };

  const setLoading = (loading: boolean) => {
    isLoading.value = loading;
    saveLoading(loading);
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

  const clearAll = () => {
    messages.value = [];
    pendingMessage.value = null;
    isLoading.value = false;
    localStorage.removeItem(MESSAGES_KEY);
    localStorage.removeItem(PENDING_KEY);
    localStorage.removeItem(LOADING_KEY);
  };

  return {
    messages,
    pendingMessage,
    isLoading,
    loadState,
    addMessage,
    setLoading,
    setPending,
    clearPending,
    clearAll,
  };
}
