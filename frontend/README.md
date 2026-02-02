# Endstate Frontend

> ← Back to [Main README](../README.md)

Vue 3 + Tailwind CSS frontend with chat and interactive knowledge graph.

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Features

- **Collapsible Sidebar** - Smooth animations, responsive design
- **Tab System** - Switch between Chat, Knowledge Graph, and Projects
- **Chat Interface** - Socratic interviewer with "Suggest Projects" button
- **Interactive Knowledge Graph** - D3.js force-directed graph:
  - Data loaded from Neo4j database
  - Drag nodes to reposition
  - Zoom in/out with buttons or scroll
  - Click nodes for details
  - Search/filter functionality
- **Project Management** - View projects, lessons, assessments, and capstone submissions

## Controls

### Chat
- Type message and press Enter to send
- Click "Suggest Projects" to generate proposal cards
- Select a proposal to create a project or reject to keep chatting

### Knowledge Graph
- Drag nodes to move them
- Scroll to zoom in/out
- Click nodes to see details
- Use search to filter nodes
- Zoom and refresh buttons in top-right corner

### Projects
- Click a project to view details
- Generate lessons for knowledge graph nodes
- Complete assessments to progress
- Submit capstone work for evaluation

## Tech Stack

- Vue 3 (Composition API)
- TypeScript
- Tailwind CSS
- D3.js (graph visualization)
- Vite (build tool)
- Lucide (icons)
