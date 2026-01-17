<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { Send, Bot, User, Sparkles } from 'lucide-vue-next'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const messages = ref<Message[]>([
  {
    id: 1,
    role: 'assistant',
    content: "Hello! I'm your AI assistant. I can help you explore knowledge graphs, answer questions, and assist with your data. What would you like to know?",
    timestamp: new Date()
  }
])

const inputMessage = ref('')
const isLoading = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMessage: Message = {
    id: Date.now(),
    role: 'user',
    content: inputMessage.value.trim(),
    timestamp: new Date()
  }
  messages.value.push(userMessage)
  inputMessage.value = ''
  await scrollToBottom()

  isLoading.value = true

  await new Promise(resolve => setTimeout(resolve, 1500))

  const responses = [
    "That's an interesting question! Based on the knowledge graph, I can see several relevant connections...",
    "I understand what you're asking. Let me analyze the data for you...",
    "Great question! Here's what I found in the knowledge base...",
    "I can help you with that. The knowledge graph shows these relationships..."
  ]

  const assistantMessage: Message = {
    id: Date.now(),
    role: 'assistant',
    content: responses[Math.floor(Math.random() * responses.length)],
    timestamp: new Date()
  }
  messages.value.push(assistantMessage)
  isLoading.value = false
  await scrollToBottom()
}

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  scrollToBottom()
})
</script>

<template>
  <div class="flex flex-col h-full bg-surface-50">
    <div class="flex-1 overflow-y-auto p-4 space-y-4" ref="messagesContainer">
      <div 
        v-for="message in messages" 
        :key="message.id"
        class="flex gap-3 animate-fade-in"
        :class="message.role === 'user' ? 'flex-row-reverse' : ''"
      >
        <div 
          class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
          :class="message.role === 'user' 
            ? 'bg-primary-600' 
            : 'bg-gradient-to-br from-primary-400 to-primary-600'"
        >
          <User v-if="message.role === 'user'" :size="16" class="text-white" />
          <Bot v-else :size="16" class="text-white" />
        </div>
        
        <div 
          class="max-w-[70%] rounded-2xl px-4 py-3 shadow-sm"
          :class="message.role === 'user' 
            ? 'bg-primary-600 text-white rounded-tr-sm' 
            : 'bg-white text-surface-800 rounded-tl-sm'"
        >
          <p class="text-sm leading-relaxed">{{ message.content }}</p>
          <p 
            class="text-xs mt-1"
            :class="message.role === 'user' ? 'text-primary-200' : 'text-surface-400'"
          >
            {{ formatTime(message.timestamp) }}
          </p>
        </div>
      </div>

      <div v-if="isLoading" class="flex gap-3 animate-fade-in">
        <div class="w-8 h-8 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center flex-shrink-0">
          <Bot :size="16" class="text-white" />
        </div>
        <div class="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
          <div class="flex items-center gap-1">
            <span class="w-2 h-2 bg-surface-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
            <span class="w-2 h-2 bg-surface-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
            <span class="w-2 h-2 bg-surface-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
          </div>
        </div>
      </div>
    </div>

    <div class="p-4 bg-white border-t border-surface-200">
      <div class="flex gap-3">
        <div class="flex-1 relative">
          <input
            v-model="inputMessage"
            @keyup.enter="sendMessage"
            type="text"
            placeholder="Type your message..."
            class="w-full px-4 py-3 pr-12 bg-surface-100 border border-surface-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all text-sm"
          />
          <button 
            @click="sendMessage"
            :disabled="!inputMessage.trim() || isLoading"
            class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg transition-colors"
            :class="inputMessage.trim() && !isLoading
              ? 'bg-primary-600 text-white hover:bg-primary-700'
              : 'bg-surface-200 text-surface-400 cursor-not-allowed'"
          >
            <Send :size="18" />
          </button>
        </div>
        <button class="p-3 bg-gradient-to-br from-primary-500 to-primary-600 text-white rounded-xl hover:from-primary-600 hover:to-primary-700 transition-all shadow-lg shadow-primary-500/25">
          <Sparkles :size="20" />
        </button>
      </div>
      <p class="text-center text-xs text-surface-400 mt-2">
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  </div>
</template>
