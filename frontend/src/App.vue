<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import Dashboard from './components/Dashboard.vue'
import ChatBox from './components/ChatBox.vue'
import KnowledgeGraph from './components/KnowledgeGraph.vue'
import Projects from './components/Projects.vue'
import SettingsModal from './components/SettingsModal.vue'
import HelpModal from './components/HelpModal.vue'
import { MessageSquare, Network, FolderOpen, Settings, HelpCircle } from 'lucide-vue-next'

const sidebarOpen = ref(true)
const activeTab = ref<'dashboard' | 'chat' | 'graph' | 'projects'>('dashboard')
const showSettings = ref(false)
const showHelp = ref(false)

// Apply saved theme on mount
onMounted(() => {
  const saved = localStorage.getItem('endstate-theme') as 'light' | 'dark' | 'system' | null
  if (saved) {
    applyTheme(saved)
  } else {
    applyTheme('system')
  }
})

const applyTheme = (theme: 'light' | 'dark' | 'system') => {
  const root = document.documentElement
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  
  if (theme === 'dark' || (theme === 'system' && prefersDark)) {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
}

const setActiveTab = (tab: 'dashboard' | 'chat' | 'graph' | 'projects') => {
  activeTab.value = tab
}

const handleHelpClose = () => {
  showHelp.value = false
  // Mark as seen so it doesn't show again automatically
  localStorage.setItem('endstate-has-seen-help', 'true')
}
</script>

<template>
  <div class="flex h-full bg-surface-100 dark:bg-surface-900">
    <Sidebar 
      :isOpen="sidebarOpen" 
      :activeTab="activeTab"
      @toggle="toggleSidebar"
      @navigate="setActiveTab"
      @openSettings="showSettings = true"
      @openHelp="showHelp = true"
    />
    
    <main 
      class="flex-1 flex flex-col transition-all duration-300"
      :class="sidebarOpen ? 'ml-64' : 'ml-16'"
    >
      <header class="h-14 bg-white dark:bg-surface-800 border-b border-surface-200 dark:border-surface-700 flex items-center justify-between px-4 shadow-sm">
        <div class="flex items-center gap-3">
          <h1 class="text-lg font-semibold text-surface-800 dark:text-white">Endstate</h1>
        </div>
        
        <div class="flex items-center gap-2">
          <nav class="flex bg-surface-100 dark:bg-surface-700 rounded-lg p-1">
            <button
              @click="activeTab = 'dashboard'"
              class="flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all"
              :class="activeTab === 'dashboard' 
                ? 'bg-white dark:bg-surface-600 text-primary-600 dark:text-primary-400 shadow-sm' 
                : 'text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200'"
            >
              Dashboard
            </button>
            <button
              @click="activeTab = 'chat'"
              class="flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all"
              :class="activeTab === 'chat' 
                ? 'bg-white dark:bg-surface-600 text-primary-600 dark:text-primary-400 shadow-sm' 
                : 'text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200'"
            >
              <MessageSquare :size="16" />
              Chat
            </button>
            <button
              @click="activeTab = 'graph'"
              class="flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all"
              :class="activeTab === 'graph' 
                ? 'bg-white dark:bg-surface-600 text-primary-600 dark:text-primary-400 shadow-sm' 
                : 'text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200'"
            >
              <Network :size="16" />
              Knowledge Graph
            </button>
            <button
              @click="activeTab = 'projects'"
              class="flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all"
              :class="activeTab === 'projects' 
                ? 'bg-white dark:bg-surface-600 text-primary-600 dark:text-primary-400 shadow-sm' 
                : 'text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200'"
            >
              <FolderOpen :size="16" />
              Projects
            </button>
          </nav>
        </div>
        
        <div class="flex items-center gap-3">
          <button 
            @click="showHelp = true"
            class="p-2 text-surface-400 hover:text-surface-600 dark:hover:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-700 rounded-lg transition-colors"
            title="Help"
          >
            <HelpCircle :size="18" />
          </button>
          <button 
            @click="showSettings = true"
            class="p-2 text-surface-400 hover:text-surface-600 dark:hover:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-700 rounded-lg transition-colors"
            title="Settings"
          >
            <Settings :size="18" />
          </button>
          <div class="w-8 h-8 bg-gradient-to-br from-primary-400 to-primary-600 rounded-full"></div>
        </div>
      </header>
      
      <div class="flex-1 overflow-hidden">
        <Dashboard v-if="activeTab === 'dashboard'" @navigate="setActiveTab" />
        <ChatBox v-if="activeTab === 'chat'" />
        <KnowledgeGraph v-if="activeTab === 'graph'" />
        <Projects v-if="activeTab === 'projects'" />
      </div>
    </main>

    <SettingsModal :isOpen="showSettings" @close="showSettings = false" />
    <HelpModal :isOpen="showHelp" @close="showHelp = false" />
  </div>
</template>
