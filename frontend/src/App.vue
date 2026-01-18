<script setup lang="ts">
import { ref } from "vue";
import Sidebar from "./components/Sidebar.vue";
import Dashboard from "./components/Dashboard.vue";
import ChatBox from "./components/ChatBox.vue";
import KnowledgeGraph from "./components/KnowledgeGraph.vue";
import { MessageSquare, Network, Settings } from "lucide-vue-next";

const sidebarOpen = ref(true);
const activeTab = ref<"dashboard" | "chat" | "graph">("dashboard");

// --- STABLE GRAPH STATE: Persists ML nodes and discovered cooking/web skills ---
const graphState = ref({
  nodes: [
    {
      id: "1",
      group: 1,
      label: "Machine Learning",
      description: "Field of AI that enables systems to learn",
    },
    {
      id: "2",
      group: 1,
      label: "Deep Learning",
      description: "Subset of ML using neural networks",
    },
    {
      id: "3",
      group: 1,
      label: "Neural Networks",
      description: "Bio-inspired computing",
    },
    {
      id: "4",
      group: 2,
      label: "Python",
      description: "AI Programming Language",
    },
    {
      id: "14",
      group: 5,
      label: "Data Science",
      description: "Extracting insights from data",
    },
    {
      id: "15",
      group: 5,
      label: "Analytics",
      description: "Analyzing data for decisions",
    },
  ],
  links: [
    { source: "1", target: "2", value: 3 },
    { source: "2", target: "3", value: 3 },
    { source: "1", target: "14", value: 2 },
    { source: "14", target: "15", value: 2 },
  ],
});

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value;
};

const setActiveTab = (tab: "dashboard" | "chat" | "graph") => {
  activeTab.value = tab;
};

// Handler to receive new skills/links from the LLM Architect
const handleGraphUpdate = (newData: { newNodes: any[]; newLinks: any[] }) => {
  newData.newNodes.forEach((node) => {
    if (!graphState.value.nodes.find((n) => n.id === node.id)) {
      graphState.value.nodes.push(node);
    }
  });
  newData.newLinks.forEach((link) => {
    graphState.value.links.push(link);
  });
};
</script>

<template>
  <div class="flex h-full bg-surface-100 font-sans">
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
      <header
        class="h-14 bg-white border-b border-surface-200 flex items-center justify-between px-4 shadow-sm z-20"
      >
        <div class="flex items-center gap-3">
          <h1 class="text-lg font-semibold text-surface-800">Endstate</h1>
          <span
            class="text-xs px-2 py-0.5 bg-primary-100 text-primary-700 rounded-full font-bold"
            >Demo</span
          >
        </div>

        <div class="flex items-center gap-2">
          <nav class="flex bg-surface-100 rounded-lg p-1">
            <button
              @click="setActiveTab('dashboard')"
              class="flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all"
              :class="
                activeTab === 'dashboard'
                  ? 'bg-white text-primary-600 shadow-sm'
                  : 'text-surface-500 hover:text-surface-700'
              "
            >
              Dashboard
            </button>
            <button
              @click="setActiveTab('chat')"
              class="flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all"
              :class="
                activeTab === 'chat'
                  ? 'bg-white text-primary-600 shadow-sm'
                  : 'text-surface-500 hover:text-surface-700'
              "
            >
              <MessageSquare :size="16" />
              Chat
            </button>
            <button
              @click="setActiveTab('graph')"
              class="flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all"
              :class="
                activeTab === 'graph'
                  ? 'bg-white text-primary-600 shadow-sm'
                  : 'text-surface-500 hover:text-surface-700'
              "
            >
              <Network :size="16" />
              Knowledge Graph
            </button>
          </nav>
        </div>

        <div class="flex items-center gap-3">
          <button
            class="p-2 text-surface-400 hover:text-surface-600 hover:bg-surface-100 rounded-lg transition-colors"
          >
            <Settings :size="18" />
          </button>
          <div
            class="w-8 h-8 bg-gradient-to-br from-primary-400 to-primary-600 rounded-full shadow-inner border border-white"
          ></div>
        </div>
      </header>

      <div class="flex-1 relative overflow-hidden">
        <Dashboard v-if="activeTab === 'dashboard'" @navigate="setActiveTab" />

        <div v-show="activeTab === 'chat'" class="h-full">
          <ChatBox @updateGraph="handleGraphUpdate" />
        </div>

        <div
          v-if="activeTab === 'graph'"
          class="h-full"
          :key="graphState.nodes.length"
        >
          <KnowledgeGraph :external-data="graphState" />
        </div>
      </div>
    </main>
  </div>
</template>
