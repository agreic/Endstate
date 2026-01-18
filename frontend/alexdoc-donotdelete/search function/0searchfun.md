# Project: Endstate AI – Web Search Integration

## Model Lock
**gemini-2.5-flash**

---

## Implementation Summary

* **Feature:** Integrated native Google Search grounding directly into the `ChatBox.vue` component.
* **Tooling:** Added `googleSearch` as a tool in the Gemini Generative Model configuration.
* **UI / UX:**
  * Added a **Search Mode** toggle with a globe icon.
  * Implemented **Source Chips** displaying the title and URL of web pages used to generate answers.
  * Added **v1beta API support** to access advanced search grounding metadata.
* **Logic:** Updated message handling to extract `groundingMetadata` and map it to a reactive `sources` array on each message object.

---

## Core Configuration (Locked)

* **Language:** TypeScript
* **Constraints:** Model downgrade is not permitted.

---

## Key Learnings

* **Grounding:** Gemini 2.5 Flash returns grounded results as discrete “chunks,” which must be filtered and de-duplicated to keep the UI clean.
* **Error Handling:** If search grounding fails, the system falls back to a helpful connection error message instead of crashing the chat.

---

## Next Level Upgrade Path

### 1. Smart Graph Injection (Endstate Specialty)

Automatically extract entities such as frameworks, concepts, or tools from search results and inject them as nodes into the Knowledge Graph.

* **Outcome:** The 3D knowledge graph grows in real time as the user chats.

---

### 2. Multi-Step Research (Agentic Search)

Upgrade from single-shot search to agentic reasoning where the AI performs multiple dependent searches to fully answer complex questions.

* **Outcome:** Deeper, more academic-quality responses.

---

### 3. Markdown Image and Chart Rendering

Leverage Gemini 2.5’s multimodal capabilities to include diagrams, images, or charts in responses.

* **Requirements:**
  * Extend markdown container CSS to support `<img>` tags.
  * Optionally integrate Mermaid.js for diagram rendering.
* **Outcome:** Visually richer explanations and research outputs.
