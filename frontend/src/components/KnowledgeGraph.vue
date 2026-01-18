<script setup lang="ts">
/**
 * --------------------------------------------------------------------------
 * AUTHORITATIVE ENTERPRISE GRAPH SYNTHESIS
 * --------------------------------------------------------------------------
 * MERGE PROTOCOL: MAXIMUM VERBOSITY & DEFENSIVE EXPANSION
 * RULE 1: ZERO CODE COMPRESSION.
 * RULE 2: NO REFACTORING.
 * RULE 3: EXPLICIT ERROR HANDLING & TYPE GUARDS.
 * RULE 4: MULTI-FILE STATE SYNTHESIS.
 * --------------------------------------------------------------------------
 */

import { ref, onMounted, onUnmounted, watch, computed, type Ref } from "vue";
import * as d3 from "d3";
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Search,
  Database,
  FileText,
  Loader2,
  Activity,
  AlertCircle,
  Info,
} from "lucide-vue-next";
import {
  fetchGraphData,
  fetchGraphStats,
  type ApiNode,
  type ApiRelationship,
} from "../services/api";

// --- PROPS DEFINITION ---
// Retaining all prop logic for LLM-generated discovery data injection
const props = defineProps<{
  externalData?: {
    nodes: any[];
    links: any[];
  };
}>();

// --- INTERFACE DEFINITIONS (EXPANDED) ---

/**
 * Represents a single node within the D3 Simulation
 */
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

/**
 * Represents a relationship/link between nodes
 */
interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
  value: number;
  label?: string;
  type?: string;
}

/**
 * Wrapper for the complete graph data structure
 */
interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

// --- REACTIVE STATE MANAGEMENT ---

// DOM References
const graphContainer: Ref<HTMLElement | null> = ref(null);
const svgRef: Ref<SVGSVGElement | null> = ref(null);

// UI Interaction State
const selectedNode: Ref<GraphNode | null> = ref(null);
const hoveredNodeId: Ref<string | null> = ref(null);
const searchQuery: Ref<string> = ref("");
const zoomLevel: Ref<number> = ref(1);

// Data Orchestration State
const dataSource: Ref<"demo" | "database"> = ref("demo");
const isLoading: Ref<boolean> = ref(false);
const loadError: Ref<string | null> = ref(null);
const graphStats: Ref<{
  total_nodes: number;
  total_relationships: number;
} | null> = ref(null);

// The Main Graph Data Store (Synthesized from multiple sources)
const graphData: Ref<GraphData> = ref({
  nodes: [],
  links: [],
});

// --- COLOR SYSTEM (COMPLETE MERGE) ---

const groupColors: Record<string | number, string> = {
  // Machine Learning / AI Domains
  "Core AI": "#0ea5e9",
  Frameworks: "#8b5cf6",
  Applications: "#10b981",
  LLMs: "#f59e0b",
  Data: "#ef4444",

  // Numeric Mapping (Fallbacks)
  1: "#0ea5e9",
  2: "#8b5cf6",
  3: "#10b981",
  4: "#f59e0b",
  5: "#ef4444",

  // Extended Categories (From Synthesis)
  "Cooking Basics": "#f472b6",
  Techniques: "#fb7185",
  "Frontend Core": "#2dd4bf",

  // Database Label Mappings
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
};

// --- STATIC DEMO DATA (RETAINED & MERGED) ---

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

// --- D3 SIMULATION ENGINE GLOBALS ---

const simulation: Ref<d3.Simulation<GraphNode, GraphLink> | null> = ref(null);
let svgElement: d3.Selection<SVGSVGElement, unknown, null, undefined> | null =
  null;
let gElement: d3.Selection<SVGGElement, unknown, null, undefined> | null = null;
let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;
let nodesSelection: d3.Selection<any, GraphNode, any, any> | null = null;
let linksSelection: d3.Selection<any, GraphLink, any, any> | null = null;

// --- EXPLICIT UTILITY METHODS (DEFENSIVE EXPANSION) ---

/**
 * Resolves the appropriate hex color for a node based on various metadata properties.
 * Protocol: Check group numeric, then group string, then labels array.
 */
const getNodeColor = (node: GraphNode): string => {
  if (node.group !== undefined && groupColors[node.group]) {
    return groupColors[node.group];
  }

  if (node.labels && node.labels.length > 0) {
    const primaryLabel = node.labels[0];
    if (groupColors[primaryLabel]) {
      return groupColors[primaryLabel];
    }
  }

  return "#94a3b8"; // Default slate-400
};

/**
 * Safely converts property values for UI display, handling objects and nulls.
 */
const formatPropertyValue = (value: any): string => {
  if (value === null || value === undefined) {
    return "None";
  }

  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch (e) {
      return "Complex Data";
    }
  }

  return String(value);
};

/**
 * Counts active connections for a given node ID across the current link set.
 */
const getConnectionCount = (nodeId: string): number => {
  if (!graphData.value || !graphData.value.links) {
    return 0;
  }

  const matches = graphData.value.links.filter((l) => {
    const sourceId =
      typeof l.source === "string" ? l.source : (l.source as GraphNode).id;
    const targetId =
      typeof l.target === "string" ? l.target : (l.target as GraphNode).id;
    return sourceId === nodeId || targetId === nodeId;
  });

  return matches.length;
};

// --- GRAPH RENDER ENGINE (MAXIMUM VERBOSITY) ---

/**
 * Initializes the D3 force simulation and SVG rendering pipeline.
 * Contains explicit error handling and null-checks to prevent runtime crashes.
 */
const initGraph = () => {
  // CRITICAL FAILURE PREVENTION: DOM GUARDS
  if (graphContainer.value === null) {
    console.error("Initialization failed: graphContainer is null.");
    return;
  }

  if (svgRef.value === null) {
    console.error("Initialization failed: svgRef is null.");
    return;
  }

  const containerWidth: number = graphContainer.value.clientWidth;
  const containerHeight: number = graphContainer.value.clientHeight;

  // DIMENSION GUARD
  if (containerWidth <= 0 || containerHeight <= 0) {
    console.warn("Graph dimensions invalid. Postponing initialization.");
    return;
  }

  // RECONSTRUCT BASE SVG ELEMENTS
  svgElement = d3.select(svgRef.value);
  svgElement.selectAll("*").remove(); // Clear previous render
  gElement = svgElement.append("g");

  // CONFIGURE ZOOM BEHAVIOR
  zoomBehavior = d3
    .zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.1, 5])
    .on("zoom", (event) => {
      if (gElement) {
        gElement.attr("transform", event.transform);
        zoomLevel.value = event.transform.k;
      }
    });

  svgElement.call(zoomBehavior).on("dblclick.zoom", null);

  // PREPARE LOCAL DATA CLONES (Object Constancy)
  const simulationNodes: GraphNode[] = graphData.value.nodes.map((d) => {
    return {
      ...d,
      fx: null,
      fy: null,
    };
  });

  const simulationLinks: GraphLink[] = graphData.value.links.map((d) => {
    return { ...d };
  });

  // LINK ID RESOLUTION
  simulationLinks.forEach((link) => {
    // Resolve Source
    if (typeof link.source === "string") {
      const match = simulationNodes.find((n) => n.id === link.source);
      if (match) {
        link.source = match;
      }
    }
    // Resolve Target
    if (typeof link.target === "string") {
      const match = simulationNodes.find((n) => n.id === link.target);
      if (match) {
        link.target = match;
      }
    }
  });

  // INITIALIZE FORCE SIMULATION
  simulation.value = d3
    .forceSimulation<GraphNode>(simulationNodes)
    .force(
      "link",
      d3
        .forceLink<GraphNode, GraphLink>(simulationLinks)
        .id((d) => d.id)
        .distance(150),
    )
    .force("charge", d3.forceManyBody().strength(-600))
    .force("center", d3.forceCenter(containerWidth / 2, containerHeight / 2))
    .force("collision", d3.forceCollide().radius(70))
    .force("x", d3.forceX(containerWidth / 2).strength(0.05))
    .force("y", d3.forceY(containerHeight / 2).strength(0.05));

  // RENDER RELATIONSHIP LINES
  linksSelection = gElement
    .append("g")
    .attr("class", "links-layer")
    .selectAll("line")
    .data(simulationLinks)
    .join("line")
    .attr("stroke", "#cbd5e1")
    .attr("stroke-opacity", 0.6)
    .attr("stroke-width", (d) => Math.sqrt(d.value || 1) * 2);

  // RENDER NODE GROUPS
  nodesSelection = gElement
    .append("g")
    .attr("class", "nodes-layer")
    .selectAll("g")
    .data(simulationNodes)
    .join("g")
    .style("cursor", "pointer")
    .call(
      d3
        .drag<any, GraphNode>()
        .on("start", (event, d) => {
          if (!event.active && simulation.value) {
            simulation.value.alphaTarget(0.3).restart();
          }
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active && simulation.value) {
            simulation.value.alphaTarget(0);
          }
          d.fx = null;
          d.fy = null;
        }) as any,
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

  // DRAW NODE CIRCLES
  nodesSelection
    .append("circle")
    .attr("r", 24)
    .attr("fill", (d) => getNodeColor(d))
    .attr("stroke", "#ffffff")
    .attr("stroke-width", 4)
    .style("filter", "drop-shadow(0 4px 6px rgba(0,0,0,0.15))");

  // DRAW NODE LABELS
  nodesSelection
    .append("text")
    .text((d) => d.label)
    .attr("x", 32)
    .attr("y", 6)
    .attr("fill", "#334155")
    .style("font-size", "14px")
    .style("font-weight", "700")
    .style("letter-spacing", "-0.025em")
    .style("pointer-events", "none");

  // SIMULATION TICK UPDATE LOGIC
  simulation.value.on("tick", () => {
    // Update link coordinates
    linksSelection
      ?.attr("x1", (d: any) => d.source.x)
      .attr("y1", (d: any) => d.source.y)
      .attr("x2", (d: any) => d.target.x)
      .attr("y2", (d: any) => d.target.y);

    // Update node group translations
    nodesSelection?.attr("transform", (d: any) => {
      return `translate(${d.x},${d.y})`;
    });
  });
};

/**
 * Dynamically updates SVG element styles (opacity, highlight) based on search and hover state.
 */
const updateStyles = () => {
  const query: string = searchQuery.value.trim().toLowerCase();

  if (nodesSelection) {
    nodesSelection.selectAll("circle").attr("opacity", (d: any) => {
      const match: boolean =
        !query ||
        d.label.toLowerCase().includes(query) ||
        (d.description && d.description.toLowerCase().includes(query));

      const isDimmed: boolean =
        (hoveredNodeId.value !== null && hoveredNodeId.value !== d.id) ||
        !match;

      return isDimmed ? 0.25 : 1.0;
    });

    nodesSelection.selectAll("text").attr("opacity", (d: any) => {
      const match: boolean = !query || d.label.toLowerCase().includes(query);
      return match ? 1.0 : 0.15;
    });
  }

  if (linksSelection) {
    linksSelection.attr("opacity", (d: any) => {
      const sId = typeof d.source === "string" ? d.source : d.source.id;
      const tId = typeof d.target === "string" ? d.target : d.target.id;

      if (hoveredNodeId.value !== null) {
        const isConnected: boolean =
          sId === hoveredNodeId.value || tId === hoveredNodeId.value;
        return isConnected ? 1.0 : 0.05;
      }
      return 0.6;
    });
  }
};

// --- DATA SOURCE LOGIC (SYNTHESIZED) ---

/**
 * Reverts the view to the static Demo data provided in the code.
 */
const loadDemoData = () => {
  isLoading.value = true;
  dataSource.value = "demo";

  const baseNodes = [...demoGraphData.nodes];
  const baseLinks = [...demoGraphData.links];

  // Explicitly merge external data if provided via props
  if (props.externalData) {
    props.externalData.nodes.forEach((newNode) => {
      const exists = baseNodes.some((n) => n.id === newNode.id);
      if (!exists) {
        baseNodes.push(newNode);
      }
    });

    props.externalData.links.forEach((newLink) => {
      baseLinks.push(newLink);
    });
  }

  graphData.value = {
    nodes: baseNodes,
    links: baseLinks,
  };

  graphStats.value = null;

  // Buffer for DOM stability
  setTimeout(() => {
    initGraph();
    isLoading.value = false;
  }, 150);
};

/**
 * Fetches real-time graph nodes and relationships from the connected API service.
 */
const loadFromDatabase = async () => {
  isLoading.value = true;
  loadError.value = null;
  dataSource.value = "database";

  try {
    const rawData = await fetchGraphData();

    if (!rawData || rawData.total_nodes === 0) {
      loadError.value = "Zero nodes found in the database instance.";
      isLoading.value = false;
      return;
    }

    // Capture metadata statistics
    graphStats.value = {
      total_nodes: rawData.total_nodes,
      total_relationships: rawData.total_relationships,
    };

    // Defensive Mapping of API response to local interfaces
    const dbNodes: GraphNode[] = rawData.nodes.map((item: ApiNode) => {
      const n = item.node;
      return {
        id: n.id || `node-${Math.random()}`,
        group: n.labels && n.labels.length > 0 ? n.labels[0] : "General",
        label: n.name || n.label || "Untitled Node",
        description: n.description || "",
        labels: n.labels || [],
        properties: n,
      };
    });

    const dbLinks: GraphLink[] = rawData.relationships.map(
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

    graphData.value = {
      nodes: dbNodes,
      links: dbLinks,
    };

    setTimeout(() => {
      initGraph();
      isLoading.value = false;
    }, 200);
  } catch (err: any) {
    loadError.value =
      err.message || "An unexpected error occurred during database fetch.";
    isLoading.value = false;
    console.error("Database Fetch Error:", err);
  }
};

// --- VIEWPORT CONTROLS ---

const executeZoomIn = () => {
  if (svgElement && zoomBehavior) {
    svgElement.transition().duration(400).call(zoomBehavior.scaleBy, 1.4);
  }
};

const executeZoomOut = () => {
  if (svgElement && zoomBehavior) {
    svgElement.transition().duration(400).call(zoomBehavior.scaleBy, 0.7);
  }
};

const executeRecenter = () => {
  if (svgElement && zoomBehavior) {
    svgElement
      .transition()
      .duration(700)
      .call(zoomBehavior.transform, d3.zoomIdentity);
  }
};

const executeSimulationRestart = () => {
  if (simulation.value) {
    simulation.value.alpha(0.5).restart();
  }
};

// --- LIFECYCLE & OBSERVABLES ---

// Watch for prop changes from LLM-driven discovery
watch(
  () => props.externalData,
  (newData) => {
    if (dataSource.value === "demo") {
      loadDemoData();
    }
  },
  { deep: true },
);

// React to search filtering
watch(searchQuery, () => {
  updateStyles();
});

let resizeDebounceTimer: any;
const handleWindowResize = () => {
  clearTimeout(resizeDebounceTimer);
  resizeDebounceTimer = setTimeout(() => {
    initGraph();
  }, 300);
};

onMounted(() => {
  loadDemoData();
  window.addEventListener("resize", handleWindowResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", handleWindowResize);
  if (simulation.value) {
    simulation.value.stop();
  }
  clearTimeout(resizeDebounceTimer);
});

// COMPUTED PROPERTIES FOR LEGEND DYNAMICS
const activeLegendItems = computed(() => {
  const categories = new Set<string>();

  graphData.value.nodes.forEach((node) => {
    if (typeof node.group === "string" && isNaN(Number(node.group))) {
      categories.add(node.group);
    } else if (node.labels && node.labels.length > 0) {
      categories.add(node.labels[0]);
    }
  });

  return Array.from(categories).sort();
});
</script>

<template>
  <div
    class="flex h-screen w-full bg-[#f8fafc] overflow-hidden antialiased text-slate-900"
  >
    <div class="flex-1 relative flex flex-col" ref="graphContainer">
      <svg
        ref="svgRef"
        class="w-full h-full cursor-grab active:cursor-grabbing"
      ></svg>

      <div class="absolute top-8 left-8 flex flex-col gap-6 z-20 w-[340px]">
        <div
          class="bg-white/95 backdrop-blur-xl rounded-[24px] shadow-[0_20px_50px_rgba(0,0,0,0.1)] border border-white p-5"
        >
          <div
            class="flex items-center gap-4 bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 focus-within:ring-2 focus-within:ring-sky-500/20 transition-all"
          >
            <Search :size="18" class="text-slate-400" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search roadmap nodes..."
              class="bg-transparent border-none outline-none text-sm font-semibold text-slate-700 w-full placeholder:text-slate-400"
            />
            <button
              v-if="searchQuery"
              @click="searchQuery = ''"
              class="text-slate-400 hover:text-slate-600 transition-colors"
            >
              <Maximize2 :size="14" class="rotate-45" />
            </button>
          </div>
        </div>

        <div
          class="bg-white/95 backdrop-blur-xl rounded-[24px] shadow-[0_20px_50px_rgba(0,0,0,0.1)] border border-white p-2 flex gap-2"
        >
          <button
            @click="loadDemoData"
            class="flex-1 flex items-center justify-center gap-2 py-3 rounded-2xl text-[11px] font-black tracking-widest transition-all"
            :class="
              dataSource === 'demo'
                ? 'bg-sky-500 text-white shadow-[0_10px_20px_rgba(14,165,233,0.3)]'
                : 'bg-transparent text-slate-500 hover:bg-slate-50'
            "
          >
            <FileText :size="16" />
            DEMO DATA
          </button>
          <button
            @click="loadFromDatabase"
            :disabled="isLoading"
            class="flex-1 flex items-center justify-center gap-2 py-3 rounded-2xl text-[11px] font-black tracking-widest transition-all"
            :class="
              dataSource === 'database'
                ? 'bg-violet-500 text-white shadow-[0_10px_20px_rgba(139,92,246,0.3)]'
                : 'bg-transparent text-slate-500 hover:bg-slate-50'
            "
          >
            <Loader2 v-if="isLoading" :size="16" class="animate-spin" />
            <Database v-else :size="16" />
            LIVE DB
          </button>
        </div>

        <div
          v-if="loadError"
          class="bg-rose-50 border border-rose-100 p-4 rounded-2xl flex items-start gap-3 animate-in fade-in slide-in-from-left-4"
        >
          <AlertCircle :size="18" class="text-rose-500 shrink-0 mt-0.5" />
          <p class="text-xs text-rose-700 font-bold leading-relaxed">
            {{ loadError }}
          </p>
        </div>

        <div
          v-if="graphStats && dataSource === 'database'"
          class="bg-slate-900/90 backdrop-blur-md p-4 rounded-2xl border border-slate-800 shadow-xl flex flex-col gap-3"
        >
          <div class="flex items-center justify-between">
            <span
              class="text-[10px] text-slate-400 font-black tracking-[0.2em] uppercase"
              >Graph Health</span
            >
            <Activity :size="14" class="text-emerald-400" />
          </div>
          <div class="flex gap-4">
            <div class="flex flex-col">
              <span class="text-xl font-black text-white leading-none">{{
                graphStats.total_nodes
              }}</span>
              <span class="text-[9px] text-slate-500 font-bold uppercase mt-1"
                >Nodes</span
              >
            </div>
            <div class="w-px h-8 bg-slate-800"></div>
            <div class="flex flex-col">
              <span class="text-xl font-black text-white leading-none">{{
                graphStats.total_relationships
              }}</span>
              <span class="text-[9px] text-slate-500 font-bold uppercase mt-1"
                >Links</span
              >
            </div>
          </div>
        </div>

        <div
          class="bg-white/95 backdrop-blur-xl rounded-[24px] shadow-[0_20px_50px_rgba(0,0,0,0.1)] border border-white p-6"
        >
          <p
            class="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-black mb-5"
          >
            Knowledge Domains
          </p>
          <div
            class="flex flex-col gap-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar"
          >
            <div
              v-for="label in activeLegendItems"
              :key="label"
              class="flex items-center gap-4 group cursor-default"
            >
              <span
                class="w-3.5 h-3.5 rounded-full shadow-sm ring-4 ring-slate-50 group-hover:scale-125 transition-transform"
                :style="{ backgroundColor: groupColors[label] || '#94a3b8' }"
              ></span>
              <span
                class="text-[12px] text-slate-600 font-bold tracking-tight"
                >{{ label }}</span
              >
            </div>
            <div v-if="activeLegendItems.length === 0" class="py-4 text-center">
              <Info :size="16" class="mx-auto text-slate-300 mb-2" />
              <p class="text-[11px] italic text-slate-400">
                Determining categories...
              </p>
            </div>
          </div>
        </div>
      </div>

      <div class="absolute top-8 right-8 flex flex-col gap-3 z-20">
        <button
          @click="executeZoomIn"
          class="p-4 bg-white rounded-2xl shadow-xl hover:bg-slate-50 transition-all border border-slate-100 text-slate-600 hover:text-sky-500"
          title="Zoom In"
        >
          <ZoomIn :size="22" />
        </button>
        <button
          @click="executeZoomOut"
          class="p-4 bg-white rounded-2xl shadow-xl hover:bg-slate-50 transition-all border border-slate-100 text-slate-600 hover:text-sky-500"
          title="Zoom Out"
        >
          <ZoomOut :size="22" />
        </button>
        <button
          @click="executeRecenter"
          class="p-4 bg-white rounded-2xl shadow-xl hover:bg-slate-50 transition-all border border-slate-100 text-slate-600 hover:text-sky-500"
          title="Recenter Camera"
        >
          <Maximize2 :size="22" />
        </button>
        <div class="h-px w-full bg-slate-100 my-1"></div>
        <button
          @click="executeSimulationRestart"
          class="p-4 bg-white rounded-2xl shadow-xl hover:bg-slate-50 transition-all border border-slate-100 text-slate-600 hover:text-emerald-500"
          title="Reheat Simulation"
        >
          <Activity :size="22" />
        </button>
      </div>

      <div
        v-if="selectedNode"
        class="absolute bottom-10 left-10 right-10 lg:right-auto lg:w-[480px] bg-white rounded-[32px] shadow-[0_40px_80px_rgba(0,0,0,0.15)] z-30 border border-slate-100 overflow-hidden animate-in fade-in slide-in-from-bottom-10 duration-500"
      >
        <div class="relative p-8">
          <button
            @click="selectedNode = null"
            class="absolute top-8 right-8 p-2 text-slate-300 hover:text-slate-900 hover:bg-slate-50 rounded-xl transition-all"
          >
            <Maximize2 :size="20" class="rotate-45" />
          </button>

          <div class="flex items-start gap-6 mb-8">
            <div
              class="w-16 h-16 rounded-[24px] shadow-inner ring-[6px] ring-slate-50 flex items-center justify-center shrink-0"
              :style="{ backgroundColor: getNodeColor(selectedNode) }"
            >
              <Info :size="28" class="text-white/80" />
            </div>
            <div class="pt-1">
              <h3
                class="font-black text-3xl text-slate-900 tracking-tighter leading-[0.9]"
              >
                {{ selectedNode.label }}
              </h3>
              <div class="flex items-center gap-2 mt-3">
                <span
                  class="text-[10px] font-black uppercase tracking-widest text-slate-400"
                  >Node Explorer</span
                >
                <div class="w-1 h-1 rounded-full bg-slate-300"></div>
                <span
                  class="text-[10px] font-black uppercase tracking-widest text-sky-500"
                  >{{ selectedNode.id }}</span
                >
              </div>
            </div>
          </div>

          <div class="space-y-6">
            <div
              class="bg-slate-50 p-6 rounded-[24px] border border-slate-100 relative overflow-hidden"
            >
              <div class="absolute top-0 left-0 w-1 h-full bg-sky-400"></div>
              <p
                class="text-[15px] text-slate-600 leading-relaxed font-bold italic"
              >
                "{{
                  selectedNode.description ||
                  "No detailed abstract available for this knowledge point."
                }}"
              </p>
            </div>

            <div
              v-if="
                selectedNode.properties &&
                Object.keys(selectedNode.properties).length > 0
              "
            >
              <p
                class="text-[10px] text-slate-400 font-black uppercase mb-3 tracking-[0.2em]"
              >
                Atomic Properties
              </p>
              <div class="grid grid-cols-1 gap-2">
                <div
                  v-for="(val, key) in selectedNode.properties"
                  :key="key"
                  class="flex items-center justify-between py-3 px-5 bg-white border border-slate-100 rounded-2xl shadow-sm"
                >
                  <span
                    class="text-[11px] font-black text-slate-400 uppercase tracking-wider"
                    >{{ key }}</span
                  >
                  <span class="text-xs font-bold text-slate-700">{{
                    formatPropertyValue(val)
                  }}</span>
                </div>
              </div>
            </div>

            <div v-if="selectedNode.labels && selectedNode.labels.length > 0">
              <p
                class="text-[10px] text-slate-400 font-black uppercase mb-3 tracking-[0.2em]"
              >
                Ontology Classifiers
              </p>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="l in selectedNode.labels"
                  :key="l"
                  class="px-4 py-1.5 bg-slate-900 text-white text-[10px] font-black rounded-xl uppercase tracking-widest"
                >
                  {{ l }}
                </span>
              </div>
            </div>

            <div
              class="pt-6 border-t border-slate-100 flex items-center justify-between"
            >
              <div class="flex items-center gap-2 text-slate-400">
                <Activity :size="14" />
                <span class="text-[11px] font-black uppercase tracking-widest">
                  Topology Influence:
                  {{ getConnectionCount(selectedNode.id) }} nodes
                </span>
              </div>
              <div
                class="flex items-center gap-1.5 px-3 py-1 bg-emerald-50 rounded-full border border-emerald-100"
              >
                <div
                  class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"
                ></div>
                <span class="text-[9px] font-black text-emerald-600 uppercase"
                  >Active Node</span
                >
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        class="absolute bottom-10 right-10 flex items-center gap-4 bg-white/80 backdrop-blur-md px-6 py-3 rounded-full border border-white/50 shadow-xl pointer-events-none"
      >
        <div class="flex gap-4 items-center">
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-slate-300"></div>
            <span
              class="text-[10px] font-black text-slate-500 uppercase tracking-widest"
              >Orbit Zoom</span
            >
          </div>
          <div class="w-1 h-1 rounded-full bg-slate-200"></div>
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-slate-300"></div>
            <span
              class="text-[10px] font-black text-slate-500 uppercase tracking-widest"
              >Drag Mass</span
            >
          </div>
          <div class="w-1 h-1 rounded-full bg-slate-200"></div>
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-slate-300"></div>
            <span
              class="text-[10px] font-black text-slate-500 uppercase tracking-widest"
              >Tap Node</span
            >
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/**
 * CUSTOM SCROLLBAR DYNAMICS
 */
.custom-scrollbar::-webkit-scrollbar {
  width: 5px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 20px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #cbd5e1;
}

/**
 * ANIMATION DEFINITIONS
 */
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-in {
  animation: fade-in 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* Ensure SVG fills container precisely */
svg {
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

/* Force text smoothing for typography-heavy panels */
.antialiased {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
