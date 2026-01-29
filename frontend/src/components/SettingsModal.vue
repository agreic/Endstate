<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue';
import { X, Moon, Sun, Monitor } from 'lucide-vue-next';

const props = defineProps<{
  isOpen: boolean
}>();

const emit = defineEmits<{
  close: []
}>();

type Theme = 'light' | 'dark' | 'system';
type LLMProvider = '' | 'gemini' | 'openrouter';

const currentTheme = ref<Theme>('system');
const isDark = ref(false);

const themes: { value: Theme; label: string; icon: any }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
];

const llmProvider = ref<LLMProvider>('');
const apiKey = ref('');
const neo4jUri = ref('');
const neo4jUser = ref('');
const neo4jPassword = ref('');

const providerOptions: { value: LLMProvider; label: string }[] = [
  { value: '', label: 'Use server default' },
  { value: 'gemini', label: 'Gemini (Google AI)' },
  { value: 'openrouter', label: 'OpenRouter' },
];

const apiKeyLabel = computed(() => {
  if (llmProvider.value === 'gemini') return 'Gemini API Key';
  if (llmProvider.value === 'openrouter') return 'OpenRouter API Key';
  return 'LLM API Key (optional)';
});

const apiKeyPlaceholder = computed(() => {
  if (llmProvider.value === 'gemini') return 'AIza...';
  if (llmProvider.value === 'openrouter') return 'sk-or-...';
  return 'Paste your API key here...';
});

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

const saveConfig = () => {
  localStorage.setItem('endstate_llm_provider', llmProvider.value);
  localStorage.setItem('endstate_gemini_api_key', apiKey.value);
  localStorage.setItem('endstate_openrouter_api_key', apiKey.value);
  localStorage.setItem('endstate_neo4j_uri', neo4jUri.value);
  localStorage.setItem('endstate_neo4j_user', neo4jUser.value);
  localStorage.setItem('endstate_neo4j_password', neo4jPassword.value);
  emit('close');
};

const handleBackdropClick = (e: MouseEvent) => {
  if (e.target === e.currentTarget) {
    emit('close');
  }
};

const loadConfig = () => {
  llmProvider.value = (localStorage.getItem('endstate_llm_provider') || '') as LLMProvider;
  apiKey.value = localStorage.getItem('endstate_openrouter_api_key') || localStorage.getItem('endstate_gemini_api_key') || '';
  neo4jUri.value = localStorage.getItem('endstate_neo4j_uri') || '';
  neo4jUser.value = localStorage.getItem('endstate_neo4j_user') || '';
  neo4jPassword.value = localStorage.getItem('endstate_neo4j_password') || '';
};

watch(() => props.isOpen, (open) => {
  if (open) {
    const savedTheme = localStorage.getItem('endstate-theme') as Theme | null;
    if (savedTheme) {
      currentTheme.value = savedTheme;
      applyTheme(savedTheme);
    }
    loadConfig();
  }
});

onMounted(() => {
  const savedTheme = localStorage.getItem('endstate-theme') as Theme | null;
  if (savedTheme) {
    currentTheme.value = savedTheme;
    applyTheme(savedTheme);
  } else {
    applyTheme('system');
  }
  loadConfig();
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

          <div class="space-y-4 pt-4 border-t dark:border-surface-700">
            <h3 class="text-sm font-medium text-surface-900 dark:text-white">Cloud Configuration</h3>
            
            <div class="space-y-3">
              <div>
                <label class="block text-xs font-medium text-surface-500 dark:text-surface-400 mb-1">LLM Provider</label>
                <select
                  v-model="llmProvider"
                  class="w-full px-3 py-2 text-sm rounded-lg border dark:border-surface-700 bg-white dark:bg-surface-900 text-surface-900 dark:text-white focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                >
                  <option v-for="opt in providerOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </div>

              <div>
                <label class="block text-xs font-medium text-surface-500 dark:text-surface-400 mb-1">{{ apiKeyLabel }}</label>
                <input 
                  v-model="apiKey"
                  type="password"
                  :placeholder="apiKeyPlaceholder"
                  class="w-full px-3 py-2 text-sm rounded-lg border dark:border-surface-700 bg-white dark:bg-surface-900 text-surface-900 dark:text-white focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                />
              </div>

              <div>
                <label class="block text-xs font-medium text-surface-500 dark:text-surface-400 mb-1">Neo4j URI</label>
                <input 
                  v-model="neo4jUri"
                  type="text"
                  placeholder="neo4j+s://xxxx.databases.neo4j.io"
                  class="w-full px-3 py-2 text-sm rounded-lg border dark:border-surface-700 bg-white dark:bg-surface-900 text-surface-900 dark:text-white focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                />
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs font-medium text-surface-500 dark:text-surface-400 mb-1">Neo4j Username</label>
                  <input 
                    v-model="neo4jUser"
                    type="text"
                    placeholder="neo4j"
                    class="w-full px-3 py-2 text-sm rounded-lg border dark:border-surface-700 bg-white dark:bg-surface-900 text-surface-900 dark:text-white focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                  />
                </div>
                <div>
                  <label class="block text-xs font-medium text-surface-500 dark:text-surface-400 mb-1">Neo4j Password</label>
                  <input 
                    v-model="neo4jPassword"
                    type="password"
                    placeholder="password"
                    class="w-full px-3 py-2 text-sm rounded-lg border dark:border-surface-700 bg-white dark:bg-surface-900 text-surface-900 dark:text-white focus:ring-2 focus:ring-primary-500 outline-none transition-all"
                  />
                </div>
              </div>
            </div>
          </div>
          
          <div class="pt-4 flex gap-3">
            <button 
              @click="saveConfig"
              class="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Save Changes
            </button>
            <button 
              @click="emit('close')"
              class="px-4 py-2 bg-surface-100 dark:bg-surface-700 hover:bg-surface-200 dark:hover:bg-surface-600 text-surface-700 dark:text-surface-200 rounded-lg text-sm font-medium transition-colors"
            >
              Cancel
            </button>
          </div>

          <div class="pt-2">
            <p class="text-[10px] leading-relaxed text-surface-500 dark:text-surface-400">
              Credentials are stored safely in your browser and sent only to the backend. This allows you to use your own free tiers for live demos.
            </p>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
