<script setup lang="ts">
import { ref } from 'vue'
import { 
  Home, 
  MessageSquare, 
  Network, 
  FolderOpen,
  Settings, 
  ChevronLeft,
  ChevronRight,
  HelpCircle
} from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  activeTab: 'dashboard' | 'chat' | 'graph' | 'projects'
}>()

const emit = defineEmits<{
  toggle: []
  navigate: [tab: 'dashboard' | 'chat' | 'graph' | 'projects']
  openSettings: []
  openHelp: []
}>()

const menuItems = [
  { icon: Home, label: 'Dashboard', tab: 'dashboard' as const },
  { icon: MessageSquare, label: 'Chat', tab: 'chat' as const },
  { icon: Network, label: 'Knowledge Graph', tab: 'graph' as const },
  { icon: FolderOpen, label: 'Projects', tab: 'projects' as const },
]

const handleNavigate = (tab: string | null) => {
  if (tab) {
    emit('navigate', tab as 'dashboard' | 'chat' | 'graph' | 'projects')
  }
}
</script>

<template>
  <aside 
    class="fixed left-0 top-0 h-full bg-surface-900 text-white transition-all duration-300 z-50"
    :class="isOpen ? 'w-64' : 'w-16'"
  >
    <div class="flex flex-col h-full">
      <div class="h-14 flex items-center justify-between px-3 border-b border-surface-700">
        <div class="flex items-center gap-3" v-if="isOpen">
          <div class="w-8 h-8 bg-gradient-to-br from-primary-400 to-primary-600 rounded-lg flex items-center justify-center">
            <span class="text-sm font-bold">E</span>
          </div>
          <span class="font-semibold">Endstate</span>
        </div>
        <button 
          @click="emit('toggle')"
          class="p-1.5 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors ml-auto"
        >
          <ChevronLeft v-if="isOpen" :size="18" />
          <ChevronRight v-else :size="18" />
        </button>
      </div>

      <nav class="flex-1 py-4 overflow-y-auto">
        <div class="px-3 mb-2" v-if="isOpen">
          <span class="text-xs text-surface-500 uppercase tracking-wider font-medium">Main</span>
        </div>
        <ul class="space-y-1 px-2">
          <li v-for="item in menuItems" :key="item.label">
            <button 
              @click="handleNavigate(item.tab)"
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all"
              :class="item.tab && activeTab === item.tab 
                ? 'bg-primary-600 text-white' 
                : 'text-surface-300 hover:bg-surface-800 hover:text-white'"
            >
              <component :is="item.icon" :size="20" />
              <span v-if="isOpen" class="text-sm font-medium">{{ item.label }}</span>
            </button>
          </li>
        </ul>

        <div class="mt-8 px-3 mb-2" v-if="isOpen">
          <span class="text-xs text-surface-500 uppercase tracking-wider font-medium">Support</span>
        </div>
        <ul class="space-y-1 px-2">
          <li>
            <button 
              @click="emit('openSettings')"
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-surface-300 hover:bg-surface-800 hover:text-white"
            >
              <Settings :size="20" />
              <span v-if="isOpen" class="text-sm font-medium">Settings</span>
            </button>
          </li>
          <li>
            <button 
              @click="emit('openHelp')"
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-surface-300 hover:bg-surface-800 hover:text-white"
            >
              <HelpCircle :size="20" />
              <span v-if="isOpen" class="text-sm font-medium">Help</span>
            </button>
          </li>
        </ul>
      </nav>

      <div v-if="isOpen" class="p-4 border-t border-surface-700">
        <button 
          @click="emit('openHelp')"
          class="w-full bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-700 hover:to-primary-600 rounded-lg p-3 transition-all"
        >
          <p class="text-sm font-medium text-white">Getting Started</p>
          <p class="text-xs text-primary-100 mt-0.5">Learn how to use Endstate</p>
        </button>
      </div>
    </div>
  </aside>
</template>
