<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from "vue";
import * as d3 from "d3";
import { ZoomIn, ZoomOut, Maximize2, Search, FileText } from "lucide-vue-next";

// --- Props for LLM-generated data ---
const props = defineProps<{
  externalData?: { nodes: any[]; links: any[] };
}>();

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
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

const graphContainer = ref<HTMLElement | null>(null);
const svgRef = ref<SVGSVGElement | null>(null);
const selectedNode = ref<GraphNode | null>(null);
const searchQuery = ref("");
const zoomLevel = ref(1);
const hoveredNodeId = ref<string | null>(null);

// This stores the combined data of your OG graph + any LLM discoveries
const graphData = ref<GraphData>({ nodes: [], links: [] });

const groupColors: Record<string | number, string> = {
  // Original ML categories (keeping these consistent)
  "Core AI": "#0ea5e9", // Sky Blue
  Frameworks: "#8b5cf6", // Violet
  Applications: "#10b981", // Emerald
  LLMs: "#f59e0b", // Amber
  Data: "#ef4444", // Red

  // Numeric fallbacks for initial nodes
  1: "#0ea5e9",
  2: "#8b5cf6",
  3: "#10b981",
  4: "#f59e0b",
  5: "#ef4444",

  // --- NEW UNIQUE COLORS FOR NEW CATEGORIES ---
  "Cooking Basics": "#f472b6", // Pink
  Techniques: "#fb7185", // Rose/Coral
  "Frontend Core": "#2dd4bf", // Teal
};

// --- OG GRAPH DATA: Restored word-for-word ---
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
    { source: "1", target: "2", value: 3 },
    { source: "2", target: "3", value: 3 },
    { source: "1", target: "13", value: 2 },
    { source: "3", target: "7", value: 2 },
    { source: "3", target: "8", value: 2 },
    { source: "3", target: "9", value: 2 },
    { source: "2", target: "5", value: 2 },
    { source: "2", target: "6", value: 2 },
    { source: "4", target: "5", value: 2 },
    { source: "4", target: "6", value: 2 },
    { source: "12", target: "10", value: 3 },
    { source: "12", target: "11", value: 3 },
    { source: "8", target: "10", value: 2 },
    { source: "8", target: "11", value: 2 },
    { source: "1", target: "14", value: 2 },
    { source: "14", target: "15", value: 2 },
    { source: "7", target: "12", value: 1 },
  ],
};

const simulation = ref<d3.Simulation<GraphNode, GraphLink> | null>(null);
let svgElement: d3.Selection<SVGSVGElement, unknown, null, undefined> | null =
  null;
let gElement: d3.Selection<SVGGElement, unknown, null, undefined> | null = null;
let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;
let nodesSelection: d3.Selection<any, GraphNode, any, any> | null = null;
let linksSelection: d3.Selection<any, GraphLink, any, any> | null = null;

const getNodeColor = (node: GraphNode): string => {
  return groupColors[node.group] || "#94a3b8";
};

const handleRestart = () => {
  if (simulation.value) simulation.value.alpha(0.3).restart();
};

const initGraph = () => {
  if (!graphContainer.value || !svgRef.value) return;

  const width = graphContainer.value.clientWidth;
  const height = graphContainer.value.clientHeight;
  if (width === 0 || height === 0) return;

  svgElement = d3.select(svgRef.value);
  svgElement.selectAll("*").remove();
  gElement = svgElement.append("g");

  zoomBehavior = d3
    .zoom<SVGSVGElement, unknown>()
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

  links.forEach((link) => {
    link.source =
      nodes.find(
        (n) =>
          n.id ===
          (typeof link.source === "string" ? link.source : link.source.id),
      ) || link.source;
    link.target =
      nodes.find(
        (n) =>
          n.id ===
          (typeof link.target === "string" ? link.target : link.target.id),
      ) || link.target;
  });

  simulation.value = d3
    .forceSimulation<GraphNode>(nodes)
    .force(
      "link",
      d3
        .forceLink<GraphNode, GraphLink>(links)
        .id((d) => d.id)
        .distance(140),
    )
    .force("charge", d3.forceManyBody().strength(-500))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(60));

  linksSelection = gElement
    .append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", "#e2e8f0")
    .attr("stroke-opacity", 0.6)
    .attr("stroke-width", 2);

  nodesSelection = gElement
    .append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .style("cursor", "grab")
    .call(
      d3
        .drag<any, GraphNode>()
        .on("start", (event, d) => {
          if (!event.active) simulation.value?.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.value?.alphaTarget(0);
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

  nodesSelection
    .append("circle")
    .attr("r", 22)
    .attr("fill", (d) => getNodeColor(d))
    .attr("stroke", "#fff")
    .attr("stroke-width", 3)
    .style("filter", "drop-shadow(0 4px 6px rgba(0,0,0,0.1))");

  nodesSelection
    .append("text")
    .text((d) => d.label)
    .attr("x", 28)
    .attr("y", 5)
    .attr("fill", "#1e293b")
    .style("font-size", "13px")
    .style("font-weight", "600")
    .style("pointer-events", "none");

  simulation.value.on("tick", () => {
    linksSelection
      ?.attr("x1", (d) => (d.source as any).x)
      .attr("y1", (d) => (d.source as any).y)
      .attr("x2", (d) => (d.target as any).x)
      .attr("y2", (d) => (d.target as any).y);
    nodesSelection?.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });
};

const updateStyles = () => {
  const query = searchQuery.value.toLowerCase();
  nodesSelection?.selectAll("circle").attr("opacity", (d: any) => {
    const matchesSearch = !query || d.label.toLowerCase().includes(query);
    const isDimmed =
      (hoveredNodeId.value && hoveredNodeId.value !== d.id) || !matchesSearch;
    return isDimmed ? 0.2 : 1;
  });
};

// --- DATA MERGING LOGIC: Merges OG nodes with LLM nodes ---
watch(
  () => props.externalData,
  (newData) => {
    const mergedNodes = [...demoGraphData.nodes];
    const mergedLinks = [...demoGraphData.links];

    if (newData) {
      newData.nodes.forEach((n) => {
        if (!mergedNodes.find((existing) => existing.id === n.id))
          mergedNodes.push(n);
      });
      newData.links.forEach((l) => mergedLinks.push(l));
    }

    graphData.value = { nodes: mergedNodes, links: mergedLinks };
    setTimeout(() => initGraph(), 100);
  },
  { deep: true, immediate: true },
);

onMounted(() => {
  window.addEventListener("resize", initGraph);
});

onUnmounted(() => {
  window.removeEventListener("resize", initGraph);
  simulation.value?.stop();
});
</script>

<template>
  <div class="flex h-full bg-slate-50">
    <div class="flex-1 relative" ref="graphContainer">
      <svg ref="svgRef" class="w-full h-full"></svg>

      <div
        class="absolute top-6 left-6 bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-5 z-10 w-72 border border-white"
      >
        <div class="flex items-center gap-3 mb-5 bg-slate-100 p-2.5 rounded-xl">
          <Search :size="18" class="text-slate-400" />
          <input
            v-model="searchQuery"
            placeholder="Search roadmap..."
            class="bg-transparent text-sm outline-none w-full font-medium"
          />
        </div>

        <div class="space-y-2.5">
          <p
            class="text-[10px] uppercase tracking-widest text-slate-400 font-bold mb-3"
          >
            Skill Categories
          </p>
          <div v-for="(color, label) in groupColors" :key="label">
            <div v-if="isNaN(Number(label))" class="flex items-center gap-3">
              <span
                class="w-3 h-3 rounded-full shadow-sm"
                :style="{ backgroundColor: color }"
              ></span>
              <span class="text-xs text-slate-600 font-semibold">{{
                label
              }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="absolute top-6 right-6 flex flex-col gap-3 z-10">
        <button
          @click="handleRestart"
          class="p-3 bg-white rounded-2xl shadow-lg hover:bg-slate-50 transition-all border border-slate-100"
        >
          <Maximize2 :size="20" class="text-slate-600" />
        </button>
      </div>

      <div
        v-if="selectedNode"
        class="absolute bottom-6 left-6 bg-white p-6 rounded-3xl shadow-2xl max-w-sm z-10 border border-slate-100"
      >
        <div class="flex items-center gap-4 mb-4">
          <div
            class="w-5 h-5 rounded-full shadow-inner"
            :style="{ backgroundColor: getNodeColor(selectedNode) }"
          ></div>
          <h3 class="font-extrabold text-xl text-slate-900 tracking-tight">
            {{ selectedNode.label }}
          </h3>
        </div>
        <p
          class="text-sm text-slate-600 leading-relaxed mb-6 font-medium italic"
        >
          "{{ selectedNode.description }}"
        </p>
      </div>
    </div>
  </div>
</template>
