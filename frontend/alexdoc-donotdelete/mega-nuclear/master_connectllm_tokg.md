# Agentic Architecting

## 1. The Core Objective: Agentic Architecting

The task required a real-time data pipeline where natural language intent is converted into a structured JSON graph schema.

The Connection ensures that when the AI proposes a learning path, such as Cooking Techniques or Frontend Core, the visualization layer dynamically expands without manual reload or session loss.

---

## 2. Technical Implementation: The Reactive Bridge

### A. Non-Destructive State Orchestration (App.vue)

The most significant change was moving the Source of Truth out of the visualization component.

#### The Problem
- \`v-if\` conditionally destroys components.
- Switching tabs previously unmounted the KnowledgeGraph.
- All newly discovered nodes were purged from memory.

#### The Fix (Persistence)
- Moved \`graphState\` to the parent App.vue.
- Switched ChatBox from \`v-if\` to \`v-show\`.
- The chat DOM is hidden but preserved.
- Graph state survives tab transitions.

#### The Fix (Collision)
- Added \`:key="graphState.nodes.length"\` to the graph container.
- Forces Vue Virtual DOM to re-initialize D3 only when node count changes.
- Prevents \`nextSibling is null\` crashes caused by D3 direct DOM mutations.

---

### B. Payload Interception and Sanitization (ChatBox.vue)

To maintain a clean UI while processing heavy JSON data, an Intercept and Clean pattern was implemented.

#### Regex Parsing
- Uses the regex:
  \`/<graph_update>([\\s\\S]*?)<\\/graph_update>/\`
- Isolates structured JSON from conversational LLM output.

#### UI Sanitization
- After emitting \`updateGraph\`, the raw tags are removed using \`.replace()\`.
- Prevents JSON and tags from rendering inside chat bubbles.

---

### C. D3.js Force Simulation Stabilization (KnowledgeGraph.vue)

Integrating D3 with Vue reactivity requires strict lifecycle control to avoid race conditions.

#### Immediate Watchers
- Implemented:
  \`watch(() => props.externalData, ..., { immediate: true })\`
- Solves initial load issues when chat-generated data must render instantly.

#### Selection Typing
- Resolved TypeScript errors related to \`Selection<BaseType>\`.
- Casted \`.call()\` to \`any\` to bypass D3 internal type mismatches.
- Ensures drag-and-drop behaviors work with SVGGElement.

---

## 3. The Black Node Resolution: Hybrid Mapping

A critical visual failure occurred when new domains like Cooking or Web Dev were introduced.

#### Legacy vs Dynamic Mapping
- Original demo nodes used numeric group IDs (1–5).
- LLM-generated nodes used string-based group names.

#### Unified Group Map
- Expanded \`groupColors\` to support both numeric and string keys.
- Preserves legacy colors like Machine Learning (ID: 1, Sky Blue).
- Enables new domains like Frontend Core to render with unique colors (Teal).

---

## 4. Current Architecture Overview

### System Layers and Responsibilities

- **Negotiator (ChatBox)**
  - Intent discovery
  - Prompt engineering
  - Regex-based payload extraction

- **Orchestrator (App.vue)**
  - Global data persistence
  - Centralized \`graphState\`
  - \`v-show\` based view switching

- **Visualizer (KnowledgeGraph)**
  - Real-time SVG rendering
  - D3 force simulation
  - Reactive prop watchers

---

## 5. Lessons Learned and Best Practices

- Always wrap D3-controlled SVGs in stable div containers when using Vue tab switching.
- Move state upward for any agentic workflow where one view generates data and another visualizes it.
- Safely reheat simulations using:
  \`simulation.value?.alpha(0.3).restart()\`
- Avoid full page reloads when introducing new nodes.