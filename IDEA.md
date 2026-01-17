### **Project Name**

**Endstate**

### **Tagline**

The Agentic Learning Architect: Transforming vague goals into executable skill graphs and adaptive projects.

### **The Problem**

Most New Year's resolutions to "learn a new skill" fail for three critical reasons that current educational platforms fail to address:

1. **Vagueness:** "Learn Python" is not a plan; it's a wish. Without a concrete definition of what "learned" looks like, learners have no way to measure progress or know when they've succeeded. Traditional course platforms treat all content as equally important, providing no guidance on what truly matters versus what's peripheral knowledge.

2. **Content Overload:** Learners drown in disconnected tutorials without understanding the dependencies between concepts. A user searching "how to build AI agents" faces thousands of hours of video content, blog posts, and documentation—each treating topics in isolation. There's no clear map showing that understanding authentication is prerequisite to calling APIs, which is prerequisite to building agent toolchains.

3. **Lack of Application:** Passive watching doesn't lead to mastery; building does. Studies in cognitive science consistently show that passive consumption has one of the lowest retention rates of any learning method. Yet most platforms reward "hours watched" rather than "skills demonstrated," creating an illusion of progress without actual capability acquisition.

### **The Solution**

**Endstate** is not a chatbot; it is a learning architect. It moves beyond "chatting about a topic" to architecting a complete learning path from a nebulous goal to tangible competence.

Users start with a vague goal (e.g., "I want to build AI agents"). Endstate employs a multi-agent system to guide them through a structured transformation:

1. **Interrogate & Clarify:** Through Socratic dialogue, the Negotiator Agent narrows the goal into a concrete Capability Statement. This isn't just clarifying "Python" versus "JavaScript"—it means defining exactly what the user wants to build, for whom, and under what constraints. The output is a verifiable capability target (e.g., "Build an autonomous research assistant that can query APIs, synthesize findings, and produce markdown reports").

2. **Architect the Path:** The Graph Generator Agent decomposes the target capability into a **Skill Dependency Graph (DAG)** stored in Neo4j. This graph explicitly models prerequisite relationships: you cannot understand async/await until you understand promises, you cannot use API authentication until you understand HTTP headers, you cannot build multi-agent systems until you understand agent communication protocols. The graph is rooted in a specific, user-chosen Capstone Project that serves as the north star.

3. **Teach & Adapt:** The Lesson Agent dynamically generates micro-lessons for each node in the graph—short, focused content chunks that combine conceptual explanation with immediate practice. The Evaluator Agent continuously monitors user performance. If a user fails to demonstrate mastery of a prerequisite concept, the system detects this friction point and inserts remedial nodes into the learning path, restructuring the graph in real-time.

### **How It Works (Agent Architecture)**

Endstate uses **LangGraph** to orchestrate a deterministic flow between specialized agents, with clear state boundaries and well-defined communication protocols:

* **🧠 Synthesizer Agent:** This agent serves as the entry point and goal clarifier. It conducts a structured interview to extract the user's true objective—moving beyond surface-level wishes to uncover the underlying capability they want to possess. It outputs a detailed Capability Statement that includes: the target deliverable, success criteria, assumed prior knowledge, and estimated timeline. This agent negotiates the "Capstone Project" with the user to ensure learning is outcome-based and measurable.

* **🕸️ Skill Graph Agent:** Given a Capability Statement, this agent decomposes the target into atomic skill nodes and their dependency relationships. It generates a Neo4j Knowledge Graph where edges represent prerequisite relationships (e.g., "understanding_functions" → "depends_on" → "understanding_variables"). The graph is validated for cycles, completeness gaps, and topological ordering before being presented to the user. This agent strictly maps dependencies so the learning path respects the natural knowledge hierarchy.

* **🎓 Lesson Generator:** A creative agent that spawns multi-modal content on demand for currently active nodes in the graph. For each skill node, it generates: a conceptual explanation with analogies, a interactive quiz with auto-grading, and a hands-on code task that demonstrates the concept. Content is generated fresh each time, allowing for personalized examples (e.g., using the user's domain of interest in code samples). This agent ensures no two learning experiences are exactly alike while maintaining pedagogical quality.

* **⚖️ The Evaluator (Judge):** This agent monitors user performance across all interactions—quiz responses, code task outputs, and conversational demonstrations. It maintains a "mastery score" for each node and implements adaptive thresholds. If error rates spike beyond a configured tolerance, or if the user explicitly requests help, the Evaluator pauses graph traversal and inserts remedial nodes. Critically, it also identifies when users are ready to advance, allowing accelerated progression through mastered material. It decides when to "slow down" for fundamentals versus "skip ahead" to new challenges.

### **Tech Stack**

* **Orchestration:** LangGraph (Python) for stateful multi-agent orchestration with checkpointing, human-in-the-loop breakpoints, and deterministic state transitions.
* **LLMs:** Hybrid approach using **Gemini 1.5 Flash** for high-volume reasoning, planning, and graph generation tasks where latency matters, combined with **Llama 3** (local/quantized) for content generation where cost efficiency and privacy are priorities.
* **Database:** **Neo4j** for storing the Skill Graph, managing dependency traversals, and enabling graph algorithms for pathfinding and prerequisite resolution.
* **Frontend:** Vue 3 + TypeScript + Tailwind CSS for visualizing the interactive Learning Graph with D3.js integration for force-directed graph rendering.
* **Observability:** **Opik** for comprehensive tracing, evaluation logging, and agent trajectory analysis.
* **Deployment:** Docker containers with FastAPI backend and Vercel frontend deployment.

### **Integration with Opik (Observability)**

We are competing for the **Best Use of Opik** prize by integrating it deeply into the core logic loop—not as an afterthought, but as a fundamental component of our agent architecture:

1. **Graph Validity Metrics:** We log the "Hallucination Rate" of the Skill Graph Agent by validating generated dependencies against a ground-truth dataset of verified skill relationships. Each edge in the generated graph is scored for plausibility, and patterns of low-confidence edges are flagged for review. This allows us to measure and improve the reliability of our graph generation over time.

2. **Lesson Quality Eval:** We use LLM-as-a-Judge to score generated lessons on multiple dimensions before showing them to the user: clarity, relevance to the target skill, accuracy of examples, and difficulty calibration. Lessons that fall below quality thresholds are regenerated. This creates a feedback loop that continuously improves content quality based on objective metrics.

3. **Agent Trajectories:** Every decision made by the Evaluator Agent is traced with full context: what the user response was, what the mastery scores were at that moment, what alternatives were considered, and why a specific action was chosen. These traces are invaluable for debugging edge cases where the system chose to insert remedial content when the user felt ready to advance—or vice versa.

### **Track**

**Personal Growth & Learning**