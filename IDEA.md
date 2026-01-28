# Endstate

**The Agentic Learning Architect**: Transform vague goals into executable skill graphs and adaptive projects.

## Vision

Endstate is a learning platform that transforms nebulous learning goals into concrete, structured learning paths. Instead of drowning in disconnected tutorials, learners get:

1. **Socratic Clarification** - Chat-based interviewer narrows vague goals into concrete capability statements
2. **Knowledge Graph Architecture** - Skills decomposed into a dependency graph (DAG) stored in Neo4j
3. **Adaptive Learning** - Dynamic lessons and assessments that adjust based on performance

> **Current Implementation**: Two-stage flow (Socratic interviewer → explicit "Suggest Projects" action). Opik tracing is disabled.

## The Problem

Most learning resolutions fail because of:

- **Vagueness** - "Learn Python" isn't a plan, it's a wish
- **Content Overload** - Disconnected tutorials without clear dependencies
- **Lack of Application** - Passive watching doesn't lead to mastery

## The Solution

**Endstate** guides learners through a structured transformation:

1. **Interrogate & Clarify** - Socratic dialogue narrows goals into verifiable capability targets
2. **Architect the Path** - Generate a Skill Dependency Graph showing prerequisite relationships
3. **Teach & Adapt** - Dynamic micro-lessons with continuous performance monitoring

## Current Flow

- **🧠 Interviewer (Chat)** - Socratic dialogue to clarify goals and constraints
- **🧠 Architect (Suggest Projects)** - Generates 3 project options from chat transcript
- **🎓 Lesson Generator** - Creates focused lessons for knowledge graph nodes
- **⚖️ Evaluator** - Rubric-based capstone evaluation with iterative feedback

## Tech Stack

- **Backend** - FastAPI + async task registry
- **LLMs** - Gemini 2.5 Flash or Llama 3 (local)
- **Database** - Neo4j for skill graph and dependency management
- **Frontend** - Vue 3 + TypeScript + Tailwind CSS with D3.js graph visualization
- **Deployment** - Docker containers, Vercel frontend

## Track

**Personal Growth & Learning**
