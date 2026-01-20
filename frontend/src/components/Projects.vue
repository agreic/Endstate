<script setup lang="ts">
import { ref, onMounted } from "vue";
import { FolderOpen, Trash2, Clock, ChevronRight, BookOpen } from "lucide-vue-next";
import { listProjects, getProject, deleteProject, type ProjectSummary, type ProjectListItem } from "../services/api";

const projects = ref<ProjectListItem[]>([]);
const selectedProject = ref<ProjectSummary | null>(null);
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
    return;
  }
  
  isLoadingProject.value = true;
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

const confirmDelete = async (projectId: string) => {
  if (!confirm("Delete this project summary? This cannot be undone.")) return;
  
  try {
    await deleteProject(projectId);
    if (selectedProject.value?.session_id === projectId) {
      selectedProject.value = null;
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

onMounted(() => {
  loadProjects();
});
</script>

<template>
  <div class="h-full bg-surface-50 overflow-y-auto">
    <div class="p-6 max-w-6xl mx-auto">
      <div class="mb-8">
        <h1 class="text-2xl font-bold text-surface-800 mb-2">Projects</h1>
        <p class="text-surface-500">
          Your saved learning projects and goals
        </p>
      </div>

      <div v-if="error" class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-red-600 text-sm">{{ error }}</p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 class="text-lg font-semibold text-surface-800 mb-4">All Projects</h2>
          
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
          
          <div v-else class="space-y-3">
            <button
              v-for="project in projects"
              :key="project.id"
              @click="selectProject(project.id)"
              class="w-full bg-white rounded-xl p-4 border border-surface-200 hover:border-primary-300 hover:shadow-md transition-all text-left"
              :class="{ 'border-primary-500 ring-2 ring-primary-100': selectedProject?.session_id === project.id }"
            >
              <div class="flex items-center justify-between mb-2">
                <h3 class="font-semibold text-surface-800">{{ project.name }}</h3>
                <ChevronRight
                  :size="16"
                  class="text-surface-400 transition-transform"
                  :class="{ 'rotate-90': selectedProject?.session_id === project.id }"
                />
              </div>
              <div class="flex items-center gap-2 text-xs text-surface-400">
                <Clock :size="12" />
                <span>{{ formatDate(project.created_at) }}</span>
              </div>
              <div v-if="project.interests.length > 0" class="mt-2 flex flex-wrap gap-1">
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

        <div>
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
          
          <div v-else class="bg-white rounded-xl shadow-sm border border-surface-200 overflow-hidden">
            <div class="p-6 border-b border-surface-100">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-xl font-bold text-surface-800">{{ selectedProject.agreed_project?.name || 'Untitled' }}</h3>
                <button
                  @click="confirmDelete(selectedProject.session_id)"
                  class="p-2 rounded-lg hover:bg-red-50 text-red-500 transition-colors"
                  title="Delete project"
                >
                  <Trash2 :size="18" />
                </button>
              </div>
              <p class="text-surface-600">{{ selectedProject.agreed_project?.description }}</p>
              <div class="mt-3 flex items-center gap-2 text-sm text-surface-400">
                <Clock :size="14" />
                <span>Timeline: {{ selectedProject.agreed_project?.timeline || 'Not specified' }}</span>
              </div>
            </div>

            <div class="p-6 border-b border-surface-100">
              <h4 class="text-sm font-semibold text-surface-400 uppercase mb-3">Your Profile</h4>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <p class="text-xs text-surface-400 mb-1">Interests</p>
                  <div class="flex flex-wrap gap-1">
                    <span
                      v-for="interest in selectedProject.user_profile?.interests || []"
                      :key="interest"
                      class="text-sm px-2 py-0.5 bg-primary-50 text-primary-700 rounded-full"
                    >
                      {{ interest }}
                    </span>
                  </div>
                </div>
                <div>
                  <p class="text-xs text-surface-400 mb-1">Skill Level</p>
                  <p class="text-sm text-surface-700 capitalize">{{ selectedProject.user_profile?.skill_level || 'Not specified' }}</p>
                </div>
                <div>
                  <p class="text-xs text-surface-400 mb-1">Time Available</p>
                  <p class="text-sm text-surface-700">{{ selectedProject.user_profile?.time_available || 'Not specified' }}</p>
                </div>
                <div>
                  <p class="text-xs text-surface-400 mb-1">Learning Style</p>
                  <p class="text-sm text-surface-700 capitalize">{{ selectedProject.user_profile?.learning_style || 'Not specified' }}</p>
                </div>
              </div>
            </div>

            <div v-if="selectedProject.agreed_project?.milestones?.length" class="p-6 border-b border-surface-100">
              <h4 class="text-sm font-semibold text-surface-400 uppercase mb-3">Milestones</h4>
              <div class="space-y-2">
                <div
                  v-for="(milestone, index) in selectedProject.agreed_project.milestones"
                  :key="index"
                  class="flex items-start gap-3"
                >
                  <span class="w-6 h-6 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-medium flex-shrink-0">
                    {{ index + 1 }}
                  </span>
                  <span class="text-sm text-surface-700">{{ milestone }}</span>
                </div>
              </div>
            </div>

            <div class="p-6 grid grid-cols-3 gap-4">
              <div v-if="selectedProject.topics?.length">
                <h4 class="text-xs font-semibold text-surface-400 uppercase mb-2">Topics</h4>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="topic in selectedProject.topics"
                    :key="topic"
                    class="text-xs px-2 py-0.5 bg-surface-100 text-surface-600 rounded-full"
                  >
                    {{ topic }}
                  </span>
                </div>
              </div>
              <div v-if="selectedProject.skills?.length">
                <h4 class="text-xs font-semibold text-surface-400 uppercase mb-2">Skills</h4>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="skill in selectedProject.skills"
                    :key="skill"
                    class="text-xs px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-full"
                  >
                    {{ skill }}
                  </span>
                </div>
              </div>
              <div v-if="selectedProject.concepts?.length">
                <h4 class="text-xs font-semibold text-surface-400 uppercase mb-2">Concepts</h4>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="concept in selectedProject.concepts"
                    :key="concept"
                    class="text-xs px-2 py-0.5 bg-amber-50 text-amber-700 rounded-full"
                  >
                    {{ concept }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
