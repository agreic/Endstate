<script setup lang="ts">
import { ref, onMounted } from "vue";
import { FolderOpen, Trash2, Clock, ChevronRight, BookOpen, Target, Zap, Brain, CheckCircle, MessageSquare, ChevronDown, ChevronUp, User, Bot } from "lucide-vue-next";
import { listProjects, getProject, deleteProject, getProjectChat, type ProjectSummary, type ProjectListItem, type ChatMessage } from "../services/api";

const projects = ref<ProjectListItem[]>([]);
const selectedProject = ref<ProjectSummary | null>(null);
const chatMessages = ref<ChatMessage[]>([]);
const showChatHistory = ref(false);
const isLoadingChat = ref(false);
const isLoading = ref(true);
const isLoadingProject = ref(false);
const error = ref<string | null>(null);

const loadProjects = async () => {
  isLoading.value = true;
  error.value = null;
  try {
    const response = await listProjects();
    projects.value = response.projects;
  } catch (e) {
    error.value = "Failed to load projects";
    console.error(e);
  } finally {
    isLoading.value = false;
  }
};

const selectProject = async (projectId: string) => {
  if (selectedProject.value?.session_id === projectId) {
    selectedProject.value = null;
    chatMessages.value = [];
    showChatHistory.value = false;
    return;
  }
  
  isLoadingProject.value = true;
  showChatHistory.value = false;
  chatMessages.value = [];
  try {
    const project = await getProject(projectId);
    selectedProject.value = project;
  } catch (e) {
    error.value = "Failed to load project details";
    console.error(e);
  } finally {
    isLoadingProject.value = false;
  }
};

const toggleChatHistory = async () => {
  if (showChatHistory.value) {
    showChatHistory.value = false;
    return;
  }
  
  if (chatMessages.value.length > 0) {
    showChatHistory.value = true;
    return;
  }
  
  if (!selectedProject.value) return;
  
  isLoadingChat.value = true;
  try {
    const response = await getProjectChat(selectedProject.value.session_id);
    chatMessages.value = response.messages;
    showChatHistory.value = true;
  } catch (e) {
    console.error("Failed to load chat history:", e);
    chatMessages.value = [];
    showChatHistory.value = true;
  } finally {
    isLoadingChat.value = false;
  }
};

const confirmDelete = async (projectId: string) => {
  if (!confirm("Delete this project and its chat history? This cannot be undone.")) return;
  
  try {
    await deleteProject(projectId);
    if (selectedProject.value?.session_id === projectId) {
      selectedProject.value = null;
      chatMessages.value = [];
      showChatHistory.value = false;
    }
    await loadProjects();
  } catch (e) {
    error.value = "Failed to delete project";
    console.error(e);
  }
};

const formatDate = (dateStr: string): string => {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const formatTime = (dateStr?: string): string => {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

onMounted(() => {
  loadProjects();
});
</script>

<template>
  <div class="h-full bg-surface-50 overflow-y-auto">
    <div class="p-6 max-w-7xl mx-auto">
      <div class="mb-8">
        <h1 class="text-2xl font-bold text-surface-800 mb-2">My Projects</h1>
        <p class="text-surface-500">
          Your learning projects and goals
        </p>
      </div>

      <div v-if="error" class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-red-600 text-sm">{{ error }}</p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-1">
          <h2 class="text-lg font-semibold text-surface-800 mb-4">Projects</h2>
          
          <div v-if="isLoading" class="flex items-center justify-center py-12">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
          
          <div v-else-if="projects.length === 0" class="bg-white rounded-xl p-8 border border-surface-200 text-center">
            <FolderOpen :size="48" class="text-surface-300 mx-auto mb-4" />
            <h3 class="text-lg font-medium text-surface-600 mb-2">No projects yet</h3>
            <p class="text-sm text-surface-400">
              Start a chat conversation to create your first project plan
            </p>
          </div>
          
          <div v-else class="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
            <button
              v-for="project in projects"
              :key="project.id"
              @click="selectProject(project.id)"
              class="w-full bg-white rounded-xl p-4 border border-surface-200 hover:border-primary-300 hover:shadow-md transition-all text-left"
              :class="{ 'border-primary-500 ring-2 ring-primary-100': selectedProject?.session_id === project.id }"
            >
              <div class="flex items-center justify-between mb-2">
                <Target :size="18" class="text-primary-500" />
                <ChevronRight
                  :size="16"
                  class="text-surface-400 transition-transform"
                  :class="{ 'rotate-90': selectedProject?.session_id === project.id }"
                />
              </div>
              <h3 class="font-semibold text-surface-800 mb-2 line-clamp-2">{{ project.name }}</h3>
              <div class="flex items-center gap-2 text-xs text-surface-400">
                <Clock :size="12" />
                <span>{{ formatDate(project.created_at) }}</span>
              </div>
              <div v-if="project.interests.length > 0" class="mt-3 flex flex-wrap gap-1">
                <span
                  v-for="interest in project.interests.slice(0, 3)"
                  :key="interest"
                  class="text-xs px-2 py-0.5 bg-surface-100 text-surface-600 rounded-full"
                >
                  {{ interest }}
                </span>
              </div>
            </button>
          </div>
        </div>

        <div class="lg:col-span-2">
          <h2 class="text-lg font-semibold text-surface-800 mb-4">Project Details</h2>
          
          <div v-if="isLoadingProject" class="flex items-center justify-center py-12">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
          
          <div v-else-if="!selectedProject" class="bg-white rounded-xl p-8 border border-surface-200 text-center">
            <BookOpen :size="48" class="text-surface-300 mx-auto mb-4" />
            <h3 class="text-lg font-medium text-surface-600 mb-2">Select a project</h3>
            <p class="text-sm text-surface-400">
              Click on a project to view its details
            </p>
          </div>
          
          <div v-else class="space-y-4">
            <div class="bg-white rounded-xl shadow-sm border border-surface-200 overflow-hidden">
              <div class="bg-gradient-to-r from-primary-500 to-primary-600 p-6 text-white">
                <div class="flex items-start justify-between">
                  <div>
                    <div class="flex items-center gap-2 mb-2 opacity-90">
                      <Target :size="16" />
                      <span class="text-xs uppercase tracking-wider">Learning Project</span>
                    </div>
                    <h3 class="text-2xl font-bold">{{ selectedProject.agreed_project?.name || 'Untitled Project' }}</h3>
                  </div>
                  <button
                    @click="confirmDelete(selectedProject.session_id)"
                    class="p-2 rounded-lg bg-white/20 hover:bg-white/30 transition-colors"
                    title="Delete project"
                  >
                    <Trash2 :size="18" />
                  </button>
                </div>
                <p class="mt-3 text-primary-100 text-sm">{{ selectedProject.agreed_project?.description }}</p>
                <div class="mt-4 flex items-center gap-4 text-sm">
                  <div class="flex items-center gap-1.5">
                    <Clock :size="14" />
                    <span>{{ selectedProject.agreed_project?.timeline || 'Flexible timeline' }}</span>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <CheckCircle :size="14" />
                    <span>{{ selectedProject.agreed_project?.milestones?.length || 0 }} milestones</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="bg-white rounded-xl shadow-sm border border-surface-200 p-6">
              <div class="flex items-center gap-2 mb-4">
                <Brain :size="20" class="text-primary-500" />
                <h4 class="font-semibold text-surface-800">Your Profile</h4>
              </div>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="p-3 bg-surface-50 rounded-lg">
                  <p class="text-xs text-surface-400 mb-1">Interests</p>
                  <div class="flex flex-wrap gap-1">
                    <span
                      v-for="interest in selectedProject.user_profile?.interests || []"
                      :key="interest"
                      class="text-xs px-2 py-0.5 bg-primary-100 text-primary-700 rounded-full"
                    >
                      {{ interest }}
                    </span>
                  </div>
                </div>
                <div class="p-3 bg-surface-50 rounded-lg">
                  <p class="text-xs text-surface-400 mb-1">Skill Level</p>
                  <p class="text-sm font-medium text-surface-700 capitalize">{{ selectedProject.user_profile?.skill_level || 'Not set' }}</p>
                </div>
                <div class="p-3 bg-surface-50 rounded-lg">
                  <p class="text-xs text-surface-400 mb-1">Time / Week</p>
                  <p class="text-sm font-medium text-surface-700">{{ selectedProject.user_profile?.time_available || 'Not set' }}</p>
                </div>
                <div class="p-3 bg-surface-50 rounded-lg">
                  <p class="text-xs text-surface-400 mb-1">Style</p>
                  <p class="text-sm font-medium text-surface-700 capitalize">{{ selectedProject.user_profile?.learning_style || 'Not set' }}</p>
                </div>
              </div>
            </div>

            <div v-if="selectedProject.agreed_project?.milestones?.length" class="bg-white rounded-xl shadow-sm border border-surface-200 p-6">
              <div class="flex items-center gap-2 mb-4">
                <Zap :size="20" class="text-amber-500" />
                <h4 class="font-semibold text-surface-800">Milestones</h4>
              </div>
              <div class="space-y-3">
                <div
                  v-for="(milestone, index) in selectedProject.agreed_project.milestones"
                  :key="index"
                  class="flex items-start gap-3 p-3 bg-surface-50 rounded-lg"
                >
                  <span class="w-6 h-6 rounded-full bg-primary-500 text-white flex items-center justify-center text-xs font-bold flex-shrink-0">
                    {{ index + 1 }}
                  </span>
                  <span class="text-sm text-surface-700">{{ milestone }}</span>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div v-if="selectedProject.skills?.length" class="bg-white rounded-xl shadow-sm border border-surface-200 p-5">
                <div class="flex items-center gap-2 mb-3">
                  <CheckCircle :size="18" class="text-emerald-500" />
                  <h4 class="font-semibold text-surface-800">Skills</h4>
                </div>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="skill in selectedProject.skills"
                    :key="skill"
                    class="text-xs px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full"
                  >
                    {{ skill }}
                  </span>
                </div>
              </div>
              <div v-if="selectedProject.topics?.length" class="bg-white rounded-xl shadow-sm border border-surface-200 p-5">
                <div class="flex items-center gap-2 mb-3">
                  <BookOpen :size="18" class="text-blue-500" />
                  <h4 class="font-semibold text-surface-800">Topics</h4>
                </div>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="topic in selectedProject.topics"
                    :key="topic"
                    class="text-xs px-3 py-1 bg-blue-50 text-blue-700 rounded-full"
                  >
                    {{ topic }}
                  </span>
                </div>
              </div>
              <div v-if="selectedProject.concepts?.length" class="bg-white rounded-xl shadow-sm border border-surface-200 p-5">
                <div class="flex items-center gap-2 mb-3">
                  <Brain :size="18" class="text-amber-500" />
                  <h4 class="font-semibold text-surface-800">Concepts</h4>
                </div>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="concept in selectedProject.concepts"
                    :key="concept"
                    class="text-xs px-3 py-1 bg-amber-50 text-amber-700 rounded-full"
                  >
                    {{ concept }}
                  </span>
                </div>
              </div>
            </div>

            <div v-if="selectedProject" class="mt-6">
              <button
                @click="toggleChatHistory"
                class="w-full flex items-center justify-between p-4 bg-white rounded-xl border border-surface-200 hover:border-primary-300 transition-colors"
              >
                <div class="flex items-center gap-2">
                  <MessageSquare :size="18" class="text-primary-500" />
                  <span class="font-semibold text-surface-800">Chat History</span>
                  <span class="text-xs text-surface-400">({{ chatMessages.length || ' archived' }})</span>
                </div>
                <ChevronDown v-if="!showChatHistory" :size="18" class="text-surface-400" />
                <ChevronUp v-else :size="18" class="text-surface-400" />
              </button>

              <div v-if="showChatHistory" class="mt-4 bg-white rounded-xl border border-surface-200 overflow-hidden">
                <div v-if="isLoadingChat" class="p-8 text-center">
                  <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
                </div>
                <div v-else-if="chatMessages.length === 0" class="p-8 text-center text-surface-400">
                  <MessageSquare :size="32" class="mx-auto mb-2 opacity-50" />
                  <p>No chat history available for this project</p>
                </div>
                <div v-else class="divide-y divide-surface-100 max-h-96 overflow-y-auto">
                  <div
                    v-for="(msg, index) in chatMessages"
                    :key="index"
                    class="flex gap-3 p-4"
                    :class="msg.role === 'user' ? 'bg-surface-50' : ''"
                  >
                    <div
                      class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                      :class="msg.role === 'user' ? 'bg-primary-600' : 'bg-gradient-to-br from-primary-400 to-primary-600'"
                    >
                      <User v-if="msg.role === 'user'" :size="14" class="text-white" />
                      <Bot v-else :size="14" class="text-white" />
                    </div>
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-2 mb-1">
                        <span class="text-xs font-medium" :class="msg.role === 'user' ? 'text-primary-600' : 'text-primary-500'">
                          {{ msg.role === 'user' ? 'You' : 'Assistant' }}
                        </span>
                        <span class="text-[10px] text-surface-400">{{ formatTime(msg.timestamp) }}</span>
                      </div>
                      <p class="text-sm text-surface-700 whitespace-pre-wrap">{{ msg.content }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
