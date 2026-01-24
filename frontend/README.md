# Endstate Frontend

A sleek, modern Vue 3 + Tailwind CSS frontend demo with chat and interactive knowledge graph.

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Features

- **Collapsible Sidebar** - Smooth animations, responsive design. Click sidebar items to navigate.
- **Tab System** - Switch between Chat and Knowledge Graph views (header tabs or sidebar)
- **Chat Interface** - Socratic interviewer plus “Suggest Projects” proposals
- **Interactive Knowledge Graph** - D3.js force-directed graph with:
  - Data loaded from Neo4j database
  - Drag nodes to reposition
  - Zoom in/out with buttons or scroll
  - Click nodes for details
  - Search/filter functionality

## Controls

### Sidebar
- Click the chevron icon to collapse/expand
- Click menu items to navigate between Chat and Knowledge Graph

### Chat
- Type message and press Enter to send
- Shift+Enter for new line
- Click “Suggest Projects” to generate proposal cards
- Select a proposal to create a project or reject to keep chatting

### Knowledge Graph
- Data loaded from Neo4j database via backend API
- Drag nodes to move them
- Scroll to zoom in/out
- Click nodes to see details
- Use search to filter nodes
- Zoom buttons in top-right corner
- Refresh button to reload data from database

## Tech Stack

- Vue 3 (Composition API)
- TypeScript
- Tailwind CSS
- D3.js (graph visualization)
- Vite (build tool)
- Lucide (icons)
