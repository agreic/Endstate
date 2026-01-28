<script setup lang="ts">
import { X, BookOpen, MessageSquare, Network, FolderOpen, Sparkles, Zap, CheckCircle } from 'lucide-vue-next';

defineProps<{
  isOpen: boolean
}>();

const emit = defineEmits<{
  close: []
}>();

const steps = [
  {
    icon: MessageSquare,
    title: '1. Start a Conversation',
    description: 'Tell the AI about your learning goals, interests, and what you want to achieve. The chat focuses on understanding your intent and constraints.'
  },
  {
    icon: Sparkles,
    title: '2. Receive Project Proposals',
    description: 'Click "Suggest Projects" to generate 2-3 focused project options based on the chat so far.'
  },
  {
    icon: CheckCircle,
    title: '3. Choose or Reject',
    description: 'Pick a proposal card to create a project, or reject all and continue chatting to refine ideas. After creating a project, you can view it in the Knowledge Graph or the Projects tab.'
  },
  {
    icon: FolderOpen,
    title: '4. Add More Skills & Topics',
    description: 'Go to the Projects tab, click on a project, and use "Generate Nodes" to add more skills, concepts, and topics to your learning path.'
  },
  {
    icon: Network,
    title: '5. Generate Lessons from the Knowledge Graph',
    description: 'In the Knowledge Graph view, click on any skill or topic node, then click "Generate Lesson" to create personalized learning content for that specific skill.'
  },
  {
    icon: BookOpen,
    title: '6. View Lessons & Create Assessments',
    description: 'Generated lessons appear in the Project Details section. Click on a lesson to view its content, and generate assessment tasks to test your understanding.'
  },
  {
    icon: Zap,
    title: '7. Capstone Mode - Final Evaluation',
    description: 'When you\'re ready, enter Capstone Mode for you final test. Submit your solution and receive AI-powered evaluation to determine if you\'ve mastered the skills. Pass to complete the project!'
  }
];

const handleBackdropClick = (e: MouseEvent) => {
  if (e.target === e.currentTarget) {
    emit('close');
  }
};
</script>

<template>
  <Teleport to="body">
    <div 
      v-if="isOpen"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto py-8"
      @click="handleBackdropClick"
    >
      <div class="bg-white dark:bg-surface-800 rounded-xl shadow-xl w-full max-w-2xl mx-4 overflow-hidden max-h-[90vh] flex flex-col">
        <div class="flex items-center justify-between p-4 border-b dark:border-surface-700 sticky top-0 bg-white dark:bg-surface-800">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
              <BookOpen :size="20" class="text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h2 class="text-lg font-semibold text-surface-900 dark:text-white">Welcome to Endstate</h2>
              <p class="text-sm text-surface-500 dark:text-surface-400">Your AI Learning Architect</p>
            </div>
          </div>
          <button 
            @click="emit('close')"
            class="p-1.5 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-700 text-surface-500 dark:text-surface-400"
          >
            <X :size="20" />
          </button>
        </div>
        
        <div class="p-6 overflow-y-auto">
          <p class="text-surface-600 dark:text-surface-300 mb-6 leading-relaxed">
            Endstate transforms your learning goals into actionable skill maps and concrete project plans. 
            Instead of generic advice, you get personalized learning roadmaps that adapt to your progress.
          </p>
          
          <div class="space-y-6">
            <h3 class="text-sm font-semibold text-surface-900 dark:text-white uppercase tracking-wider">How It Works</h3>
            
            <div class="space-y-4">
              <div 
                v-for="(step, index) in steps" 
                :key="index"
                class="flex gap-4"
              >
                <div class="flex-shrink-0 w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center mt-0.5">
                  <component :is="step.icon" :size="20" class="text-primary-600 dark:text-primary-400" />
                </div>
                <div class="flex-1">
                  <h4 class="text-sm font-medium text-surface-900 dark:text-white mb-1">{{ step.title }}</h4>
                  <p class="text-sm text-surface-600 dark:text-surface-400 leading-relaxed">{{ step.description }}</p>
                </div>
              </div>
            </div>
          </div>
          
          <div class="mt-8 p-4 bg-surface-50 dark:bg-surface-700/50 rounded-lg">
            <div class="flex items-start gap-3">
              <Zap :size="18" class="text-amber-500 mt-0.5 flex-shrink-0" />
              <div>
                <h4 class="text-sm font-medium text-surface-900 dark:text-white mb-1">Pro Tips</h4>
                <ul class="text-sm text-surface-600 dark:text-surface-400 space-y-1">
                  <li>• Be specific about your current skill level and time availability</li>
                  <li>• Use the Knowledge Graph to generate lessons for skills you want to focus on</li>
                  <li>• Complete assessment tasks before attempting the Capstone to ensure readiness</li>
                  <li>• You can resubmit Capstone solutions unlimited times until you pass</li>
                  <li>• Toggle dark mode in Settings for comfortable nighttime learning</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
        
        <div class="p-4 border-t dark:border-surface-700 bg-surface-50 dark:bg-surface-800/50 sticky bottom-0">
          <button 
            @click="emit('close')"
            class="w-full py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
          >
            Get Started
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
