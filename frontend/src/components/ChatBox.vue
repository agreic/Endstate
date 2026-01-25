<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { Send, Bot, User, Sparkles, RotateCcw, X } from "lucide-vue-next";
import { marked } from "marked";
import type { ChatStore } from "../composables/useChat";

const renderMarkdown = (content: string) => {
  return marked.parse(content);
};

const props = defineProps<{
  chat: ChatStore;
}>();

const inputMessage = ref("");
const messagesContainer = ref<HTMLElement | null>(null);
const showError = ref(true);

const {
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
} = props.chat;

const isInputDisabled = computed(() => {
  return isSending.value || isChatBlocked.value;
});

const canSend = computed(() => {
  return !isInputDisabled.value && !!inputMessage.value.trim();
});

const formatTime = (date: Date) => {
  if (!date || isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

watch(messages, () => {
  setTimeout(scrollToBottom, 50);
}, { deep: true });

watch(error, () => {
  if (error.value) {
    showError.value = true;
    // Auto-dismiss error after 10 seconds
    setTimeout(() => {
      showError.value = false;
    }, 10000);
  }
}, { deep: true });

const handleSend = async () => {
  if (isInputDisabled.value) return;
  
  const text = inputMessage.value.trim();
  inputMessage.value = "";
  
  await sendMessage(text);
};

const handleSuggestProjects = async () => {
  await requestProjectSuggestions();
};

const dismissError = () => {
  showError.value = false;
};
</script>

<template>
  <div class="flex flex-col h-full bg-surface-50 relative">
    <!-- Project Proposals Overlay - positioned over the entire chat area -->
    <div
      v-if="pendingProposals.length"
      class="absolute inset-0 bg-white/80 backdrop-blur-sm z-20 flex items-center justify-center p-4"
    >
      <div class="w-full max-w-3xl bg-white rounded-2xl border border-surface-200 shadow-xl p-5">
        <div class="flex items-start justify-between gap-4 mb-4">
          <div>
            <p class="text-xs uppercase text-surface-400 font-medium tracking-wide">Suggested Projects</p>
            <p class="text-sm text-surface-700">Pick one to create a project, or reject all to keep chatting.</p>
          </div>
        </div>
        <div class="grid gap-3 md:grid-cols-3">
          <button
            v-for="(proposal, idx) in pendingProposals"
            :key="proposal.title || idx"
            @click="acceptProposal(proposal)"
            class="text-left p-4 rounded-xl border border-surface-200 bg-surface-50 hover:bg-surface-100 hover:border-primary-300 transition-all hover:shadow-md"
          >
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-semibold text-surface-800">{{ proposal.title }}</p>
              <span class="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full border border-surface-200 text-surface-500">
                {{ proposal.difficulty }}
              </span>
            </div>
            <p class="text-xs text-surface-500 mt-2 line-clamp-3">{{ proposal.description }}</p>
            <div v-if="proposal.tags?.length" class="flex flex-wrap gap-1 mt-3">
              <span
                v-for="tag in proposal.tags"
                :key="tag"
                class="text-[10px] px-2 py-0.5 rounded-full bg-surface-100 text-surface-600 border border-surface-200"
              >
                {{ tag }}
              </span>
            </div>
          </button>
        </div>
        <div class="flex justify-end mt-4">
          <button
            @click="rejectProposals"
            class="text-xs px-3 py-1.5 rounded-lg bg-red-50 text-red-600 border border-red-200 hover:bg-red-100 transition-colors"
          >
            Reject All
          </button>
        </div>
      </div>
    </div>

    <div v-if="showError && error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-2 mx-4 mt-4 rounded-lg text-sm flex items-center gap-2 relative z-10">
      <span class="flex-1">{{ error }}</span>
      <button @click="dismissError" class="text-red-400 hover:text-red-600">
        <X :size="16" />
      </button>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-6" ref="messagesContainer">

      <div
        v-for="(message, index) in messages"
        :key="index"
        class="flex gap-3"
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
          </div>
          <p
            class="text-[10px] text-surface-400 mt-1 px-2"
            :class="message.role === 'user' ? 'text-right' : ''"
          >
            {{ formatTime(message.timestamp) }}
          </p>
        </div>
      </div>

      <div v-if="connectionStatus === 'connecting'" class="flex gap-3">
        <div
          class="w-8 h-8 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center flex-shrink-0"
        >
          <Bot :size="16" class="text-white" />
        </div>
        <div
          class="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-surface-100"
        >
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-surface-400 mr-2">Connecting...</span>
          </div>
        </div>
      </div>

      <div v-if="connectionStatus === 'ready' && messages.length === 0" class="text-center text-surface-400 text-sm py-6">
        Start a conversation to see your chat history here.
      </div>

      <div v-if="isLocked" class="flex gap-3">
        <div
          class="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center flex-shrink-0"
        >
          <Bot :size="16" class="text-white" />
        </div>
        <div
          class="bg-amber-50 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-amber-200"
        >
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-amber-600 mr-2">
              {{ processingMode === 'summary' ? 'Creating project plan...' : processingMode === 'proposal' ? 'Generating project suggestions...' : 'Thinking...' }}
            </span>
            <div class="flex gap-1">
              <span class="w-1.5 h-1.5 bg-amber-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
              <span class="w-1.5 h-1.5 bg-amber-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
              <span class="w-1.5 h-1.5 bg-amber-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="p-4 bg-white border-t border-surface-200">
      <div class="max-w-4xl mx-auto">
        <div class="flex items-center gap-2">
          <button
            @click="handleSuggestProjects"
            :disabled="isInputDisabled"
            class="flex-shrink-0 px-3 h-[44px] rounded-lg border transition-colors flex items-center gap-2 bg-surface-50 border-surface-200 text-surface-600 hover:border-surface-300 disabled:opacity-60"
            title="Suggest Projects"
          >
            <Sparkles :size="18" />
            <span class="text-xs font-medium">Suggest Projects</span>
          </button>

          <div class="relative flex-1 h-[44px] overflow-hidden rounded-lg border border-surface-200 focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500">
            <textarea
              v-model="inputMessage"
              @keydown.enter.prevent="handleSend"
              placeholder="Ask anything about your learning goals..."
              rows="1"
              class="w-full h-full px-4 bg-surface-50 text-sm resize-none outline-none"
              :disabled="isInputDisabled"
              style="padding-top: 12px; padding-bottom: 12px;"
            ></textarea>

            <button
              @click="handleSend"
              :disabled="!canSend"
              class="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 rounded-md transition-colors"
              :class="canSend ? 'text-primary-600' : 'text-surface-300'"
            >
              <Send :size="18" />
            </button>
          </div>
        </div>
        <div class="flex items-center justify-between mt-2">
          <p class="text-[10px] text-surface-400">
            {{ isLocked ? (processingMode === 'summary' ? 'Creating project plan... Please wait.' : processingMode === 'proposal' ? 'Generating project suggestions...' : 'Thinking... Please wait.') : (pendingProposals.length ? 'Select a project or reject all to continue chatting.' : 'Chat history stored on backend.') }}
          </p>
          <button
            @click="resetChat"
            :disabled="isSending || isLocked"
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
