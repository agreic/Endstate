<script setup lang="ts">
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatBox from './components/ChatBox.vue'
import KnowledgeGraph from './components/KnowledgeGraph.vue'
import { MessageSquare, Network, Settings } from 'lucide-vue-next'

const sidebarOpen = ref(true)
const activeTab = ref<'chat' | 'graph'>('chat')

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
}

const setActiveTab = (tab: 'chat' | 'graph') => {
  activeTab.value = tab
}
</script>

<template>
  <div class="flex h-full bg-surface-100">
    <Sidebar 
      :isOpen="sidebarOpen" 
      :activeTab="activeTab"
      @toggle="toggleSidebar"
      @navigate="setActiveTab"
    />
    
    <main 
      class="flex-1 flex flex-col transition-all duration-300"
      :class="sidebarOpen ? 'ml-64' : 'ml-16'"
    >
      <header class="h-14 bg-white border-b border-surface-200 flex items-center justify-between px-4 shadow-sm">
        <div class="flex items-center gap-3">
          <h1 class="text-lg font-semibold text-surface-800">Endstate</h1>
          <span class="text-xs px-2 py-0.5 bg-primary-100 text-primary-700 rounded-full">Demo</span>
        </div>
        
        <div class="flex items-center gap-2">
          <nav class="flex bg-surface-100 rounded-lg p-1">
            <button
              @click="activeTab = 'chat'"
              class="flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all"
              :class="activeTab === 'chat' 
                ? 'bg-white text-primary-600 shadow-sm' 
                : 'text-surface-500 hover:text-surface-700'"
            >
              <MessageSquare :size="16" />
              Chat
            </button>
            <button
              @click="activeTab = 'graph'"
              class="flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all"
              :class="activeTab === 'graph' 
                ? 'bg-white text-primary-600 shadow-sm' 
                : 'text-surface-500 hover:text-surface-700'"
            >
              <Network :size="16" />
              Knowledge Graph
            </button>
          </nav>
        </div>
        
        <div class="flex items-center gap-3">
          <button class="p-2 text-surface-400 hover:text-surface-600 hover:bg-surface-100 rounded-lg transition-colors">
            <Settings :size="18" />
          </button>
          <div class="w-8 h-8 bg-gradient-to-br from-primary-400 to-primary-600 rounded-full"></div>
        </div>
      </header>
      
      <div class="flex-1 overflow-hidden">
        <ChatBox v-if="activeTab === 'chat'" />
        <KnowledgeGraph v-if="activeTab === 'graph'" />
      </div>
    </main>
  </div>
</template>
