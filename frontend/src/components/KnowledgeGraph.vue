<script setup lang="ts">
/**
 * D3 KNOWLEDGE GRAPH COMPONENT - MERGED MASTER VERSION
 * AUTHORITATIVE SOURCE: NO FEATURES REMOVED.
 * * FEATURES INCLUDED:
 * 1.  Force-Directed Simulation with Collision Detection
 * 2.  Dual Data Source (Demo ML Data + Live API Database)
 * 3.  External Prop Merging for LLM Discovery
 * 4.  Advanced Zoom/Pan Behavior with Transitions
 * 5.  State-Aware Node Highlighting and Search Filtering
 * 6.  Detailed Metadata Inspector with Property Mapping
 * 7.  Responsive Window Resize Handling
 */

import { ref, onMounted, onUnmounted, watch, computed } from "vue";
import * as d3 from "d3";
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Search,
  Database,
  FileText,
  Loader2,
} from "lucide-vue-next";
import {
  fetchGraphData,
  fetchGraphStats,
  type ApiNode,
  type ApiRelationship,
} from "../services/api";

// --- Props Definition ---
// This allows the LLM Discovery engine to push new nodes into the current view.
const props = defineProps<{
  externalData?: {
    nodes: any[];
    links: any[];
  };
}>();

// --- Explicit Interfaces ---
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

// --- Component State ---
const graphContainer = ref<HTMLElement | null>(null);
const svgRef = ref<SVGSVGElement | null>(null);
const selectedNode = ref<GraphNode | null>(null);
const searchQuery = ref("");
const zoomLevel = ref(1);
const hoveredNodeId = ref<string | null>(null);
const dataSource = ref<"demo" | "database">("demo");
const isLoading = ref(false);
const loadError = ref<string | null>(null);
const graphStats = ref<{
  total_nodes: number;
  total_relationships: number;
} | null>(null);
const graphData = ref<GraphData>({ nodes: [], links: [] });

// --- Unified Color Palette ---
// Combines the original ML numeric groups with the new discovery category strings.
const groupColors: Record<string | number, string> = {
  1: "#0ea5e9", // Sky Blue
  2: "#8b5cf6", // Violet
  3: "#10b981", // Emerald
  4: "#f59e0b", // Amber
  5: "#ef4444", // Red
  "Core AI": "#0ea5e9",
  Frameworks: "#8b5cf6",
  Applications: "#10b981",
  LLMs: "#f59e0b",
  Data: "#ef4444",
  Skill: "#0ea5e9",
  Concept: "#8b5cf6",
  Topic: "#10b981",
  Project: "#f59e0b",
  Resource: "#ef4444",
  Tool: "#ec4899",
  Person: "#6366f1",
  Domain: "#14b8a6",
  Assessment: "#f97316",
  Milestone: "#84cc16",
  "Cooking Basics": "#f472b6",
  Techniques: "#fb7185",
  "Frontend Core": "#2dd4bf",
};

// --- Static Demo Content ---
// Preserving every single detail of the original dataset.
const demoGraphData: GraphData = {
  nodes: [
    {
      id: "1",
      group: 1,
      label: "Machine Learning",
      description: "Field of AI that enables systems to learn",
    },
    {
      id: "2",
      group: 1,
      label: "Deep Learning",
      description: "Subset of ML using neural networks",
    },
    {
      id: "3",
      group: 1,
      label: "Neural Networks",
      description: "Computing systems inspired by biological brains",
    },
    {
      id: "4",
      group: 2,
      label: "Python",
      description: "Programming language popular in AI",
    },
    {
      id: "5",
      group: 2,
      label: "TensorFlow",
      description: "Open source ML framework by Google",
    },
    {
      id: "6",
      group: 2,
      label: "PyTorch",
      description: "Open source ML framework by Meta",
    },
    {
      id: "7",
      group: 3,
      label: "Computer Vision",
      description: "Enabling computers to see and understand images",
    },
    {
      id: "8",
      group: 3,
      label: "NLP",
      description: "Processing human language by computers",
    },
    {
      id: "9",
      group: 3,
      label: "Speech Recognition",
      description: "Converting spoken words to text",
    },
    {
      id: "10",
      group: 4,
      label: "GPT",
      description: "Generative Pre-trained Transformer models",
    },
    {
      id: "11",
      group: 4,
      label: "BERT",
      description: "Bidirectional Encoder Representations",
    },
    {
      id: "12",
      group: 4,
      label: "Transformer",
      description: "Architecture using attention mechanism",
    },
    {
      id: "13",
      group: 1,
      label: "Reinforcement Learning",
      description: "Learning through rewards and punishments",
    },
    {
      id: "14",
      group: 5,
      label: "Data Science",
      description: "Extracting insights from data",
    },
    {
      id: "15",
      group: 5,
      label: "Analytics",
      description: "Analyzing data for decisions",
    },
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

// --- D3 Globals ---
let simulation: d3.Simulation<GraphNode, GraphLink> | null = null;
let svgElement: d3.Selection<SVGSVGElement, unknown, null, undefined> | null =
  null;
let gElement: d3.Selection<SVGGElement, unknown, null, undefined> | null = null;
let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;
let nodesSelection: d3.Selection<any, GraphNode, any, any> | null = null;
let linksSelection: d3.Selection<any, GraphLink, any, any> | null = null;

// --- Utility Functions ---

/**
 * Returns the color associated with a node based on its source and group/label.
 */
const getNodeColor = (node: GraphNode): string => {
  if (dataSource.value === "demo") {
    const demoColor = groupColors[node.group];
    return demoColor || groupColors[1];
  }
  const label = node.labels?.[0] || "Skill";
  return groupColors[label] || groupColors["Skill"];
};

/**
 * Ensures property values are readable strings for the inspector.
 */
const formatPropertyValue = (value: any): string => {
  if (value === null || value === undefined) return "N/A";
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
};

/**
 * Calculates how many links are connected to a specific node.
 */
const getConnectionCount = (nodeId: string): number => {
  const allLinks = graphData.value.links;
  const filtered = allLinks.filter((link) => {
    const sourceId =
      typeof link.source === "string" ? link.source : (link.source as any).id;
    const targetId =
      typeof link.target === "string" ? link.target : (link.target as any).id;
    return sourceId === nodeId || targetId === nodeId;
  });
  return filtered.length;
};

// --- Logic: Data Loading & Merging ---

/**
 * Loads graph from the database service.
 */
const loadFromDatabase = async () => {
  dataSource.value = "database";
  isLoading.value = true;
  loadError.value = null;

  try {
    const data = await fetchGraphData();

    if (!data || data.total_nodes === 0) {
      loadError.value =
        "No data found in database. Please populate the knowledge base.";
      isLoading.value = false;
      return;
    }

    // Update stats for the UI header
    graphStats.value = {
      total_nodes: data.total_nodes,
      total_relationships: data.total_relationships,
    };

    const mappedNodes: GraphNode[] = data.nodes.map((item: ApiNode) => {
      const n = item.node;
      return {
        id: n.id || `node-${Math.random().toString(36).substr(2, 9)}`,
        group: n.labels?.[0] || "Skill",
        label: n.name || n.labels?.[0] || "Unknown",
        description: n.description,
        labels: n.labels,
        properties: n,
      };
    });

    const mappedLinks: GraphLink[] = data.relationships.map(
      (rel: ApiRelationship) => {
        return {
          source: rel.source,
          target: rel.target,
          value: 1,
          type: rel.type,
          label: rel.type,
        };
      },
    );

    graphData.value = { nodes: mappedNodes, links: mappedLinks };

    // Defer initialization to ensure DOM is ready
    setTimeout(() => {
      initGraph();
      isLoading.value = false;
    }, 100);
  } catch (err: any) {
    console.error("Graph Data Load Error:", err);
    loadError.value =
      err.message || "Fatal error communicating with database service.";
    isLoading.value = false;
  }
};

/**
 * Loads demo data and merges with any externally provided nodes.
 */
const loadDemoData = () => {
  dataSource.value = "demo";
  loadError.value = null;

  const mergedNodes = [...demoGraphData.nodes];
  const mergedLinks = [...demoGraphData.links];

  if (props.externalData) {
    // Merge logic: avoid duplicate IDs
    props.externalData.nodes.forEach((newNode) => {
      const exists = mergedNodes.some((exNode) => exNode.id === newNode.id);
      if (!exists) {
        mergedNodes.push(newNode);
      }
    });

    props.externalData.links.forEach((newLink) => {
      mergedLinks.push(newLink);
    });
  }

  graphData.value = {
    nodes: mergedNodes,
    links: mergedLinks,
  };

  graphStats.value = null;

  setTimeout(() => {
    initGraph();
  }, 50);
};

// --- Logic: Interaction & Styling ---

/**
 * Predicate for node visibility and highlighting.
 */
const isNodeMatching = (node: GraphNode): boolean => {
  if (!searchQuery.value) return true;
  const q = searchQuery.value.toLowerCase().trim();

  const labelMatch = node.label.toLowerCase().includes(q);
  const descMatch = node.description?.toLowerCase().includes(q);
  const tagsMatch =
    node.labels && node.labels.some((l) => l.toLowerCase().includes(q));

  return !!(labelMatch || descMatch || tagsMatch);
};

/**
 * Predicate for link visibility.
 */
const isLinkMatching = (link: GraphLink): boolean => {
  if (!searchQuery.value) return true;

  const sId =
    typeof link.source === "string" ? link.source : (link.source as any).id;
  const tId =
    typeof link.target === "string" ? link.target : (link.target as any).id;

  const sourceNode = graphData.value.nodes.find((n) => n.id === sId);
  const targetNode = graphData.value.nodes.find((n) => n.id === tId);

  if (!sourceNode || !targetNode) return false;
  return isNodeMatching(sourceNode) && isNodeMatching(targetNode);
};

/**
 * Core style updater for D3 elements.
 */
const updateStyles = () => {
  if (!nodesSelection || !linksSelection) return;

  const q = searchQuery.value.toLowerCase();

  // Update Circles
  nodesSelection
    .selectAll("circle")
    .transition()
    .duration(200)
    .attr("fill", (d: any) => {
      const base = getNodeColor(d);
      if (!isNodeMatching(d)) return "#d4d4d8"; // Grayed out
      return hoveredNodeId.value === d.id
        ? d3.color(base)?.brighter(0.4)?.toString() || base
        : base;
    })
    .attr("opacity", (d: any) => {
      const matches = isNodeMatching(d);
      const isDistant = hoveredNodeId.value && hoveredNodeId.value !== d.id;
      return isDistant || !matches ? 0.15 : 1;
    })
    .attr("stroke", (d: any) => {
      if (selectedNode.value?.id === d.id) return "#2563eb";
      return hoveredNodeId.value === d.id ? "#1e40af" : "#ffffff";
    })
    .attr("stroke-width", (d: any) => {
      return hoveredNodeId.value === d.id || selectedNode.value?.id === d.id
        ? 4
        : 2;
    });

  // Update Text Labels
  nodesSelection
    .selectAll("text")
    .transition()
    .duration(200)
    .attr("opacity", (d: any) => (isNodeMatching(d) ? 1 : 0.1))
    .attr("font-weight", (d: any) =>
      hoveredNodeId.value === d.id ? "800" : "600",
    );

  // Update Links
  linksSelection
    .transition()
    .duration(200)
    .attr("opacity", (d: any) => (isLinkMatching(d) ? 0.6 : 0.05))
    .attr("stroke", (d: any) => (isLinkMatching(d) ? "#cbd5e1" : "#f1f5f9"));
};

// React to search query changes
watch(searchQuery, () => {
  updateStyles();
});

// --- D3 Engine: Force Simulation ---

/**
 * Initializes the D3 svg, simulation, and bindings.
 */
const initGraph = () => {
  if (!graphContainer.value || !svgRef.value) return;

  const width = graphContainer.value.clientWidth;
  const height = graphContainer.value.clientHeight;

  if (width === 0 || height === 0) return;

  // Clear and setup SVG
  svgElement = d3.select(svgRef.value);
  svgElement.selectAll("*").remove();

  // Layer group for zooming
  gElement = svgElement.append("g");

  // Zoom setup
  zoomBehavior = d3
    .zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.05, 5])
    .on("zoom", (event) => {
      gElement?.attr("transform", event.transform);
      zoomLevel.value = event.transform.k;
    });

  svgElement.call(zoomBehavior).on("dblclick.zoom", null);

  // Deep copy data for D3 mutation
  const nodes: GraphNode[] = graphData.value.nodes.map((d) => ({
    ...d,
    fx: null,
    fy: null,
  }));
  const links: GraphLink[] = graphData.value.links.map((d) => ({ ...d }));

  // Link resolution: ensure source/target point to node objects
  links.forEach((link) => {
    const sLookup =
      typeof link.source === "string" ? link.source : (link.source as any).id;
    const tLookup =
      typeof link.target === "string" ? link.target : (link.target as any).id;

    link.source = nodes.find((n) => n.id === sLookup) || link.source;
    link.target = nodes.find((n) => n.id === tLookup) || link.target;
  });

  // Simulation setup with high collision prevention
  simulation = d3
    .forceSimulation<GraphNode>(nodes)
    .force(
      "link",
      d3
        .forceLink<GraphNode, GraphLink>(links)
        .id((d) => d.id)
        .distance(150),
    )
    .force("charge", d3.forceManyBody().strength(-600))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(70))
    .force("x", d3.forceX(width / 2).strength(0.05))
    .force("y", d3.forceY(height / 2).strength(0.05));

  // Render Links
  linksSelection = gElement
    .append("g")
    .attr("class", "links-layer")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", "#e2e8f0")
    .attr("stroke-opacity", 0.6)
    .attr("stroke-width", (d) => Math.max((d.value || 1) * 2, 2));

  // Render Nodes
  nodesSelection = gElement
    .append("g")
    .attr("class", "nodes-layer")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .style("cursor", "grab")
    .call(
      d3
        .drag<any, GraphNode>()
        .on("start", (e, d) => {
          if (!e.active) simulation?.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (e, d) => {
          d.fx = e.x;
          d.fy = e.y;
        })
        .on("end", (e, d) => {
          if (!e.active) simulation?.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }),
    )
    .on("mouseenter", (e, d) => {
      hoveredNodeId.value = d.id;
      updateStyles();
    })
    .on("mouseleave", () => {
      hoveredNodeId.value = null;
      updateStyles();
    })
    .on("click", (e, d) => {
      selectedNode.value = d;
      e.stopPropagation();
    });

  // Node Backgrounds
  nodesSelection
    .append("circle")
    .attr("r", 24)
    .attr("fill", (d) => getNodeColor(d))
    .attr("stroke", "#ffffff")
    .attr("stroke-width", 3)
    .style("filter", "drop-shadow(0 4px 6px rgba(0,0,0,0.12))");

  // Node Labels
  nodesSelection
    .append("text")
    .text((d) => d.label)
    .attr("x", 32)
    .attr("y", 6)
    .attr("fill", "#0f172a")
    .style("font-size", "14px")
    .style("font-weight", "600")
    .style("pointer-events", "none")
    .style("text-shadow", "0 0 4px rgba(255,255,255,0.8)");

  // Simulation Update Tick
  simulation.on("tick", () => {
    linksSelection
      ?.attr("x1", (d) => (d.source as any).x)
      .attr("y1", (d) => (d.source as any).y)
      .attr("x2", (d) => (d.target as any).x)
      .attr("y2", (d) => (d.target as any).y);

    nodesSelection?.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });

  // Global click to deselect
  svgElement.on("click", () => {
    selectedNode.value = null;
  });
};

// --- View Controls ---

const zoomIn = () => {
  if (!svgElement || !zoomBehavior) return;
  svgElement.transition().duration(400).call(zoomBehavior.scaleBy, 1.4);
};

const zoomOut = () => {
  if (!svgElement || !zoomBehavior) return;
  svgElement.transition().duration(400).call(zoomBehavior.scaleBy, 0.6);
};

const resetZoom = () => {
  if (!svgElement || !zoomBehavior) return;
  svgElement
    .transition()
    .duration(600)
    .call(zoomBehavior.transform, d3.zoomIdentity);
  if (simulation) {
    simulation.alpha(0.5).restart();
  }
};

const handleResize = () => {
  if (simulation) {
    initGraph();
  }
};

// --- Component Lifecycle ---

onMounted(() => {
  loadDemoData();
  window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  if (simulation) {
    simulation.stop();
  }
});

// --- Computed UI State ---

const legendItems = computed(() => {
  if (dataSource.value === "demo") {
    return ["Core AI", "Frameworks", "Applications", "LLMs", "Data"];
  }
  const uniqueLabels = new Set(
    graphData.value.nodes.map((n) => n.labels?.[0] || "Skill"),
  );
  return Array.from(uniqueLabels).sort();
});

const activeNodesCount = computed(() => {
  return graphData.value.nodes.filter(isNodeMatching).length;
});
</script>

<template>
  <div
    class="flex h-full bg-slate-50 overflow-hidden relative selection:bg-primary-100"
  >
    <div class="flex-1 h-full w-full" ref="graphContainer">
      <svg
        ref="svgRef"
        class="w-full h-full block bg-slate-50 transition-colors duration-500"
      ></svg>

      <div
        class="absolute top-6 left-6 bg-white/95 backdrop-blur-lg rounded-3xl shadow-2xl p-6 z-10 w-85 border border-slate-200/60 ring-1 ring-black/5"
      >
        <div
          class="flex items-center gap-4 mb-5 bg-slate-50 p-3 rounded-2xl border border-slate-200 focus-within:ring-2 focus-within:ring-primary-400 focus-within:border-transparent transition-all"
        >
          <Search :size="20" class="text-slate-400" />
          <input
            v-model="searchQuery"
            placeholder="Search knowledge graph..."
            class="bg-transparent text-sm outline-none w-full font-bold text-slate-700 placeholder:text-slate-400"
          />
          <button
            v-if="searchQuery"
            @click="searchQuery = ''"
            class="text-slate-300 hover:text-slate-600 transition-colors font-black text-lg"
          >
            ×
          </button>
        </div>

        <div class="grid grid-cols-2 gap-3 mb-6">
          <button
            @click="loadDemoData"
            :class="
              dataSource === 'demo'
                ? 'bg-primary-600 text-white shadow-lg shadow-primary-200'
                : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
            "
            class="flex items-center justify-center gap-2 px-4 py-3 rounded-2xl text-[13px] font-extrabold border transition-all active:scale-95"
          >
            <FileText :size="16" />
            Demo Data
          </button>
          <button
            @click="loadFromDatabase"
            :disabled="isLoading"
            :class="
              dataSource === 'database'
                ? 'bg-primary-600 text-white shadow-lg shadow-primary-200'
                : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
            "
            class="flex items-center justify-center gap-2 px-4 py-3 rounded-2xl text-[13px] font-extrabold border transition-all active:scale-95 disabled:opacity-50"
          >
            <Loader2 v-if="isLoading" :size="16" class="animate-spin" />
            <Database v-else :size="16" />
            Database
          </button>
        </div>

        <Transition name="fade">
          <div
            v-if="loadError"
            class="p-3 mb-5 bg-red-50 text-[11px] text-red-600 rounded-xl border border-red-100 font-bold leading-tight"
          >
            {{ loadError }}
          </div>
        </Transition>

        <div
          class="space-y-3 max-h-56 overflow-y-auto pr-2 custom-scrollbar border-t border-slate-100 pt-5"
        >
          <p
            class="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-black mb-4"
          >
            Category Map
          </p>
          <div
            v-for="label in legendItems"
            :key="label"
            class="flex items-center gap-4 group cursor-help"
          >
            <span
              class="w-4 h-4 rounded-full border-2 border-white shadow-sm transition-transform group-hover:scale-125"
              :style="{
                backgroundColor: groupColors[label] || groupColors['Skill'],
              }"
            ></span>
            <span
              class="text-[13px] text-slate-600 font-bold group-hover:text-slate-900 transition-colors"
              >{{ label }}</span
            >
          </div>
        </div>

        <div
          class="mt-6 pt-5 border-t border-slate-100 flex items-center justify-between"
        >
          <div class="space-y-1">
            <p
              class="text-[10px] text-slate-400 font-bold uppercase tracking-widest"
            >
              Total Connectivity
            </p>
            <p class="text-sm font-black text-slate-800">
              {{ graphStats?.total_nodes || graphData.nodes.length }} Nodes
            </p>
          </div>
          <div v-if="searchQuery" class="text-right">
            <p
              class="text-[10px] text-primary-500 font-bold uppercase tracking-widest"
            >
              Filtered Result
            </p>
            <p class="text-sm font-black text-primary-600">
              {{ activeNodesCount }} Active
            </p>
          </div>
        </div>
      </div>

      <div class="absolute top-6 right-6 flex flex-col gap-4 z-10">
        <button
          @click="zoomIn"
          class="p-4 bg-white/95 backdrop-blur-md rounded-2xl shadow-xl border border-slate-100 hover:bg-slate-50 hover:shadow-2xl transition-all group active:scale-90"
        >
          <ZoomIn
            :size="24"
            class="text-slate-600 group-hover:text-primary-600"
          />
        </button>
        <button
          @click="zoomOut"
          class="p-4 bg-white/95 backdrop-blur-md rounded-2xl shadow-xl border border-slate-100 hover:bg-slate-50 hover:shadow-2xl transition-all group active:scale-90"
        >
          <ZoomOut
            :size="24"
            class="text-slate-600 group-hover:text-primary-600"
          />
        </button>
        <button
          @click="resetZoom"
          class="p-4 bg-white/95 backdrop-blur-md rounded-2xl shadow-xl border border-slate-100 hover:bg-slate-50 hover:shadow-2xl transition-all group active:scale-90"
        >
          <Maximize2
            :size="24"
            class="text-slate-600 group-hover:text-primary-600"
          />
        </button>
      </div>

      <Transition name="slide-up">
        <div
          v-if="selectedNode"
          class="absolute bottom-8 left-8 bg-white/98 backdrop-blur-xl p-8 rounded-[3rem] shadow-[0_25px_60px_-15px_rgba(0,0,0,0.2)] max-w-md z-20 border border-slate-100 ring-1 ring-black/5 overflow-hidden"
        >
          <div class="flex items-center gap-5 mb-6">
            <div
              class="w-8 h-8 rounded-2xl shadow-inner ring-4 ring-slate-50 transition-all duration-500"
              :style="{ backgroundColor: getNodeColor(selectedNode) }"
            ></div>
            <h3
              class="font-black text-2xl text-slate-900 tracking-tight leading-none"
            >
              {{ selectedNode.label }}
            </h3>
          </div>

          <div v-if="selectedNode.description" class="mb-8">
            <p
              class="text-base text-slate-600 italic font-semibold leading-relaxed p-4 bg-slate-50 rounded-2xl border-l-4 border-primary-500"
            >
              "{{ selectedNode.description }}"
            </p>
          </div>

          <div v-if="selectedNode.labels?.length" class="mb-6">
            <p
              class="text-[11px] uppercase text-slate-400 font-black tracking-widest mb-3"
            >
              Classification Tags
            </p>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="tag in selectedNode.labels"
                :key="tag"
                class="text-[12px] px-3.5 py-1.5 bg-primary-50 text-primary-700 rounded-xl font-black border border-primary-100"
              >
                {{ tag }}
              </span>
            </div>
          </div>

          <div
            v-if="
              selectedNode.properties &&
              Object.keys(selectedNode.properties).length
            "
            class="mb-8"
          >
            <p
              class="text-[11px] uppercase text-slate-400 font-black tracking-widest mb-3"
            >
              System Metadata
            </p>
            <div
              class="space-y-2 max-h-40 overflow-y-auto custom-scrollbar pr-3"
            >
              <div
                v-for="(val, key) in selectedNode.properties"
                :key="key"
                class="group flex flex-col bg-slate-50/50 p-3 rounded-2xl border border-slate-100 hover:border-primary-200 transition-colors"
              >
                <span
                  class="text-[10px] font-black text-slate-400 uppercase tracking-tighter mb-1"
                  >{{ key }}</span
                >
                <span
                  class="text-[13px] text-slate-700 font-bold break-all leading-tight"
                  >{{ formatPropertyValue(val) }}</span
                >
              </div>
            </div>
          </div>

          <div
            class="pt-6 border-t border-slate-100 flex justify-between items-center"
          >
            <div class="flex items-center gap-2">
              <div class="flex -space-x-2">
                <div
                  class="w-6 h-6 rounded-full bg-primary-100 border-2 border-white"
                ></div>
                <div
                  class="w-6 h-6 rounded-full bg-primary-200 border-2 border-white"
                ></div>
              </div>
              <span
                class="text-xs text-slate-500 font-black uppercase tracking-widest"
                >{{ getConnectionCount(selectedNode.id) }} Active
                Connections</span
              >
            </div>
            <button
              @click="selectedNode = null"
              class="text-xs text-white bg-slate-900 px-6 py-2.5 rounded-2xl font-black hover:bg-primary-600 transition-all shadow-lg active:scale-95"
            >
              DONE
            </button>
          </div>
        </div>
      </Transition>

      <div
        class="absolute bottom-8 right-8 text-[11px] text-slate-500 bg-white/90 backdrop-blur-md px-6 py-3 rounded-full shadow-xl border border-slate-100 font-black tracking-[0.15em] flex items-center gap-3"
      >
        <span class="w-2 h-2 rounded-full bg-primary-500 animate-pulse"></span>
        DRAG NODES · PINCH TO ZOOM · CLICK NODE FOR DETAILS
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Scrollbar Styling */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* Animations */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide-up-enter-from {
  transform: translateY(100%) scale(0.9);
  opacity: 0;
}
.slide-up-leave-to {
  transform: translateY(100%) scale(0.9);
  opacity: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Base Styles */
text {
  pointer-events: none;
  user-select: none;
}
circle,
line {
  transition: all 0.3s ease;
}

/* Simulation Performance Class */
.links-layer,
.nodes-layer {
  will-change: transform;
}
</style>
