<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { X, Moon, Sun, Monitor } from 'lucide-vue-next';

const props = defineProps<{
  isOpen: boolean
}>();

const emit = defineEmits<{
  close: []
}>();

type Theme = 'light' | 'dark' | 'system';

const currentTheme = ref<Theme>('system');
const isDark = ref(false);

const themes: { value: Theme; label: string; icon: any }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
];

const setTheme = (theme: Theme) => {
  currentTheme.value = theme;
  applyTheme(theme);
  localStorage.setItem('endstate-theme', theme);
};

const applyTheme = (theme: Theme) => {
  const root = document.documentElement;
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  if (theme === 'dark' || (theme === 'system' && prefersDark)) {
    isDark.value = true;
    root.classList.add('dark');
  } else {
    isDark.value = false;
    root.classList.remove('dark');
  }
};

const handleBackdropClick = (e: MouseEvent) => {
  if (e.target === e.currentTarget) {
    emit('close');
  }
};

watch(() => props.isOpen, (open) => {
  if (open) {
    const saved = localStorage.getItem('endstate-theme') as Theme | null;
    if (saved) {
      currentTheme.value = saved;
      applyTheme(saved);
    }
  }
});

onMounted(() => {
  const saved = localStorage.getItem('endstate-theme') as Theme | null;
  if (saved) {
    currentTheme.value = saved;
    applyTheme(saved);
  } else {
    applyTheme('system');
  }
});
</script>

<template>
  <Teleport to="body">
    <div 
      v-if="isOpen"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click="handleBackdropClick"
    >
      <div class="bg-white dark:bg-surface-800 rounded-xl shadow-xl w-full max-w-md mx-4 overflow-hidden">
        <div class="flex items-center justify-between p-4 border-b dark:border-surface-700">
          <h2 class="text-lg font-semibold text-surface-900 dark:text-white">Settings</h2>
          <button 
            @click="emit('close')"
            class="p-1.5 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-700 text-surface-500 dark:text-surface-400"
          >
            <X :size="20" />
          </button>
        </div>
        
        <div class="p-4 space-y-6">
          <div>
            <h3 class="text-sm font-medium text-surface-900 dark:text-white mb-3">Appearance</h3>
            <div class="grid grid-cols-3 gap-2">
              <button
                v-for="theme in themes"
                :key="theme.value"
                @click="setTheme(theme.value)"
                class="flex flex-col items-center gap-2 p-3 rounded-lg border-2 transition-all"
                :class="currentTheme === theme.value 
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' 
                  : 'border-surface-200 dark:border-surface-700 hover:border-surface-300 dark:hover:border-surface-600'"
              >
                <component 
                  :is="theme.icon" 
                  :size="24"
                  :class="currentTheme === theme.value ? 'text-primary-600 dark:text-primary-400' : 'text-surface-500 dark:text-surface-400'"
                />
                <span 
                  class="text-xs font-medium"
                  :class="currentTheme === theme.value ? 'text-primary-600 dark:text-primary-400' : 'text-surface-600 dark:text-surface-400'"
                >
                  {{ theme.label }}
                </span>
              </button>
            </div>
          </div>
          
          <div class="pt-4 border-t dark:border-surface-700">
            <p class="text-xs text-surface-500 dark:text-surface-400">
              Theme preference is saved locally and will persist across sessions.
            </p>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
