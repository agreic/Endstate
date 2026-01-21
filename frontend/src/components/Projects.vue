<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from "vue";
import { FolderOpen, Trash2, Clock, ChevronRight, BookOpen, Target, Brain, CheckCircle, MessageSquare, ChevronDown, ChevronUp, User, Bot, Pencil, Save, X, Play, Zap } from "lucide-vue-next";
import { marked } from "marked";
import { listProjects, getProject, deleteProject, getProjectChat, renameProject, startProject, listProjectLessons, listProjectAssessments, updateProjectProfile, createProjectAssessment, submitProjectAssessment, archiveProjectLesson, deleteProjectLesson, archiveProjectAssessment, deleteProjectAssessment, getJobStatus, cancelJob, type ProjectSummary, type ProjectListItem, type ChatMessage, type ProjectLesson, type ProjectAssessment } from "../services/api";

const projects = ref<ProjectListItem[]>([]);
const selectedProject = ref<ProjectSummary | null>(null);
const chatMessages = ref<ChatMessage[]>([]);
const showChatHistory = ref(false);
const isLoadingChat = ref(false);
const isLoading = ref(true);
const isLoadingProject = ref(false);
const error = ref<string | null>(null);
const isRenaming = ref(false);
const renameValue = ref("");
const renameError = ref<string | null>(null);
const isStarting = ref(false);
const startError = ref<string | null>(null);
const startStats = ref<{ nodes: number; relationships: number } | null>(null);
const reinitJobId = ref<string | null>(null);
let reinitPollTimer: number | null = null;
const profileDraft = ref({
  interests: [] as string[],
  interestsText: "",
  skill_level: "intermediate",
  time_available: "2 hours/week",
  learning_style: "hybrid",
});
const profileSaving = ref(false);
const profileError = ref<string | null>(null);
const lessons = ref<ProjectLesson[]>([]);
const selectedLesson = ref<ProjectLesson | null>(null);
const showAssessmentPanel = ref(false);
const assessments = ref<ProjectAssessment[]>([]);
const assessmentAnswers = ref<Record<string, string>>({});
const assessmentError = ref<string | null>(null);
const lessonsLoading = ref(false);
const assessmentsLoading = ref(false);
const assessmentJobs = ref<Array<{ job_id: string; lesson_id: string }>>([]);
const assessmentJobTimers = new Map<string, number>();

const DEFAULT_PROJECT_ID = "project-all";

const activeLessons = computed(() => lessons.value.filter((lesson) => !lesson.archived));
const archivedLessons = computed(() => lessons.value.filter((lesson) => lesson.archived));
const activeAssessments = computed(() => assessments.value.filter((assessment) => !assessment.archived));
const archivedAssessments = computed(() => assessments.value.filter((assessment) => assessment.archived));

const SKILL_LEVELS = ["Beginner", "Intermediate", "Experienced", "Advanced"];
const TIME_OPTIONS = [
  "10 minutes/week",
  "30 minutes/week",
  "1 hour/week",
  "2 hours/week",
  "5 hours/week",
  "10 hours/week",
  "10+ hours/week",
];
const STYLE_OPTIONS = ["Theoretical", "Hands-on", "Hybrid"];

const renderMarkdown = (content: string) => {
  return marked.parse(content || "");
};

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
    startStats.value = null;
    lessons.value = [];
    assessments.value = [];
    assessmentJobs.value = [];
    clearAssessmentJobTimers();
    localStorage.removeItem("endstate_active_project_id");
    return;
  }
  
  isLoadingProject.value = true;
  showChatHistory.value = false;
  chatMessages.value = [];
  startStats.value = null;
  lessons.value = [];
  assessments.value = [];
  assessmentJobs.value = [];
  clearAssessmentJobTimers();
  try {
    const project = await getProject(projectId);
    selectedProject.value = project;
    renameValue.value = project.agreed_project?.name || "";
    localStorage.setItem("endstate_active_project_id", project.session_id);
    const interests = project.user_profile?.interests || [];
    profileDraft.value = {
      interests,
      interestsText: interests.join(", "),
      skill_level: project.user_profile?.skill_level || "intermediate",
      time_available: project.user_profile?.time_available || "2 hours/week",
      learning_style: project.user_profile?.learning_style || "hybrid",
    };
    await loadProjectExtras(projectId);
    loadAssessmentJobsForProject(projectId);
  } catch (e) {
    error.value = "Failed to load project details";
    console.error(e);
  } finally {
    isLoadingProject.value = false;
  }
};

const loadProjectExtras = async (projectId: string) => {
  lessonsLoading.value = true;
  assessmentsLoading.value = true;
  try {
    const [lessonsResponse, assessmentsResponse] = await Promise.all([
      listProjectLessons(projectId),
      listProjectAssessments(projectId),
    ]);
    lessons.value = [...lessonsResponse.lessons].sort((a, b) => {
      const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
      return aTime - bTime;
    });
    assessments.value = assessmentsResponse.assessments;
  } catch (e) {
    console.error("Failed to load project extras", e);
  } finally {
    lessonsLoading.value = false;
    assessmentsLoading.value = false;
  }
};

const assessmentJobsKey = (projectId: string) => `endstate_assessment_jobs_${projectId}`;

const persistAssessmentJobs = (projectId: string) => {
  localStorage.setItem(assessmentJobsKey(projectId), JSON.stringify(assessmentJobs.value));
};

const clearAssessmentJobTimers = () => {
  assessmentJobTimers.forEach((timerId) => window.clearTimeout(timerId));
  assessmentJobTimers.clear();
};

const scheduleAssessmentPoll = (jobId: string, projectId: string) => {
  if (assessmentJobTimers.has(jobId)) return;
  const timerId = window.setTimeout(async () => {
    assessmentJobTimers.delete(jobId);
    try {
      const status = await getJobStatus(jobId);
      if (status.status === "completed" && status.result) {
        await loadProjectExtras(projectId);
        assessmentJobs.value = assessmentJobs.value.filter((job) => job.job_id !== jobId);
        persistAssessmentJobs(projectId);
        return;
      }
      if (status.status === "failed" || status.status === "canceled") {
        assessmentJobs.value = assessmentJobs.value.filter((job) => job.job_id !== jobId);
        persistAssessmentJobs(projectId);
        return;
      }
    } catch (e) {
      console.error("Failed to poll assessment job", e);
    }
    scheduleAssessmentPoll(jobId, projectId);
  }, 2000);
  assessmentJobTimers.set(jobId, timerId);
};

const loadAssessmentJobsForProject = (projectId: string) => {
  const stored = localStorage.getItem(assessmentJobsKey(projectId));
  try {
    const parsed = stored ? JSON.parse(stored) : [];
    assessmentJobs.value = Array.isArray(parsed)
      ? parsed.filter((job) => job?.job_id && job?.lesson_id)
      : [];
  } catch (e) {
    assessmentJobs.value = [];
  }
  assessmentJobs.value.forEach((job) => scheduleAssessmentPoll(job.job_id, projectId));
};

const startRename = () => {
  if (!selectedProject.value) return;
  renameError.value = null;
  renameValue.value = selectedProject.value.agreed_project?.name || "";
  isRenaming.value = true;
};

const cancelRename = () => {
  isRenaming.value = false;
  renameError.value = null;
};

const saveRename = async () => {
  if (!selectedProject.value) return;
  const nextName = renameValue.value.trim();
  if (!nextName) {
    renameError.value = "Name cannot be empty";
    return;
  }
  renameError.value = null;
  try {
    const response = await renameProject(selectedProject.value.session_id, nextName);
    if (!selectedProject.value.agreed_project) {
      selectedProject.value.agreed_project = {
        name: response.name,
        description: "",
        timeline: "",
        milestones: [],
      };
    } else {
      selectedProject.value.agreed_project.name = response.name;
    }
    selectedProject.value.updated_at = response.updated_at || selectedProject.value.updated_at;
    projects.value = projects.value.map((project) =>
      project.id === selectedProject.value?.session_id
        ? { ...project, name: response.name }
        : project,
    );
    isRenaming.value = false;
  } catch (e) {
    renameError.value = "Failed to rename project";
  }
};

const saveProfile = async () => {
  if (!selectedProject.value) return;
  profileSaving.value = true;
  profileError.value = null;
  try {
    const interests = profileDraft.value.interestsText
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const response = await updateProjectProfile(selectedProject.value.session_id, {
      interests,
      skill_level: profileDraft.value.skill_level,
      time_available: profileDraft.value.time_available,
      learning_style: profileDraft.value.learning_style,
    });
    selectedProject.value.user_profile = response.user_profile;
    profileDraft.value.interests = interests;
  } catch (e) {
    profileError.value = "Failed to update profile";
  } finally {
    profileSaving.value = false;
  }
};

const openLesson = (lesson: ProjectLesson) => {
  selectedLesson.value = lesson;
  showAssessmentPanel.value = false;
};

const closeLesson = () => {
  selectedLesson.value = null;
  showAssessmentPanel.value = false;
};

const openAssessmentPanel = () => {
  showAssessmentPanel.value = true;
};

const closeAssessmentPanel = () => {
  showAssessmentPanel.value = false;
};

const generateAssessment = async (lessonId: string) => {
  if (!selectedProject.value) return;
  assessmentError.value = null;
  try {
    const response = await createProjectAssessment(selectedProject.value.session_id, lessonId);
    if (response.job_id) {
      assessmentJobs.value = [{ job_id: response.job_id, lesson_id: lessonId }, ...assessmentJobs.value];
      persistAssessmentJobs(selectedProject.value.session_id);
      scheduleAssessmentPoll(response.job_id, selectedProject.value.session_id);
      return;
    }
    assessmentError.value = "Assessment generation did not return a job id";
  } catch (e) {
    assessmentError.value = e instanceof Error ? e.message : "Failed to generate assessment";
  }
};

const submitAssessment = async (assessmentId: string) => {
  if (!selectedProject.value) return;
  assessmentError.value = null;
  const answer = assessmentAnswers.value[assessmentId] || "";
  if (!answer.trim()) {
    assessmentError.value = "Answer cannot be empty";
    return;
  }
  try {
    const response = await submitProjectAssessment(selectedProject.value.session_id, assessmentId, answer);
    assessments.value = assessments.value.map((assessment) =>
      assessment.id === assessmentId
        ? { ...assessment, status: response.result, feedback: response.feedback, archived: response.result === "pass" }
        : assessment,
    );
    if (response.result === "pass") {
      const passedAssessment = assessments.value.find((assessment) => assessment.id === assessmentId);
      if (passedAssessment) {
        lessons.value = lessons.value.map((lesson) =>
          lesson.id === passedAssessment.lesson_id ? { ...lesson, archived: true } : lesson,
        );
        if (selectedLesson.value?.id === passedAssessment.lesson_id) {
          selectedLesson.value = null;
          showAssessmentPanel.value = false;
        }
      }
    }
  } catch (e) {
    assessmentError.value = e instanceof Error ? e.message : "Failed to submit assessment";
  }
};

const assessmentStatusLabel = (status?: string) => {
  if (!status || status === "pending") return "Not taken";
  if (status === "pass") return "Passed";
  if (status === "fail") return "Failed";
  return status;
};

const lessonTitleById = (lessonId: string) => {
  const lesson = lessons.value.find((item) => item.id === lessonId);
  return lesson?.title || "Lesson";
};

const isAssessmentJobActive = (lessonId: string) => {
  return assessmentJobs.value.some((job) => job.lesson_id === lessonId);
};

const isDefaultProject = computed(() => selectedProject.value?.session_id === DEFAULT_PROJECT_ID);

const archiveLesson = async (lessonId: string) => {
  if (!selectedProject.value) return;
  await archiveProjectLesson(selectedProject.value.session_id, lessonId);
  lessons.value = lessons.value.map((lesson) =>
    lesson.id === lessonId ? { ...lesson, archived: true } : lesson,
  );
  if (selectedLesson.value?.id === lessonId) {
    selectedLesson.value = null;
    showAssessmentPanel.value = false;
  }
};

const removeLesson = async (lessonId: string) => {
  if (!selectedProject.value) return;
  if (!confirm("Remove this lesson? This cannot be undone.")) return;
  await deleteProjectLesson(selectedProject.value.session_id, lessonId);
  lessons.value = lessons.value.filter((lesson) => lesson.id !== lessonId);
  if (selectedLesson.value?.id === lessonId) {
    selectedLesson.value = null;
    showAssessmentPanel.value = false;
  }
};

const archiveAssessment = async (assessmentId: string) => {
  if (!selectedProject.value) return;
  await archiveProjectAssessment(selectedProject.value.session_id, assessmentId);
  assessments.value = assessments.value.map((assessment) =>
    assessment.id === assessmentId ? { ...assessment, archived: true } : assessment,
  );
};

const removeAssessment = async (assessmentId: string) => {
  if (!selectedProject.value) return;
  if (!confirm("Remove this assessment? This cannot be undone.")) return;
  await deleteProjectAssessment(selectedProject.value.session_id, assessmentId);
  assessments.value = assessments.value.filter((assessment) => assessment.id !== assessmentId);
};

const cancelAssessmentJob = async (jobId: string) => {
  if (!selectedProject.value) return;
  try {
    await cancelJob(jobId);
  } catch (e) {
    assessmentError.value = "Failed to cancel assessment generation";
  } finally {
    assessmentJobs.value = assessmentJobs.value.filter((job) => job.job_id !== jobId);
    persistAssessmentJobs(selectedProject.value.session_id);
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
  const isDefault = projectId === DEFAULT_PROJECT_ID;
  const message = isDefault
    ? "Clear the default project? This will remove its lessons and assessments."
    : "Delete this project and its chat history? This cannot be undone.";
  if (!confirm(message)) return;
  
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

const handleReinitializeProject = async () => {
  if (!selectedProject.value) return;
  isStarting.value = true;
  startError.value = null;
  try {
    const response = await startProject(selectedProject.value.session_id);
    if (response.status === "queued" && response.job_id) {
      reinitJobId.value = response.job_id;
      pollReinitJob();
      return;
    }
    applyReinitResult(response);
  } catch (e) {
    startError.value = e instanceof Error ? e.message : "Failed to reinitialize project";
  } finally {
    if (!reinitJobId.value) {
      isStarting.value = false;
    }
  }
};

const applyReinitResult = async (response: any) => {
  if (!selectedProject.value) return;
  if (response.user_profile) {
    const interests = response.user_profile.interests || [];
    selectedProject.value.user_profile = response.user_profile;
    profileDraft.value = {
      interests,
      interestsText: interests.join(", "),
      skill_level: response.user_profile.skill_level || "intermediate",
      time_available: response.user_profile.time_available || "2 hours/week",
      learning_style: response.user_profile.learning_style || "hybrid",
    };
  }
  if (response.project_status) {
    selectedProject.value.project_status = response.project_status;
  }
  if (response.started_at) {
    selectedProject.value.started_at = response.started_at;
  }
  startStats.value = {
    nodes: response.nodes_added ?? 0,
    relationships: response.relationships_added ?? 0,
  };
  localStorage.setItem("endstate_active_project_id", selectedProject.value.session_id);
  await loadProjectExtras(selectedProject.value.session_id);
};

const pollReinitJob = async () => {
  if (!reinitJobId.value || !selectedProject.value) return;
  if (reinitPollTimer) window.clearTimeout(reinitPollTimer);
  try {
    const status = await getJobStatus(reinitJobId.value);
    if (status.status === "completed" && status.result) {
      await applyReinitResult(status.result);
      reinitJobId.value = null;
      isStarting.value = false;
      return;
    }
    if (status.status === "failed") {
      startError.value = status.error || "Failed to reinitialize project";
      reinitJobId.value = null;
      isStarting.value = false;
      return;
    }
    if (status.status === "canceled") {
      startError.value = "Reinitialize canceled";
      reinitJobId.value = null;
      isStarting.value = false;
      return;
    }
  } catch (e) {
    startError.value = e instanceof Error ? e.message : "Failed to reinitialize project";
    reinitJobId.value = null;
    isStarting.value = false;
    return;
  }
  reinitPollTimer = window.setTimeout(pollReinitJob, 2000);
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

const handleLessonEvent = (event: CustomEvent) => {
  const projectId = event.detail?.projectId;
  if (selectedProject.value?.session_id === projectId) {
    loadProjectExtras(projectId);
  }
};

onMounted(() => {
  loadProjects();
  window.addEventListener("endstate:lesson-created", handleLessonEvent as EventListener);
  window.addEventListener("endstate:lesson-queued", handleLessonEvent as EventListener);
});

onUnmounted(() => {
  window.removeEventListener("endstate:lesson-created", handleLessonEvent as EventListener);
  window.removeEventListener("endstate:lesson-queued", handleLessonEvent as EventListener);
  clearAssessmentJobTimers();
  if (reinitPollTimer) window.clearTimeout(reinitPollTimer);
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
                <div class="flex items-start justify-between gap-4">
                  <div class="flex-1">
                    <div class="flex items-center gap-2 mb-2 opacity-90">
                      <Target :size="16" />
                      <span class="text-xs uppercase tracking-wider">Learning Project</span>
                    </div>
                    <div v-if="isRenaming" class="space-y-2">
                      <input
                        v-model="renameValue"
                        type="text"
                        class="px-3 py-2 rounded-md text-surface-800 text-sm w-full"
                        placeholder="Project name"
                      />
                      <p v-if="renameError" class="text-xs text-red-100">{{ renameError }}</p>
                    </div>
                    <h3 v-else class="text-2xl font-bold">{{ selectedProject.agreed_project?.name || 'Untitled Project' }}</h3>
                  </div>
                  <div class="flex gap-2">
                    <button
                      @click="handleReinitializeProject"
                      :disabled="isStarting || isDefaultProject"
                      class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/20 hover:bg-white/30 transition-colors text-xs disabled:opacity-60"
                      title="Reinitialize project"
                    >
                      <Play :size="16" />
                      <span>
                        {{ isDefaultProject ? 'Default' : (isStarting ? 'Reinitializing...' : 'Reinitialize') }}
                      </span>
                    </button>
                    <button
                      v-if="!isRenaming && !isDefaultProject"
                      @click="startRename"
                      class="p-2 rounded-lg bg-white/20 hover:bg-white/30 transition-colors"
                      title="Rename project"
                    >
                      <Pencil :size="18" />
                    </button>
                    <button
                      v-else
                      @click="saveRename"
                      class="p-2 rounded-lg bg-white/20 hover:bg-white/30 transition-colors"
                      title="Save name"
                    >
                      <Save :size="18" />
                    </button>
                    <button
                      v-if="isRenaming && !isDefaultProject"
                      @click="cancelRename"
                      class="p-2 rounded-lg bg-white/20 hover:bg-white/30 transition-colors"
                      title="Cancel rename"
                    >
                      <X :size="18" />
                    </button>
                    <button
                      @click="confirmDelete(selectedProject.session_id)"
                      class="p-2 rounded-lg bg-white/20 hover:bg-white/30 transition-colors"
                      title="Delete project"
                    >
                      <Trash2 :size="18" />
                    </button>
                  </div>
                </div>
                <p class="mt-3 text-primary-100 text-sm">{{ selectedProject.agreed_project?.description }}</p>
                <p v-if="startStats" class="mt-2 text-xs text-primary-100">
                  Added {{ startStats.nodes }} nodes · {{ startStats.relationships }} relationships
                </p>
                <p v-if="startError" class="mt-2 text-xs text-red-100">{{ startError }}</p>
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
              <div class="mt-4 border-t border-surface-100 pt-4">
                <p class="text-xs text-surface-400 mb-2">Update Profile</p>
                <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
                  <div class="md:col-span-2">
                    <label class="text-xs text-surface-500 mb-1 block">Interests (comma separated)</label>
                    <input
                      v-model="profileDraft.interestsText"
                      type="text"
                      class="w-full px-3 py-2 text-sm rounded-lg border border-surface-200"
                      placeholder="e.g. Python, Lambdas"
                    />
                  </div>
                  <div>
                    <label class="text-xs text-surface-500 mb-1 block">Skill Level</label>
                    <select v-model="profileDraft.skill_level" class="w-full px-3 py-2 text-sm rounded-lg border border-surface-200">
                      <option v-for="level in SKILL_LEVELS" :key="level" :value="level.toLowerCase()">
                        {{ level }}
                      </option>
                    </select>
                  </div>
                  <div>
                    <label class="text-xs text-surface-500 mb-1 block">Style</label>
                    <select v-model="profileDraft.learning_style" class="w-full px-3 py-2 text-sm rounded-lg border border-surface-200">
                      <option v-for="style in STYLE_OPTIONS" :key="style" :value="style.toLowerCase()">
                        {{ style }}
                      </option>
                    </select>
                  </div>
                  <div class="md:col-span-2">
                    <label class="text-xs text-surface-500 mb-1 block">Time / Week</label>
                    <select v-model="profileDraft.time_available" class="w-full px-3 py-2 text-sm rounded-lg border border-surface-200">
                      <option v-for="time in TIME_OPTIONS" :key="time" :value="time">
                        {{ time }}
                      </option>
                    </select>
                  </div>
                  <div class="md:col-span-2 flex items-end justify-end gap-3">
                    <p v-if="profileError" class="text-xs text-red-500">{{ profileError }}</p>
                    <button
                      @click="saveProfile"
                      :disabled="profileSaving"
                      class="px-4 py-2 text-sm rounded-lg bg-primary-600 text-white hover:bg-primary-700 transition-colors disabled:opacity-60"
                    >
                      {{ profileSaving ? 'Saving...' : 'Save Profile' }}
                    </button>
                  </div>
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

            <div class="bg-white rounded-xl shadow-sm border border-surface-200 p-6">
              <div class="flex items-center gap-2 mb-4">
                <MessageSquare :size="18" class="text-primary-500" />
                <h4 class="font-semibold text-surface-800">Lessons</h4>
              </div>
              <div v-if="lessonsLoading" class="text-sm text-surface-400">Loading lessons...</div>
              <div v-else-if="activeLessons.length === 0" class="text-sm text-surface-400">No lessons yet.</div>
              <div v-else class="space-y-3">
                <div
                  v-for="lesson in activeLessons"
                  :key="lesson.id"
                  class="w-full text-left p-3 bg-surface-50 rounded-lg hover:bg-surface-100 transition-colors"
                >
                  <div class="flex items-start justify-between gap-3">
                    <button @click="openLesson(lesson)" class="flex-1 text-left">
                      <p class="text-sm font-semibold text-surface-700">{{ lesson.title }}</p>
                      <div class="text-xs text-surface-500 mt-1 line-clamp-2 markdown-container" v-html="renderMarkdown(lesson.explanation)"></div>
                    </button>
                    <div class="flex flex-col gap-2">
                      <button
                        @click.stop="archiveLesson(lesson.id)"
                        class="text-xs px-2 py-1 rounded border border-surface-200 text-surface-600 hover:bg-surface-100"
                      >
                        Archive
                      </button>
                      <button
                        @click.stop="removeLesson(lesson.id)"
                        class="text-xs px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="selectedLesson" class="bg-white rounded-xl shadow-sm border border-surface-200 p-6">
              <div class="flex items-center justify-between mb-4">
                <h4 class="font-semibold text-surface-800">{{ selectedLesson.title }}</h4>
                <div class="flex items-center gap-2">
                  <button
                    @click="archiveLesson(selectedLesson.id)"
                    class="text-xs px-2 py-1 rounded border border-surface-200 text-surface-600 hover:bg-surface-100"
                  >
                    Archive
                  </button>
                  <button
                    @click="removeLesson(selectedLesson.id)"
                    class="text-xs px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50"
                  >
                    Remove
                  </button>
                  <button
                    @click="closeLesson"
                    class="text-xs text-surface-500 hover:text-surface-700"
                  >
                    Close
                  </button>
                </div>
              </div>
              <div class="text-sm text-surface-700 mb-3 markdown-container" v-html="renderMarkdown(selectedLesson.explanation)"></div>
              <div v-if="selectedLesson.task" class="text-sm text-surface-600 mb-4 markdown-container" v-html="renderMarkdown(selectedLesson.task)"></div>
              <button
                @click="openAssessmentPanel"
                class="text-xs px-3 py-1.5 rounded-lg bg-primary-600 text-white hover:bg-primary-700 transition-colors"
              >
                Open task
              </button>
              <div v-if="showAssessmentPanel" class="mt-4 p-3 bg-surface-50 rounded-lg">
                <div class="flex items-center justify-between mb-2">
                  <p class="text-xs font-semibold text-surface-600">Assessment</p>
                  <button @click="closeAssessmentPanel" class="text-xs text-surface-500 hover:text-surface-700">
                    Back
                  </button>
                </div>
                <button
                  @click="generateAssessment(selectedLesson.id)"
                  :disabled="isAssessmentJobActive(selectedLesson.id)"
                  class="text-xs px-3 py-1.5 rounded-lg bg-primary-100 text-primary-700 hover:bg-primary-200 transition-colors"
                >
                  {{ isAssessmentJobActive(selectedLesson.id) ? 'Generating...' : 'Generate assessment' }}
                </button>
                <p v-if="isAssessmentJobActive(selectedLesson.id)" class="mt-2 text-xs text-surface-500">
                  Assessment generation in progress. You can continue browsing.
                </p>
              </div>
            </div>

            <div class="bg-white rounded-xl shadow-sm border border-surface-200 p-6">
              <div class="flex items-center gap-2 mb-4">
                <CheckCircle :size="18" class="text-emerald-500" />
                <h4 class="font-semibold text-surface-800">Assessments</h4>
              </div>
              <div v-if="assessmentsLoading" class="text-sm text-surface-400">Loading assessments...</div>
              <div v-else>
                <div v-if="activeAssessments.length === 0 && assessmentJobs.length === 0" class="text-sm text-surface-400">No assessments yet.</div>
                <div v-if="assessmentJobs.length > 0" class="mt-3 space-y-2">
                  <div v-for="job in assessmentJobs" :key="job.job_id" class="flex items-center justify-between text-xs text-surface-500 bg-surface-50 rounded-lg px-3 py-2">
                    <span>Generating assessment for {{ lessonTitleById(job.lesson_id) }}...</span>
                    <button
                      @click="cancelAssessmentJob(job.job_id)"
                      class="text-xs px-2 py-1 rounded border border-surface-200 text-surface-600 hover:bg-surface-100"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
                <div v-if="activeAssessments.length > 0" class="mt-3 space-y-4">
                  <div v-for="assessment in activeAssessments" :key="assessment.id" class="p-3 bg-surface-50 rounded-lg">
                    <p class="text-xs text-surface-400 mb-1">Lesson: {{ lessonTitleById(assessment.lesson_id) }}</p>
                    <div class="text-sm text-surface-700 markdown-container" v-html="renderMarkdown(assessment.prompt)"></div>
                    <p class="text-xs mt-2 text-surface-500">
                      Status: <span class="font-semibold">{{ assessmentStatusLabel(assessment.status) }}</span>
                    </p>
                    <div v-if="assessment.feedback" class="text-xs text-surface-600 mt-2 markdown-container" v-html="renderMarkdown(assessment.feedback)"></div>
                    <div class="mt-3">
                      <textarea
                        v-model="assessmentAnswers[assessment.id]"
                        rows="2"
                        class="w-full px-3 py-2 text-xs rounded-lg border border-surface-200"
                        placeholder="Write your answer here..."
                      ></textarea>
                      <div class="flex items-center justify-between mt-2">
                        <div class="flex items-center gap-2">
                          <button
                            @click="archiveAssessment(assessment.id)"
                            class="text-xs px-2 py-1 rounded border border-surface-200 text-surface-600 hover:bg-surface-100"
                          >
                            Archive
                          </button>
                          <button
                            @click="removeAssessment(assessment.id)"
                            class="text-xs px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50"
                          >
                            Remove
                          </button>
                        </div>
                        <button
                          @click="submitAssessment(assessment.id)"
                          class="text-xs px-3 py-1.5 rounded-lg bg-emerald-100 text-emerald-700 hover:bg-emerald-200 transition-colors"
                        >
                          Submit answer
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <p v-if="assessmentError" class="mt-2 text-xs text-red-500">{{ assessmentError }}</p>
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

            <div v-if="selectedProject" class="mt-4 space-y-4">
              <div class="bg-white rounded-xl shadow-sm border border-surface-200 p-6">
                <div class="flex items-center gap-2 mb-4">
                  <BookOpen :size="18" class="text-surface-500" />
                  <h4 class="font-semibold text-surface-800">Archived Lessons</h4>
                </div>
                <div v-if="archivedLessons.length === 0" class="text-sm text-surface-400">No archived lessons.</div>
                <div v-else class="space-y-3">
                  <div v-for="lesson in archivedLessons" :key="lesson.id" class="p-3 bg-surface-50 rounded-lg">
                    <div class="flex items-start justify-between gap-3">
                      <div>
                        <p class="text-sm font-semibold text-surface-700">{{ lesson.title }}</p>
                        <div class="text-xs text-surface-500 mt-1 line-clamp-2 markdown-container" v-html="renderMarkdown(lesson.explanation)"></div>
                      </div>
                      <button
                        @click="removeLesson(lesson.id)"
                        class="text-xs px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div class="bg-white rounded-xl shadow-sm border border-surface-200 p-6">
                <div class="flex items-center gap-2 mb-4">
                  <CheckCircle :size="18" class="text-surface-500" />
                  <h4 class="font-semibold text-surface-800">Archived Assessments</h4>
                </div>
                <div v-if="archivedAssessments.length === 0" class="text-sm text-surface-400">No archived assessments.</div>
                <div v-else class="space-y-3">
                  <div v-for="assessment in archivedAssessments" :key="assessment.id" class="p-3 bg-surface-50 rounded-lg">
                    <p class="text-xs text-surface-400 mb-1">Lesson: {{ lessonTitleById(assessment.lesson_id) }}</p>
                    <div class="text-sm text-surface-700 markdown-container" v-html="renderMarkdown(assessment.prompt)"></div>
                    <p class="text-xs mt-2 text-surface-500">
                      Status: <span class="font-semibold">{{ assessmentStatusLabel(assessment.status) }}</span>
                    </p>
                    <div v-if="assessment.feedback" class="text-xs text-surface-600 mt-2 markdown-container" v-html="renderMarkdown(assessment.feedback)"></div>
                    <div class="mt-3 flex justify-end">
                      <button
                        @click="removeAssessment(assessment.id)"
                        class="text-xs px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50"
                      >
                        Remove
                      </button>
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
