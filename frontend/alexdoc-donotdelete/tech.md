# Technical Documentation: Endstate Demo Architecture

## 1. Application Entry & Infrastructure

The project is scaffolded as a modern Vite 5 and Vue 3 application, optimized for rapid development and lean production builds.

- **Build Tooling:** Powered by Vite 5, utilizing native ESM for the development server and Rollup for efficient production bundling.
- **Initialization:** The `main.ts` entry point uses `createApp(App).mount('#app')` to bootstrap the root component, injecting global styles via Tailwind CSS.
- **Type Safety:** Integrated with TypeScript 5.3 and `vue-tsc`. A global `.d.ts` module shim provides type definitions for Single File Components (SFCs), ensuring full IDE support and compile time checking.

---

## 2. Core Framework & Styling

The UI layer prioritizes reactivity and performance through the latest Vue standards.

- **Vue 3 (Composition API):** Exclusively uses `<script setup>` syntax, reducing boilerplate, improving variable scoping, and enabling better compiler optimization.
- **Tailwind CSS 3.4:** Utility first styling with custom color tokens such as `surface` and `primary`. Arbitrary value support like `ml-[value]` enables fluid layout transitions during sidebar toggling.
- **Iconography:** Integrated with `lucide-vue-next` for consistent, lightweight SVG icons with tree shaking support.

---

## 3. Component Architecture & Routing

To maintain a lightweight demo footprint, the application avoids a formal router in favor of dynamic component mounting.

- **State Management:** Local reactive state using `ref` and `computed`, avoiding unnecessary global state overhead.
- **Navigation Logic:** View switching is controlled by an `activeTab` state. Components are conditionally rendered using `v-if`, ensuring resource heavy components such as D3 simulations or message histories only run when active.
- **Communication:** Strict one way data flow using props and custom emits. For example, the Sidebar emits a `Maps` event to update the parent component’s `activeTab`.

### View Breakdown

- **Dashboard.vue:** Aggregates metrics and high level activity logs.
- **ChatBox.vue:** Conversational interface managing message arrays and UI feedback.
- **KnowledgeGraph.vue:** Specialized container for D3 driven data visualization.

---

## 4. Knowledge Graph Engine (D3.js Integration)

The graph implementation bridges Vue’s reactive DOM with D3’s imperative manipulation model.

### Simulation Physics

Implemented using `d3.forceSimulation` with the following forces:

- **forceLink:** Manages connectivity with a 120px target distance.
- **forceManyBody:** Applies a -400 strength charge to ensure nodes maintain visual separation.
- **forceCollide:** A 50px collision radius prevents overlapping and preserves label readability.

### Interaction Layer

- **Drag and Drop:** Implemented via `d3.drag`, updating `fx` and `fy` to pause simulation physics on the active node.
- **Zoom and Pan:** Implemented with `d3.zoom`, supporting a scale range from 0.3x to 4x.
- **Real time Filtering:** Predicate based filtering using `isNodeMatching` updates SVG attributes such as opacity and stroke directly, avoiding re execution of the force simulation.

---

## 5. Messaging & UI Logic

Advanced Vue features manage complex UI states and simulate real world behavior.

- **Asynchronous DOM Updates:** The chat interface uses `nextTick` to ensure `scrollTop` calculations occur only after new message nodes are rendered.
- **Network Simulation:** Mock AI latency is implemented with a Promise based wrapper around `setTimeout`, enabling realistic testing of loading states and animations.
- **Reactive Synchronization:** A `watch` on the `searchQuery` state triggers localized restyling within the D3 SVG, keeping the visualization synchronized without a full component remount.

---

## 6. Dependency Manifest

- **vue (3.4.0):** Core reactive framework.
- **d3 (7.8.5):** Mathematical engine for force directed layouts and SVG calculations.
- **lucide-vue-next (0.294.0):** Icon system.
- **vite (5.0.10):** Development and build orchestration.
- **typescript (5.3.3):** Static typing.
- **tailwindcss (3.4.0):** PostCSS based utility styling.