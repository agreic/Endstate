import { ref, watch } from 'vue';
import type { Message } from '../components/ChatBox.vue';

const MESSAGES_KEY = 'endstate_chat_messages';
const PENDING_KEY = 'endstate_chat_pending';

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

  const addMessage = (message: Message) => {
    messages.value.push(message);
    saveMessages();
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

  const clearAll = () => {
    messages.value = [];
    pendingMessage.value = null;
    localStorage.removeItem(MESSAGES_KEY);
    localStorage.removeItem(PENDING_KEY);
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
