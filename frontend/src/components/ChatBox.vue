<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import { Send, Bot, User, Globe, RotateCcw } from "lucide-vue-next";
import { marked } from "marked";
import { useChat } from "../composables/useChat";

const renderMarkdown = (content: string) => {
  return marked.parse(content);
};

const inputMessage = ref("");
const isSearchEnabled = ref(false);
const messagesContainer = ref<HTMLElement | null>(null);

const { messages, isLoading, isProcessing, error, sendMessage, resetChat } = useChat();

const isInputDisabled = computed(() => {
  return isLoading.value || isProcessing.value || !inputMessage.value.trim();
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
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

watch(messages, () => {
  scrollToBottom();
}, { deep: true });

const handleSend = async () => {
  if (isInputDisabled.value) return;
  
  const text = inputMessage.value.trim();
  inputMessage.value = "";
  
  await sendMessage(text);
};
</script>

<template>
  <div class="flex flex-col h-full bg-surface-50">
    <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-2 mx-4 mt-4 rounded-lg text-sm">
      {{ error }}
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-6" ref="messagesContainer">
      <div
        v-for="message in messages"
        :key="message.id"
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

      <div v-if="isLoading" class="flex gap-3">
        <div
          class="w-8 h-8 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center flex-shrink-0"
        >
          <Bot :size="16" class="text-white" />
        </div>
        <div
          class="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-surface-100"
        >
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-surface-400 mr-2">Thinking...</span>
            <div class="flex gap-1">
              <span class="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
              <span class="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
              <span class="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="isProcessing" class="flex gap-3">
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
        <div class="flex items-stretch gap-2">
          <button
            @click="isSearchEnabled = !isSearchEnabled"
            class="flex-shrink-0 p-2.5 rounded-lg border transition-colors flex items-center justify-center"
            :class="
              isSearchEnabled
                ? 'bg-primary-50 border-primary-200 text-primary-600'
                : 'bg-surface-50 border-surface-200 text-surface-400 hover:border-surface-300'
            "
          >
            <Globe :size="18" />
          </button>

          <div class="relative flex-1">
            <textarea
              v-model="inputMessage"
              @keydown.enter.prevent="handleSend"
              placeholder="Ask anything about your learning goals..."
              rows="1"
              class="w-full h-full min-h-[44px] px-4 py-2.5 pr-10 bg-surface-50 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-sm resize-none leading-normal"
              :disabled="isInputDisabled"
            ></textarea>

            <button
              @click="handleSend"
              :disabled="isInputDisabled"
              class="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 rounded-md transition-colors"
              :class="inputMessage.trim() && !isLoading && !isProcessing ? 'text-primary-600' : 'text-surface-300'"
            >
              <Send :size="18" />
            </button>
          </div>
        </div>
        <div class="flex items-center justify-between mt-2">
          <p class="text-[10px] text-surface-400">
            {{ isProcessing ? 'Creating project plan... Please wait.' : 'Chat history stored on backend.' }}
          </p>
          <button
            @click="resetChat"
            :disabled="isLoading || isProcessing"
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
