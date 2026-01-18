<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from "vue";
import * as d3 from "d3";
import { 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  Search, 
  Database, 
  FileText, 
  Loader2 
} from "lucide-vue-next";
import { fetchGraphData, fetchGraphStats, type ApiNode, type ApiRelationship } from "../services/api";

// --- Props for LLM-generated data / External discovery ---
const props = defineProps<{
  externalData?: { nodes: any[]; links: any[] };
}>();

// --- Comprehensive Interfaces ---
interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  group: string | number;
  label: string;
  description?: string;
  labels?: string[];
  properties?: Record<string, any>;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
  value: number;
  label?: string;
  type?: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

// --- Reactive State ---
const graphContainer = ref<HTMLElement | null>(null);
const svgRef = ref<SVGSVGElement | null>(null);
const selectedNode = ref<GraphNode | null>(null);
const searchQuery = ref("");
const zoomLevel = ref(1);
const hoveredNodeId = ref<string | null>(null);
const dataSource = ref<'demo' | 'database'>('demo');
const isLoading = ref(false);
const loadError = ref<string | null>(null);
const graphStats = ref<{ total_nodes: number; total_relationships: number } | null>(null);
const graphData = ref<GraphData>({ nodes: [], links: [] });

// --- Color Definitions (Merged from all versions) ---
const groupColors: Record<string | number, string> = {
  // Demo ML Categories
  1: "#0ea5e9", // Core AI
  2: "#8b5cf6", // Frameworks
  3: "#10b981", // Applications
  4: "#f59e0b", // LLMs
  5: "#ef4444", // Data
  "Core AI": "#0ea5e9",
  "Frameworks": "#8b5cf6",
  "Applications": "#10b981",
  "LLMs": "#f59e0b",
  "Data": "#ef4444",
  
  // Database Labels
  'Skill': "#0ea5e9",
  'Concept': "#8b5cf6",
  'Topic': "#10b981",
  'Project': "#f59e0b",
  'Resource': "#ef4444",
  'Tool': "#ec4899",
  'Person': "#6366f1",
  'Domain': "#14b8a6",
  'Assessment': "#f97316",
  'Milestone': "#84cc16",

  // LLM Discovery Specific Categories
  "Cooking Basics": "#f472b6",
  "Techniques": "#fb7185",
  "Frontend Core": "#2dd4bf",
};

// --- Static Demo Data (Restored exactly) ---
const demoGraphData: GraphData = {
  nodes: [
    { id: "1", group: 1, label: "Machine Learning", description: "Field of AI that enables systems to learn" },
    { id: "2", group: 1, label: "Deep Learning", description: "Subset of ML using neural networks" },
    { id: "3", group: 1, label: "Neural Networks", description: "Computing systems inspired by biological brains" },
    { id: "4", group: 2, label: "Python", description: "Programming language popular in AI" },
    { id: "5", group: 2, label: "TensorFlow", description: "Open source ML framework by Google" },
    { id: "6", group: 2, label: "PyTorch", description: "Open source ML framework by Meta" },
    { id: "7", group: 3, label: "Computer Vision", description: "Enabling computers to see and understand images" },
    { id: "8", group: 3, label: "NLP", description: "Processing human language by computers" },
    { id: "9", group: 3, label: "Speech Recognition", description: "Converting spoken words to text" },
    { id: "10", group: 4, label: "GPT", description: "Generative Pre-trained Transformer models" },
    { id: "11", group: 4, label: "BERT", description: "Bidirectional Encoder Representations" },
    { id: "12", group: 4, label: "Transformer", description: "Architecture using attention mechanism" },
    { id: "13", group: 1, label: "Reinforcement Learning", description: "Learning through rewards and punishments" },
    { id: "14", group: 5, label: "Data Science", description: "Extracting insights from data" },
    { id: "15", group: 5, label: "Analytics", description: "Analyzing data for decisions" },
  ],
  links: [
    { source: "1", target: "2", value: 3, label: "includes" },
    { source: "2", target: "3", value: 3, label: "uses" },
    { source: "1", target: "13", value: 2, label: "includes" },
    { source: "3", target: "7", value: 2, label: "enables" },
    { source: "3", target: "8", value: 2, label: "enables" },
    { source: "3", target: "9", value: 2, label: "enables" },
    { source: "2", target: "5", value: 2, label: "implemented in" },
    { source: "2", target: "6", value: 2, label: "implemented in" },
    { source: "4", target: "5", value: 2, label: "primary language" },
    { source: "4", target: "6", value: 2, label: "primary language" },
    { source: "12", target: "10", value: 3, label: "architecture" },
    { source: "12", target: "11", value: 3, label: "architecture" },
    { source: "8", target: "10", value: 2, label: "powers" },
    { source: "8", target: "11", value: 2, label: "powers" },
    { source: "1", target: "14", value: 2, label: "part of" },
    { source: "14", target: "15", value: 2, label: "includes" },
    { source: "7", target: "12", value: 1, label: "uses" },
  ],
};

// --- D3 References ---
let simulation: d3.Simulation<GraphNode, GraphLink> | null = null;
let svgElement: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null;
let gElement: d3.Selection<SVGGElement, unknown, null, undefined> | null = null;
let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;
let nodesSelection: d3.Selection<any, GraphNode, any, any> | null = null;
let linksSelection: d3.Selection<any, GraphLink, any, any> | null = null;

// --- Helper Functions ---
const getNodeColor = (node: GraphNode): string => {
  if (dataSource.value === 'demo') {
    return groupColors[node.group] || groupColors[1];
  }
  return groupColors[node.labels?.[0] || 'Skill'] || groupColors['Skill'];
};

const formatPropertyValue = (value: any): string => {
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value);
  }
  return String(value);
};

const getConnectionCount = (nodeId: string): number => {
  return graphData.value.links.filter((l) => {
    const sourceId = typeof l.source === "string" ? l.source : (l.source as GraphNode).id;
    const targetId = typeof l.target === "string" ? l.target : (l.target as GraphNode).id;
    return sourceId === nodeId || targetId === nodeId;
  }).length;
};

// --- Data Loading Logic ---
const loadFromDatabase = async () => {
  dataSource.value = 'database';
  isLoading.value = true;
  loadError.value = null;
  
  try {
    const data = await fetchGraphData();
    
    if (data.total_nodes === 0) {
      loadError.value = "No data found in database. Add some content first!";
      isLoading.value = false;
      return;
    }
    
    graphStats.value = {
      total_nodes: data.total_nodes,
      total_relationships: data.total_relationships,
    };
    
    const mappedNodes = data.nodes.map((item: ApiNode) => {
      const nodeData = item.node;
      return {
        id: nodeData.id || String(Math.random()),
        group: nodeData.labels?.[0] || 'Skill',
        label: nodeData.name || nodeData.labels?.[0] || 'Unknown',
        description: nodeData.description,
        labels: nodeData.labels,
        properties: nodeData,
      };
    });
    
    const mappedLinks = data.relationships.map((rel: ApiRelationship) => ({
      source: rel.source,
      target: rel.target,
      value: 1,
      type: rel.type,
      label: rel.type,
    }));

    graphData.value = { nodes: mappedNodes, links: mappedLinks };
    
    setTimeout(() => {
      initGraph();
      isLoading.value = false;
    }, 100);
    
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Failed to load graph data';
    isLoading.value = false;
  }
};

const loadDemoData = () => {
  dataSource.value = 'demo';
  loadError.value = null;
  
  // Merge Demo Data with External Props if available
  const mergedNodes = [...demoGraphData.nodes];
  const mergedLinks = [...demoGraphData.links];

  if (props.externalData) {
    props.externalData.nodes.forEach((n) => {
      if (!mergedNodes.find((existing) => existing.id === n.id)) {
        mergedNodes.push(n);
      }
    });
    props.externalData.links.forEach((l) => mergedLinks.push(l));
  }

  graphData.value = { nodes: mergedNodes, links: mergedLinks };
  graphStats.value = null;
  
  setTimeout(() => {
    initGraph();
  }, 50);
};

// --- Styling and Search Filters ---
const isNodeMatching = (node: GraphNode): boolean => {
  if (!searchQuery.value) return true;
  const query = searchQuery.value.toLowerCase();
  return (
    node.label.toLowerCase().includes(query) ||
    node.description?.toLowerCase().includes(query) ||
    node.id === query ||
    (node.labels && node.labels.some(l => l.toLowerCase().includes(query)))
  );
};

const isLinkMatching = (link: GraphLink): boolean => {
  if (!searchQuery.value) return true;
  const sourceNode = link.source as GraphNode;
  const targetNode = link.target as GraphNode;
  if (!sourceNode || !targetNode) return false;
  return isNodeMatching(sourceNode) && isNodeMatching(targetNode);
};

const updateStyles = () => {
  if (!nodesSelection || !linksSelection) return;

  const query = searchQuery.value.toLowerCase();

  nodesSelection.selectAll("circle")
    .attr("fill", (d: GraphNode) => {
      const isMatch = isNodeMatching(d);
      const isHovered = hoveredNodeId.value === d.id;
      const baseColor = getNodeColor(d);
      if (!isMatch) return "#d4d4d8";
      if (isHovered) return d3.color(baseColor)?.brighter(0.3)?.toString() || baseColor;
      return baseColor;
    })
    .attr("opacity", (d: GraphNode) => {
      const matchesSearch = !query || d.label.toLowerCase().includes(query);
      const isDimmed = (hoveredNodeId.value && hoveredNodeId.value !== d.id) || !matchesSearch;
      return isDimmed ? 0.2 : 1;
    })
    .attr("stroke", (d: GraphNode) => (hoveredNodeId.value === d.id ? "#1e40af" : "#fff"))
    .attr("stroke-width", (d: GraphNode) => (hoveredNodeId.value === d.id ? 3 : 2));

  nodesSelection.selectAll("text")
    .attr("opacity", (d: GraphNode) => isNodeMatching(d) ? 1 : 0.3)
    .attr("font-weight", (d: GraphNode) => (hoveredNodeId.value === d.id ? "700" : "500"));

  linksSelection
    .attr("opacity", (d: GraphLink) => isLinkMatching(d) ? 0.6 : 0.1)
    .attr("stroke", (d: GraphLink) => isLinkMatching(d) ? "#d4d4d8" : "#e4e4e7");
};

watch(searchQuery, updateStyles);

// --- Core D3 Implementation ---
const initGraph = () => {
  if (!graphContainer.value || !svgRef.value) return;

  const width = graphContainer.value.clientWidth;
  const height = graphContainer.value.clientHeight;
  if (width === 0 || height === 0) return;

  svgElement = d3.select(svgRef.value);
  svgElement.selectAll("*").remove();
  gElement = svgElement.append("g");

  zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.1, 4])
    .on("zoom", (event) => {
      gElement?.attr("transform", event.transform);
      zoomLevel.value = event.transform.k;
    });

  svgElement.call(zoomBehavior).on("dblclick.zoom", null);

  const nodes: GraphNode[] = graphData.value.nodes.map((d) => ({
    ...d,
    fx: null,
    fy: null,
  }));
  const links: GraphLink[] = graphData.value.links.map((d) => ({ ...d }));

  // Link ID mapping
  links.forEach((link) => {
    link.source = nodes.find(n => n.id === (typeof link.source === "string" ? link.source : (link.source as any).id)) || link.source;
    link.target = nodes.find(n => n.id === (typeof link.target === "string" ? link.target : (link.target as any).id)) || link.target;
  });

  simulation = d3.forceSimulation<GraphNode>(nodes)
    .force("link", d3.forceLink<GraphNode, GraphLink>(links).id((d) => d.id).distance(140))
    .force("charge", d3.forceManyBody().strength(-500))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(60));

  linksSelection = gElement.append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", "#e2e8f0")
    .attr("stroke-opacity", 0.6)
    .attr("stroke-width", (d) => (d.value || 1) * 1.5);

  nodesSelection = gElement.append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .style("cursor", "grab")
    .call(
      d3.drag<any, GraphNode>()
        .on("start", (event, d) => {
          if (!event.active) simulation?.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation?.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
    )
    .on("mouseenter", (event, d) => {
      hoveredNodeId.value = d.id;
      updateStyles();
    })
    .on("mouseleave", () => {
      hoveredNodeId.value = null;
      updateStyles();
    })
    .on("click", (event, d) => {
      selectedNode.value = d;
      event.stopPropagation();
    });

  nodesSelection.append("circle")
    .attr("r", 22)
    .attr("fill", (d) => getNodeColor(d))
    .attr("stroke", "#fff")
    .attr("stroke-width", 3)
    .style("filter", "drop-shadow(0 4px 6px rgba(0,0,0,0.1))");

  nodesSelection.append("text")
    .text((d) => d.label)
    .attr("x", 28)
    .attr("y", 5)
    .attr("fill", "#1e293b")
    .style("font-size", "13px")
    .style("font-weight", "600")
    .style("pointer-events", "none");

  svgElement.on("click", () => {
    selectedNode.value = null;
  });

  simulation.on("tick", () => {
    linksSelection
      ?.attr("x1", (d) => (d.source as any).x)
      .attr("y1", (d) => (d.source as any).y)
      .attr("x2", (d) => (d.target as any).x)
      .attr("y2", (d) => (d.target as any).y);
    nodesSelection?.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });
};

// --- View Control Functions ---
const zoomIn = () => {
  if (svgElement && zoomBehavior) {
    svgElement.transition().duration(300).call(zoomBehavior.scaleBy, 1.3);
  }
};

const zoomOut = () => {
  if (svgElement && zoomBehavior) {
    svgElement.transition().duration(300).call(zoomBehavior.scaleBy, 0.7);
  }
};

const resetZoom = () => {
  if (svgElement && zoomBehavior) {
    svgElement.transition().duration(500).call(zoomBehavior.transform, d3.zoomIdentity);
  }
  if (simulation) simulation.alpha(0.3).restart();
};

const clearSearch = () => {
  searchQuery.value = "";
};

// --- Lifecycle Hooks ---
watch(
  () => props.externalData,
  () => {
    if (dataSource.value === 'demo') {
      loadDemoData();
    }
  },
  { deep: true }
);

onMounted(() => {
  loadDemoData();
  window.addEventListener("resize", initGraph);
});

onUnmounted(() => {
  window.removeEventListener("resize", initGraph);
  if (simulation) simulation.stop();
});

// --- Computed Stats & Legend ---
const totalNodesCount = computed(() => {
  if (graphStats.value) return graphStats.value.total_nodes;
  return graphData.value.nodes.length;
});

const totalLinksCount = computed(() => {
  if (graphStats.value) return graphStats.value.total_relationships;
  return graphData.value.links.length;
});

const legendItems = computed(() => {
  if (dataSource.value === 'demo') {
    return ['Core AI', 'Frameworks', 'Applications', 'LLMs', 'Data'];
  }
  const labels = new Set(graphData.value.nodes.map(n => n.labels?.[0] || 'Skill'));
  return Array.from(labels).sort();
});
</script>

<template>
  <div class="flex h-full bg-slate-50 overflow-hidden font-sans">
    <div class="flex-1 relative" ref="graphContainer">
      <svg ref="svgRef" class="w-full h-full block bg-slate-50"></svg>

      <div 
        class="absolute top-6 left-6 bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-5 z-10 w-80 border border-white"
      >
        <div class="flex items-center gap-3 mb-4 bg-slate-100 p-2.5 rounded-xl border border-slate-200 focus-within:border-primary-400 transition-all">
          <Search :size="18" class="text-slate-400" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search knowledge graph..."
            class="bg-transparent text-sm outline-none w-full font-medium text-slate-700"
          />
          <button v-if="searchQuery" @click="clearSearch" class="text-slate-400 hover:text-slate-600 font-bold">
            ×
          </button>
        </div>

        <div class="flex items-center gap-2 mb-5">
          <button
            @click="loadDemoData"
            class="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all border"
            :class="dataSource === 'demo' ? 'bg-primary-50 border-primary-200 text-primary-700 shadow-sm' : 'bg-white border-slate-100 text-slate-500 hover:bg-slate-50'"
          >
            <FileText :size="14" />
            Demo
          </button>
          <button
            @click="loadFromDatabase"
            :disabled="isLoading"
            class="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all border"
            :class="dataSource === 'database' ? 'bg-primary-50 border-primary-200 text-primary-700 shadow-sm' : 'bg-white border-slate-100 text-slate-500 hover:bg-slate-50'"
          >
            <Loader2 v-if="isLoading" :size="14" class="animate-spin" />
            <Database v-else :size="14" />
            Database
          </button>
        </div>

        <div v-if="loadError" class="p-2 mb-4 bg-red-50 border border-red-100 rounded-lg text-[11px] text-red-500 font-medium animate-pulse">
          {{ loadError }}
        </div>

        <div class="space-y-3 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
          <p class="text-[10px] uppercase tracking-widest text-slate-400 font-bold">
            Mapped Categories
          </p>
          <div v-for="label in legendItems" :key="label" class="flex items-center gap-3 group">
            <span
              class="w-3 h-3 rounded-full shadow-sm group-hover:scale-110 transition-transform"
              :style="{ backgroundColor: groupColors[label] || groupColors['Skill'] }"
            ></span>
            <span class="text-xs text-slate-600 font-semibold truncate">{{ label }}</span>
          </div>
        </div>

        <div class="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between">
          <p class="text-[11px] font-bold text-slate-400">
            {{ totalNodesCount }} Nodes / {{ totalLinksCount }} Links
          </p>
          <div v-if="searchQuery" class="text-[11px] text-primary-600 font-bold bg-primary-50 px-2 py-0.5 rounded-full">
            {{ graphData.nodes.filter(isNodeMatching).length }} matching
          </div>
        </div>
      </div>

      <div class="absolute top-6 right-6 flex flex-col gap-3 z-10">
        <button
          @click="zoomIn"
          class="p-3 bg-white/90 backdrop-blur-md rounded-2xl shadow-lg hover:bg-slate-50 transition-all border border-slate-100 group"
          title="Zoom In"
        >
          <ZoomIn :size="20" class="text-slate-600 group-hover:text-primary-600" />
        </button>
        <button
          @click="zoomOut"
          class="p-3 bg-white/90 backdrop-blur-md rounded-2xl shadow-lg hover:bg-slate-50 transition-all border border-slate-100 group"
          title="Zoom Out"
        >
          <ZoomOut :size="20" class="text-slate-600 group-hover:text-primary-600" />
        </button>
        <button
          @click="resetZoom"
          class="p-3 bg-white/90 backdrop-blur-md rounded-2xl shadow-lg hover:bg-slate-50 transition-all border border-slate-100 group"
          title="Reset View"
        >
          <Maximize2 :size="20" class="text-slate-600 group-hover:text-primary-600" />
        </button>
      </div>

      <Transition 
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="translate-y-10 opacity-0"
        enter-to-class="translate-y-0 opacity-100"
        leave-active-class="transition duration-200 ease-in"
        leave-from-class="translate-y-0 opacity-100"
        leave-to-class="translate-y-10 opacity-0"
      >
        <div
          v-if="selectedNode"
          class="absolute bottom-6 left-6 bg-white/95 backdrop-blur-md p-6 rounded-[2rem] shadow-2xl max-w-sm z-20 border border-slate-100"
        >
          <div class="flex items-center gap-4 mb-4">
            <div
              class="w-5 h-5 rounded-full shadow-inner ring-4 ring-slate-50"
              :style="{ backgroundColor: getNodeColor(selectedNode) }"
            ></div>
            <h3 class="font-extrabold text-xl text-slate-900 tracking-tight leading-none">
              {{ selectedNode.label }}
            </h3>
          </div>
          
          <div v-if="selectedNode.description" class="mb-5">
             <p class="text-sm text-slate-600 leading-relaxed font-medium italic">
              "{{ selectedNode.description }}"
            </p>
          </div>

          <div v-if="selectedNode.labels?.length" class="mb-4">
            <p class="text-[10px] uppercase tracking-tighter text-slate-400 font-bold mb-2">Node Type</p>
            <div class="flex flex-wrap gap-1.5">
              <span
                v-for="label in selectedNode.labels"
                :key="label"
                class="text-[11px] px-2.5 py-1 bg-slate-100 text-slate-600 rounded-lg font-bold border border-slate-200"
              >
                {{ label }}
              </span>
            </div>
          </div>

          <div v-if="selectedNode.properties && Object.keys(selectedNode.properties).length > 0" class="mb-5">
            <p class="text-[10px] uppercase tracking-tighter text-slate-400 font-bold mb-2">Properties</p>
            <div class="space-y-1.5 max-h-32 overflow-y-auto pr-2 custom-scrollbar">
              <div v-for="(value, key) in selectedNode.properties" :key="key" class="text-xs bg-slate-50 p-2 rounded-lg border border-slate-100">
                <span class="font-bold text-slate-500">{{ key }}:</span>
                <span class="text-slate-700 ml-1 break-words font-medium">{{ formatPropertyValue(value) }}</span>
              </div>
            </div>
          </div>

          <div class="pt-4 border-t border-slate-100 flex items-center justify-between">
            <span class="text-xs text-slate-400 font-semibold flex items-center gap-1.5">
              <Maximize2 :size="12" />
              {{ getConnectionCount(selectedNode.id) }} connections
            </span>
            <button @click="selectedNode = null" class="text-xs text-primary-600 font-bold hover:underline">
              Close
            </button>
          </div>
        </div>
      </Transition>

      <div
        class="absolute bottom-6 right-6 text-[11px] text-slate-400 bg-white/80 backdrop-blur-sm px-4 py-2 rounded-2xl shadow-sm border border-slate-100 font-bold tracking-tight"
      >
        <span class="text-primary-500">Drag</span> to move · <span class="text-primary-500">Scroll</span> to zoom · <span class="text-primary-500">Click</span> for details
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #cbd5e1;
}

/* Ensure smooth transitions for D3 elements via classes */
line {
  transition: opacity 0.3s ease, stroke 0.3s ease;
}

circle {
  transition: opacity 0.3s ease, fill 0.3s ease, stroke-width 0.2s ease;
}

text {
  transition: opacity 0.3s ease, font-weight 0.2s ease;
  user-select: none;
}

.animate-fade-in {
  animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
