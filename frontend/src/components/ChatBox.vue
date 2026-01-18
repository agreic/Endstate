<script setup lang="ts">
import { ref, nextTick, onMounted } from "vue";
import { Send, Bot, User, Globe, ExternalLink } from "lucide-vue-next"; // Added Globe and ExternalLink
import { GoogleGenerativeAI } from "@google/generative-ai";
import { marked } from "marked";

const API_KEY = import.meta.env.VITE_GEMINI_API_KEY;
const genAI = new GoogleGenerativeAI(API_KEY);
const emit = defineEmits<{
  (e: "updateGraph", data: any): void;
}>();
// State for Web Search Toggle
const isSearchEnabled = ref(false);

const renderMarkdown = (content: string) => {
  return marked.parse(content);
};

const systemPrompt = `
You are Endstate AI, the Agentic Learning Architect.
Your goal is to transform vague learning wishes into executable skill graphs.

RULES:
1. When a user asks for a "skill graph" or a "learning path", you MUST provide a JSON block.
2. This JSON block MUST be wrapped in <graph_update> tags.
3. After the tags, tell the user: "I've architected your learning path! Head over to the Knowledge Graph tab to see your new roadmap."

JSON FORMAT:
<graph_update>
{
  "newNodes": [
    {"id": "unique_id", "group": 1, "label": "Skill Name", "description": "Short summary"}
  ],
  "newLinks": [
    {"source": "prerequisite_id", "target": "skill_id", "value": 3}
  ]
}
</graph_update>
`;

// Initialize Model WITH Google Search Tool
const model = genAI.getGenerativeModel({
  model: "gemini-2.5-flash", // 2.0/2.5 Flash supports grounding best
  systemInstruction: systemPrompt,
  tools: [
    {
      //@ts-ignore - Some TS definitions might not have googleSearch yet
      googleSearch: {},
    },
  ],
});

interface Source {
  title: string;
  url: string;
}

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: Source[]; // Store sources here
}

const messages = ref<Message[]>([
  {
    id: 1,
    role: "assistant",
    content: "Hello! I'm Endstate AI. What would you like to learn today?",
    timestamp: new Date(),
  },
]);

const inputMessage = ref("");
const isLoading = ref(false);
const messagesContainer = ref<HTMLElement | null>(null);

// History management
const chat = model.startChat({
  history: [],
});

const scrollToBottom = async () => {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return;

  const userText = inputMessage.value.trim();

  messages.value.push({
    id: Date.now(),
    role: "user",
    content: userText,
    timestamp: new Date(),
  });

  inputMessage.value = "";
  isLoading.value = true;
  await scrollToBottom();

  try {
    // If search is disabled, we could technically use a different model instance,
    // but Gemini is smart enough to only search if the prompt requires it.
    const result = await chat.sendMessage(userText);
    const response = await result.response;
    const rawText = response.text();

    // --- NEW: EXTRACT GRAPH DATA ---

    const graphMatch = rawText.match(
      /<graph_update>([\s\S]*?)<\/graph_update>/,
    );
    let cleanContent = rawText;

    // Inside sendMessage function
    if (graphMatch) {
      try {
        const graphData = JSON.parse(graphMatch[1]);
        emit("updateGraph", graphData); // Sends data to App.vue

        // This cleans the chat bubble so it only shows the "Head over to the tab" text
        cleanContent = rawText.replace(
          /<graph_update>[\s\S]*?<\/graph_update>/,
          "",
        );
      } catch (e) {
        console.error("Graph parsing failed", e);
      }
    }
    // --- END NEW SECTION ---
    // Extract Grounding Metadata (Sources)
    const metadata = response.candidates?.[0]?.groundingMetadata;
    const sources: Source[] = [];

    if (metadata?.searchEntryPoint?.sdkBlob) {
      // This is where the visual Google Search chips come from if using the widget
    }

    if (metadata?.groundingChunks) {
      metadata.groundingChunks.forEach((chunk: any) => {
        if (chunk.web) {
          sources.push({
            title: chunk.web.title,
            url: chunk.web.uri,
          });
        }
      });
    }

    // Remove duplicates
    const uniqueSources = sources
      .filter((v, i, a) => a.findIndex((t) => t.url === v.url) === i)
      .slice(0, 3);

    messages.value.push({
      id: Date.now(),
      role: "assistant",
      content: cleanContent,
      timestamp: new Date(),
      sources: uniqueSources,
    });
  } catch (error) {
    console.error(error);
    messages.value.push({
      id: Date.now(),
      role: "assistant",
      content: "I'm having trouble connecting to the web right now.",
      timestamp: new Date(),
    });
  } finally {
    isLoading.value = false;
    await scrollToBottom();
  }
};

const formatTime = (date: Date) => {
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

onMounted(() => scrollToBottom());
</script>

<template>
  <div class="flex flex-col h-full bg-surface-50">
    <div class="flex-1 overflow-y-auto p-4 space-y-6" ref="messagesContainer">
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
    </div>

    <div class="p-4 bg-white border-t border-surface-200">
      <div class="max-w-4xl mx-auto">
        <div class="flex gap-3 items-end">
          <button
            @click="isSearchEnabled = !isSearchEnabled"
            class="p-3 rounded-xl border transition-all flex items-center justify-center gap-2 group"
            :class="
              isSearchEnabled
                ? 'bg-primary-50 border-primary-200 text-primary-600 ring-2 ring-primary-500/10'
                : 'bg-surface-50 border-surface-200 text-surface-400 hover:border-surface-300'
            "
          >
            <Globe :size="20" :class="isSearchEnabled ? 'animate-pulse' : ''" />
            <span v-if="isSearchEnabled" class="text-xs font-bold pr-1"
              >Search On</span
            >
          </button>

          <div class="flex-1 relative">
            <textarea
              v-model="inputMessage"
              @keydown.enter.prevent="sendMessage"
              placeholder="Ask anything or use web search..."
              rows="1"
              class="w-full px-4 py-3 pr-12 bg-surface-50 border border-surface-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all text-sm resize-none"
            ></textarea>

            <button
              @click="sendMessage"
              :disabled="!inputMessage.trim() || isLoading"
              class="absolute right-2 bottom-2 p-2 rounded-lg transition-all"
              :class="
                inputMessage.trim() && !isLoading
                  ? 'bg-primary-600 text-white shadow-md hover:bg-primary-700'
                  : 'bg-surface-200 text-surface-400 cursor-not-allowed'
              "
            >
              <Send :size="18" />
            </button>
          </div>
        </div>
        <p class="text-center text-[10px] text-surface-400 mt-2">
          Endstate AI can browse the web to provide real-time information.
        </p>
      </div>
    </div>
  </div>
</template>
