<script setup lang="ts">
import { ref, nextTick, onMounted, onUpdated } from "vue";
import { Send, Bot, User, Globe, ExternalLink, RotateCcw } from "lucide-vue-next";
import { marked } from "marked";
import { sendChatMessage as apiSendChatMessage, resetChatSession, checkSessionLocked } from "../services/api";
import { useChatPersistence } from "../composables/useChatPersistence";

interface Source {
  title: string;
  url: string;
}

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: Source[];
}

const SESSION_ID_KEY = 'endstate_chat_session_id';

const getSessionId = (): string => {
  let sessionId = localStorage.getItem(SESSION_ID_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem(SESSION_ID_KEY, sessionId);
  }
  return sessionId;
};

const renderMarkdown = (content: string) => {
  return marked.parse(content);
};

const sessionId = ref(getSessionId());
const inputMessage = ref("");
const isSearchEnabled = ref(false);
const messagesContainer = ref<HTMLElement | null>(null);
const isResetting = ref(false);
const abortController = ref<AbortController | null>(null);
const isProcessing = ref(false);

const { 
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
} = useChatPersistence();

const scrollToBottom = async () => {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

const formatTime = (date: Date) => {
  if (!date || isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

const cancelPendingRequest = () => {
  if (abortController.value) {
    abortController.value.abort();
    abortController.value = null;
  }
};

const resetConversation = async () => {
  if (isResetting.value || isLoading.value) {
    cancelPendingRequest();
  }
  
  if (!confirm("Reset the conversation? This will clear all messages.")) return;
  
  isResetting.value = true;
  cancelPendingRequest();
  setLoading(false);
  clearPending();
  
  try {
    await resetChatSession(sessionId.value);
    clearMessages();
  } catch (e) {
    console.error('Failed to reset chat:', e);
    alert('Failed to reset. Make sure the backend is running.');
  } finally {
    isResetting.value = false;
  }
};

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value || isProcessing.value) return;

  const userText = inputMessage.value.trim();

  addMessage({
    id: Date.now(),
    role: "user",
    content: userText,
    timestamp: new Date(),
  });

  inputMessage.value = "";
  setPending(userText);
  await scrollToBottom();

  cancelPendingRequest();
  abortController.value = new AbortController();
  setLoading(true);
  
  try {
    const response = await apiSendChatMessage(userText, isSearchEnabled.value, sessionId.value, abortController.value.signal);

    if (response.is_processing) {
      isProcessing.value = true;
      addMessage({
        id: Date.now(),
        role: "assistant",
        content: response.content,
        timestamp: new Date(),
      });
      pollForProcessingComplete();
    } else {
      addMessage({
        id: Date.now(),
        role: "assistant",
        content: response.content,
        timestamp: new Date(),
        sources: response.sources as Source[],
      });
    }
  } catch (error: any) {
    setLoading(false);
    if (error.name === 'AbortError') {
      console.log('Request was cancelled');
      return;
    }
    console.error(error);
    addMessage({
      id: Date.now(),
      role: "assistant",
      content: "I'm having trouble connecting to the server right now. Please try again later.",
      timestamp: new Date(),
    });
  } finally {
    if (!isProcessing.value) {
      setLoading(false);
      abortController.value = null;
      clearPending();
    }
    await scrollToBottom();
  }
};

const pollForProcessingComplete = async () => {
  const pollInterval = 2000;
  let attempts = 0;
  const maxAttempts = 30;

  while (isProcessing.value && attempts < maxAttempts) {
    await new Promise(resolve => setTimeout(resolve, pollInterval));
    attempts++;

    try {
      const result = await checkSessionLocked(sessionId.value);
      if (!result.locked) {
        isProcessing.value = false;
        setLoading(false);
        abortController.value = null;
        clearPending();
        await loadState(sessionId.value);
        await scrollToBottom();
        break;
      }
    } catch (e) {
      console.error('Error polling for processing status:', e);
    }
  }

  if (isProcessing.value && attempts >= maxAttempts) {
    isProcessing.value = false;
    setLoading(false);
    abortController.value = null;
    clearPending();
  }
};

const checkPendingResponse = async () => {
  if (pendingMessage.value && !isLoading.value) {
    cancelPendingRequest();
    abortController.value = new AbortController();
    setLoading(true);
    
    try {
      const response = await apiSendChatMessage(pendingMessage.value.text, isSearchEnabled.value, sessionId.value, abortController.value.signal);
      addMessage({
        id: Date.now(),
        role: "assistant",
        content: response.content,
        timestamp: new Date(),
        sources: response.sources as Source[],
      });
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('Request was cancelled');
        return;
      }
      console.error(error);
      addMessage({
        id: Date.now(),
        role: "assistant",
        content: "I'm having trouble connecting to the server right now. Please try again later.",
        timestamp: new Date(),
      });
    } finally {
      abortController.value = null;
      clearPending();
      await scrollToBottom();
    }
  }
};

onMounted(async () => {
  await loadState(sessionId.value);
  checkPendingResponse();
});

onUpdated(() => {
  scrollToBottom();
});
</script>

<template>
  <div class="flex flex-col h-full bg-surface-50">
    <div class="flex-1 overflow-y-auto p-4 space-y-6" ref="messagesContainer">
      <div v-if="hasError" class="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
        <p class="text-amber-700 text-sm">Unable to connect to backend. Make sure the server is running.</p>
      </div>

      <div
        v-for="message in messages"
        :key="message.id"
        class="flex gap-3 animate-fade-in"
        :class="message.role === 'user' ? 'flex-row-reverse' : ''"
      >
        <div
          class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm"
          :class="
            message.role === 'user'
              ? 'bg-primary-600'
              : 'bg-gradient-to-br from-primary-400 to-primary-600'
          "
        >
          <User v-if="message.role === 'user'" :size="16" class="text-white" />
          <Bot v-else :size="16" class="text-white" />
        </div>

        <div class="max-w-[85%] lg:max-w-[70%]">
          <div
            class="rounded-2xl px-4 py-3 shadow-sm"
            :class="
              message.role === 'user'
                ? 'bg-primary-600 text-white'
                : 'bg-white text-surface-800'
            "
          >
            <div
              class="text-sm leading-relaxed markdown-container"
              v-html="renderMarkdown(message.content)"
            ></div>

            <div
              v-if="message.sources && message.sources.length > 0"
              class="mt-3 pt-3 border-t border-surface-100"
            >
              <p
                class="text-[10px] uppercase tracking-wider font-bold text-surface-400 mb-2 flex items-center gap-1"
              >
                <Globe :size="10" /> Sources Found
              </p>
              <div class="flex flex-wrap gap-2">
                <a
                  v-for="source in message.sources"
                  :key="source.url"
                  :href="source.url"
                  target="_blank"
                  class="flex items-center gap-1.5 px-2 py-1 bg-surface-50 hover:bg-surface-100 border border-surface-200 rounded-md text-[11px] text-primary-700 transition-colors"
                >
                  <span class="truncate max-w-[120px]">{{ source.title }}</span>
                  <ExternalLink :size="10" />
                </a>
              </div>
            </div>
          </div>
          <p
            class="text-[10px] text-surface-400 mt-1 px-2"
            :class="message.role === 'user' ? 'text-right' : ''"
          >
            {{ formatTime(message.timestamp) }}
          </p>
        </div>
      </div>

      <div v-if="isLoading" class="flex gap-3 animate-fade-in">
        <div
          class="w-8 h-8 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center flex-shrink-0"
        >
          <Bot :size="16" class="text-white" />
        </div>
        <div
          class="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-surface-100"
        >
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-surface-400 mr-2">{{
              isSearchEnabled ? "Searching web..." : "Thinking..."
            }}</span>
            <div class="flex gap-1">
              <span
                class="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce"
                style="animation-delay: 0ms"
              ></span>
              <span
                class="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce"
                style="animation-delay: 150ms"
              ></span>
              <span
                class="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce"
                style="animation-delay: 300ms"
              ></span>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="isProcessing" class="flex gap-3 animate-fade-in">
        <div
          class="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center flex-shrink-0"
        >
          <Bot :size="16" class="text-white" />
        </div>
        <div
          class="bg-amber-50 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-amber-200"
        >
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-amber-600 mr-2">Creating project plan...</span>
            <div class="flex gap-1">
              <span
                class="w-1.5 h-1.5 bg-amber-400 rounded-full animate-bounce"
                style="animation-delay: 0ms"
              ></span>
              <span
                class="w-1.5 h-1.5 bg-amber-400 rounded-full animate-bounce"
                style="animation-delay: 150ms"
              ></span>
              <span
                class="w-1.5 h-1.5 bg-amber-400 rounded-full animate-bounce"
                style="animation-delay: 300ms"
              ></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="p-4 bg-white border-t border-surface-200">
      <div class="max-w-4xl mx-auto">
        <div class="flex items-stretch gap-2">
          <button
            @click="isSearchEnabled = !isSearchEnabled"
            class="flex-shrink-0 p-2.5 rounded-lg border transition-colors flex items-center justify-center"
            :class="
              isSearchEnabled
                ? 'bg-primary-50 border-primary-200 text-primary-600'
                : 'bg-surface-50 border-surface-200 text-surface-400 hover:border-surface-300'
            "
            title="Toggle web search"
          >
            <Globe :size="18" />
          </button>

            <div class="relative flex-1">
            <textarea
              v-model="inputMessage"
              @keydown.enter.prevent="sendMessage"
              placeholder="Ask anything about your learning goals..."
              rows="1"
              class="w-full h-full min-h-[44px] px-4 py-2.5 pr-10 bg-surface-50 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-sm resize-none leading-normal disabled:opacity-50"
              :disabled="isProcessing"
            ></textarea>

            <button
              @click="sendMessage"
              :disabled="!inputMessage.trim() || isLoading || isProcessing"
              class="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 rounded-md transition-colors text-surface-300 hover:text-primary-600 disabled:cursor-not-allowed"
              :class="{ 'text-primary-600': inputMessage.trim() && !isLoading && !isProcessing }"
            >
              <Send :size="18" />
            </button>
          </div>
        </div>
        <div class="flex items-center justify-between mt-2">
          <p class="text-[10px] text-surface-400">
            {{ isProcessing ? 'Creating project plan... Please wait.' : 'Chat history stored on backend. Agree to a project to create a summary.' }}
          </p>
          <button
            @click="resetConversation"
            :disabled="isResetting || isLoading || isProcessing"
            class="flex items-center gap-1 text-xs text-surface-400 hover:text-red-500 transition-colors disabled:opacity-50"
          >
            <RotateCcw :size="12" />
            Reset
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
