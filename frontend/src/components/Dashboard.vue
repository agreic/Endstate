<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  MessageSquare,
  Network,
  ArrowRight,
  Sparkles,
  TrendingUp,
} from "lucide-vue-next";
import { fetchGraphStats, listProjects } from "../services/api";

const emit = defineEmits<{
  navigate: [tab: "dashboard" | "chat" | "graph" | "projects"];
}>();

interface Stat {
  label: string;
  value: string;
  change: string;
  icon: any;
}

const stats = ref<Stat[]>([]);
const isLoading = ref(true);

const quickActions = [
  {
    label: "Start New Chat",
    icon: MessageSquare,
    color: "bg-primary-500",
    tab: "chat" as const,
  },
  {
    label: "Explore Graph",
    icon: Network,
    color: "bg-emerald-500",
    tab: "graph" as const,
  },
  {
    label: "View Projects",
    icon: Sparkles,
    color: "bg-amber-500",
    tab: "projects" as const,
  },
];

const loadDashboardData = async () => {
  isLoading.value = true;
  try {
    const [graphStatsData, projectsData] = await Promise.all([
      fetchGraphStats(),
      listProjects(),
    ]);
    
    stats.value = [
      { label: "Projects", value: formatNumber(projectsData.projects.length), change: "—", icon: Sparkles },
      { label: "Graph Nodes", value: formatNumber(graphStatsData.total_nodes), change: "—", icon: Network },
      { label: "Relationships", value: formatNumber(graphStatsData.total_relationships), change: "—", icon: TrendingUp },
    ];
  } catch (error) {
    console.error("Failed to load dashboard data:", error);
    stats.value = [
      { label: "Projects", value: "--", change: "—", icon: Sparkles },
      { label: "Graph Nodes", value: "--", change: "—", icon: Network },
      { label: "Relationships", value: "--", change: "—", icon: TrendingUp },
    ];
  } finally {
    isLoading.value = false;
  }
};

const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
};

onMounted(() => {
  loadDashboardData();
});
</script>

<template>
  <div class="h-full bg-surface-50 overflow-y-auto">
    <div class="p-6 max-w-6xl mx-auto">
      <div class="mb-8">
        <h1 class="text-2xl font-bold text-surface-800 mb-2">Welcome back!</h1>
        <p class="text-surface-500">
          Here's what's happening with your knowledge base today.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div
          v-for="stat in stats"
          :key="stat.label"
          class="bg-white rounded-xl p-5 shadow-sm border border-surface-100 hover:shadow-md transition-shadow"
        >
          <div class="flex items-center justify-between mb-3">
            <div
              class="w-10 h-10 rounded-lg bg-primary-50 flex items-center justify-center"
            >
              <component :is="stat.icon" :size="20" class="text-primary-600" />
            </div>
            <span
              class="text-xs font-medium text-surface-400 bg-surface-50 px-2 py-1 rounded-full"
            >
              {{ stat.change }}
            </span>
          </div>
          <p class="text-2xl font-bold text-surface-800 mb-1">
            {{ stat.value }}
          </p>
          <p class="text-sm text-surface-500">{{ stat.label }}</p>
        </div>
      </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div
            class="lg:col-span-3 bg-white rounded-xl p-6 shadow-sm border border-surface-100"
          >
            <div class="flex items-center justify-between mb-6">
              <h2 class="text-lg font-semibold text-surface-800">
                Quick Actions
              </h2>
            </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <button
                v-for="action in quickActions"
                :key="action.label"
                @click="action.tab && emit('navigate', action.tab)"
                class="flex items-center gap-3 p-4 ..."
              >
              <div
                :class="[
                  action.color,
                  'w-10 h-10 rounded-lg flex items-center justify-center',
                ]"
              >
                <component :is="action.icon" :size="20" class="text-white" />
              </div>
              <span
                class="text-sm font-medium text-surface-700 group-hover:text-primary-700"
              >
                {{ action.label }}
              </span>
              <ArrowRight
                :size="16"
                class="ml-auto text-surface-400 group-hover:text-primary-500 transition-colors"
              />
              </button>
            </div>
          </div>
      </div>

      <div
        class="bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl p-6 text-white"
      >
        <div class="flex items-start gap-4">
          <div
            class="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0"
          >
            <Sparkles :size="24" />
          </div>
          <div>
            <h3 class="text-lg font-semibold mb-2">
              Pro Tip: Explore Connections
            </h3>
            <p class="text-primary-100 text-sm mb-4">
              Did you know you can drag nodes in the Knowledge Graph to
              reorganize your data? Try clicking on any node to see its
              connections and details.
            </p>
            <button
              @click="emit('navigate', 'graph')"
              class="px-4 py-2 bg-white text-primary-600 rounded-lg text-sm font-medium hover:bg-primary-50 transition-colors"
            >
              Open graph
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
