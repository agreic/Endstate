<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from "vue";
import * as d3 from "d3";
import { ZoomIn, ZoomOut, Maximize2, Search, Database, FileText, Loader2 } from "lucide-vue-next";
import { fetchGraphData, fetchGraphStats, type ApiNode, type ApiRelationship } from "../services/api";

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  group: number;
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

const graphData = ref<GraphData>({ nodes: [], links: [] });

const demoGroupColors: Record<number, string> = {
  1: "#0ea5e9",
  2: "#8b5cf6",
  3: "#10b981",
  4: "#f59e0b",
  5: "#ef4444",
};

const dbGroupColors: Record<string, string> = {
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
};

const getNodeColor = (node: GraphNode): string => {
  if (dataSource.value === 'demo') {
    return demoGroupColors[node.group] || demoGroupColors[1];
  }
  return dbGroupColors[node.labels?.[0] || 'Skill'] || dbGroupColors['Skill'];
};

const getUniqueLabels = (): string[] => {
  if (dataSource.value === 'demo') {
    return ['Core AI', 'Frameworks', 'Applications', 'LLMs', 'Data'];
  }
  const labels = new Set(graphData.value.nodes.map(n => n.labels?.[0] || 'Skill'));
  return Array.from(labels).sort();
};

const getLabelDisplayName = (label: string): string => {
  if (dataSource.value === 'demo') {
    return label;
  }
  return label;
};

const getColorForLegendItem = (index: number, label: string): string => {
  if (dataSource.value === 'demo') {
    return demoGroupColors[index + 1] || demoGroupColors[1];
  }
  return dbGroupColors[label] || dbGroupColors['Skill'];
};

let simulation: d3.Simulation<GraphNode, GraphLink> | null = null;
let svgElement: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null;
let gElement: d3.Selection<SVGGElement, unknown, null, undefined> | null = null;
let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;
let nodesSelection: d3.Selection<d3.EnterElement | d3.Selection<SVGGElement, GraphNode, SVGGElement, unknown>, GraphNode, d3.EnterElement, unknown> | null = null;
let linksSelection: d3.Selection<d3.EnterElement | d3.Selection<SVGSVGElementElement, GraphLink, SVGGElement, unknown>, GraphLink, d3.EnterElement, unknown> | null = null;

const formatPropertyValue = (value: any): string => {
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value);
  }
  return String(value);
};

const loadFromDatabase = async () => {
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
    
    graphData.value.nodes = data.nodes.map((item: ApiNode) => {
      const nodeData = item.node;
      return {
        id: nodeData.id || String(Math.random()),
        group: 1,
        label: nodeData.name || nodeData.labels?.[0] || 'Unknown',
        description: nodeData.description,
        labels: nodeData.labels,
        properties: nodeData,
      };
    });
    
    graphData.value.links = data.relationships.map((rel: ApiRelationship) => ({
      source: rel.source,
      target: rel.target,
      value: 1,
      type: rel.type,
      label: rel.type,
    }));
    
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
  graphData.value = { nodes: [...demoGraphData.nodes], links: [...demoGraphData.links] };
  graphStats.value = null;
  setTimeout(() => {
    initGraph();
  }, 50);
};

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

const updateNodeStyles = () => {
  if (!nodesSelection) return;

  nodesSelection
    .selectAll("circle")
    .attr("fill", (d) => {
      const node = d as GraphNode;
      const isMatch = isNodeMatching(node);
      const isHovered = hoveredNodeId.value === node.id;
      const baseColor = getNodeColor(node);

      if (!isMatch) {
        return "#d4d4d8";
      }
      if (isHovered) {
        return d3.color(baseColor)?.brighter(0.3)?.toString() || baseColor;
      }
      return baseColor;
    })
    .attr("opacity", (d) => {
      const node = d as GraphNode;
      return isNodeMatching(node) ? 1 : 0.3;
    })
    .attr("stroke", (d) => {
      const node = d as GraphNode;
      return isNodeMatching(node) && hoveredNodeId.value === node.id
        ? "#1e40af"
        : "#fff";
    })
    .attr("stroke-width", (d) => {
      const node = d as GraphNode;
      return isNodeMatching(node) && hoveredNodeId.value === node.id ? 3 : 2;
    });

  nodesSelection
    .selectAll("text")
    .attr("opacity", (d) => {
      const node = d as GraphNode;
      return isNodeMatching(node) ? 1 : 0.3;
    })
    .attr("font-weight", (d) => {
      const node = d as GraphNode;
      return hoveredNodeId.value === node.id ? "700" : "500";
    });
};

const updateLinkStyles = () => {
  if (!linksSelection) return;

  linksSelection
    .attr("opacity", (d) => {
      const link = d as GraphLink;
      return isLinkMatching(link) ? 0.6 : 0.1;
    })
    .attr("stroke", (d) => {
      const link = d as GraphLink;
      return isLinkMatching(link) ? "#d4d4d8" : "#e4e4e7";
    });
};

watch(searchQuery, () => {
  updateNodeStyles();
  updateLinkStyles();
});

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
    .scaleExtent([0.3, 4])
    .on("zoom", (event) => {
      if (gElement) {
        gElement.attr("transform", event.transform);
        zoomLevel.value = event.transform.k;
      }
    });

  svgElement.call(zoomBehavior);
  svgElement.on("dblclick.zoom", null);

  const nodes: GraphNode[] = graphData.value.nodes.map((d) => ({
    ...d,
    fx: null,
    fy: null,
  }));
  const links: GraphLink[] = graphData.value.links.map((d) => ({ ...d }));

  for (const link of links) {
    const sourceNode = nodes.find((n) => n.id === link.source || (link.source as GraphNode)?.id === link.source);
    const targetNode = nodes.find((n) => n.id === link.target || (link.target as GraphNode)?.id === link.target);
    if (sourceNode) link.source = sourceNode;
    if (targetNode) link.target = targetNode;
  }

  simulation = d3
    .forceSimulation<GraphNode>(nodes)
    .force(
      "link",
      d3
        .forceLink<GraphNode, GraphLink>(links)
        .id((d) => d.id)
        .distance(120),
    )
    .force("charge", d3.forceManyBody().strength(-400))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(50));

  linksSelection = gElement
    .append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", "#d4d4d8")
    .attr("stroke-opacity", 0.6)
    .attr("stroke-width", (d) => d.value * 0.8);

  nodesSelection = gElement
    .append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .style("cursor", "pointer")
    .call(
      d3
        .drag<SVGGElement, GraphNode>()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended),
    )
    .on("mouseenter", (event, d) => {
      hoveredNodeId.value = d.id;
      updateNodeStyles();
    })
    .on("mouseleave", () => {
      hoveredNodeId.value = null;
      updateNodeStyles();
    });

  nodesSelection
    .append("circle")
    .attr("r", 20)
    .attr("fill", (d) => getNodeColor(d))
    .attr("stroke", "#fff")
    .attr("stroke-width", 2)
    .style("filter", "drop-shadow(0 2px 4px rgba(0,0,0,0.1))");

  nodesSelection
    .append("text")
    .text((d) => d.label)
    .attr("x", 24)
    .attr("y", 5)
    .attr("fill", "#3f3f46")
    .attr("font-size", "12px")
    .attr("font-weight", "500")
    .style("pointer-events", "none");

  nodesSelection.on("click", (event, d) => {
    selectedNode.value = d;
    event.stopPropagation();
  });

  svgElement.on("click", () => {
    selectedNode.value = null;
  });

  simulation.on("tick", () => {
    linksSelection
      ?.attr("x1", (d) => (d.source as GraphNode).x || 0)
      .attr("y1", (d) => (d.source as GraphNode).y || 0)
      .attr("x2", (d) => (d.target as GraphNode).x || 0)
      .attr("y2", (d) => (d.target as GraphNode).y || 0);

    nodesSelection?.attr(
      "transform",
      (d) => `translate(${d.x || 0},${d.y || 0})`,
    );
  });

  function dragstarted(
    event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>,
    d: GraphNode,
  ) {
    if (!event.active && simulation) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(
    event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>,
    d: GraphNode,
  ) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragended(
    event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>,
    d: GraphNode,
  ) {
    if (!event.active && simulation) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }
};

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
    svgElement
      .transition()
      .duration(500)
      .call(zoomBehavior.transform, d3.zoomIdentity);
  }
};

let resizeTimeout: ReturnType<typeof setTimeout>;

const handleResize = () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => {
    initGraph();
  }, 100);
};

onMounted(() => {
  loadDemoData();
  window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  if (simulation) simulation.stop();
  clearTimeout(resizeTimeout);
});

const getConnectionCount = (nodeId: string): number => {
  return graphData.value.links.filter((l) => {
    const sourceId = typeof l.source === "string" ? l.source : (l.source as GraphNode).id;
    const targetId = typeof l.target === "string" ? l.target : (l.target as GraphNode).id;
    return sourceId === nodeId || targetId === nodeId;
  }).length;
};

const clearSearch = () => {
  searchQuery.value = "";
};

const totalNodes = computed(() => {
  if (graphStats.value) return graphStats.value.total_nodes;
  return graphData.value.nodes.length;
});

const totalRelationships = computed(() => {
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
  <div class="flex h-full bg-surface-50">
    <div class="flex-1 relative" ref="graphContainer" style="min-height: 400px">
      <svg ref="svgRef" class="w-full h-full" style="display: block"></svg>

      <div class="absolute top-4 left-4 bg-white rounded-xl shadow-lg p-3 z-10">
        <div class="flex items-center gap-2 mb-3">
          <Search :size="16" class="text-surface-400" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search nodes..."
            class="text-sm border-none outline-none bg-transparent w-40"
          />
          <button
            v-if="searchQuery"
            @click="clearSearch"
            class="text-surface-400 hover:text-surface-600"
          >
            ×
          </button>
        </div>
        
        <div class="flex items-center gap-2 mb-3">
          <button
            @click="loadDemoData"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            :class="dataSource === 'demo' ? 'bg-primary-100 text-primary-700' : 'bg-surface-100 text-surface-600 hover:bg-surface-200'"
          >
            <FileText :size="14" />
            Demo
          </button>
          <button
            @click="loadFromDatabase"
            :disabled="isLoading"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            :class="dataSource === 'database' ? 'bg-primary-100 text-primary-700' : 'bg-surface-100 text-surface-600 hover:bg-surface-200'"
          >
            <template v-if="isLoading">
              <Loader2 :size="14" class="animate-spin" />
              Loading...
            </template>
            <template v-else>
              <Database :size="14" />
              Database
            </template>
          </button>
        </div>
        
        <div v-if="loadError" class="text-xs text-red-500 mb-2">
          {{ loadError }}
        </div>
        
        <div class="space-y-1">
          <div
            v-for="(label, index) in legendItems"
            :key="label"
            class="flex items-center gap-2"
          >
            <span
              class="w-3 h-3 rounded-full"
              :style="{ backgroundColor: getColorForLegendItem(index, label) }"
            ></span>
            <span class="text-xs text-surface-600">{{ getLabelDisplayName(label) }}</span>
          </div>
        </div>
        
        <div v-if="dataSource === 'database' && graphStats" class="mt-3 pt-3 border-t border-surface-100">
          <p class="text-xs text-surface-400">
            {{ totalNodes }} nodes, {{ totalRelationships }} relationships
          </p>
        </div>
        
        <p v-if="searchQuery" class="text-xs text-surface-400 mt-2">
          {{ graphData.nodes.filter(isNodeMatching).length }} of
          {{ totalNodes }} nodes match
        </p>
      </div>

      <div class="absolute top-4 right-4 flex flex-col gap-2 z-10">
        <button
          @click="zoomIn"
          class="p-2 bg-white rounded-lg shadow-md hover:bg-surface-50 transition-colors cursor-pointer"
          title="Zoom In"
        >
          <ZoomIn :size="20" class="text-surface-600" />
        </button>
        <button
          @click="zoomOut"
          class="p-2 bg-white rounded-lg shadow-md hover:bg-surface-50 transition-colors cursor-pointer"
          title="Zoom Out"
        >
          <ZoomOut :size="20" class="text-surface-600" />
        </button>
        <button
          @click="resetZoom"
          class="p-2 bg-white rounded-lg shadow-md hover:bg-surface-50 transition-colors cursor-pointer"
          title="Reset View"
        >
          <Maximize2 :size="20" class="text-surface-600" />
        </button>
      </div>

      <div
        v-if="selectedNode"
        class="absolute bottom-4 left-4 bg-white rounded-xl shadow-lg p-4 max-w-xs z-10 animate-fade-in"
      >
        <div class="flex items-center gap-3 mb-2">
          <span
            class="w-4 h-4 rounded-full"
            :style="{ backgroundColor: getNodeColor(selectedNode) }"
          ></span>
          <h3 class="font-semibold text-surface-800">{{ selectedNode.label }}</h3>
        </div>
        
        <p v-if="selectedNode.description" class="text-sm text-surface-600 mb-3">
          {{ selectedNode.description }}
        </p>
        
        <div v-if="selectedNode.labels?.length" class="mb-3">
          <p class="text-xs text-surface-400 uppercase mb-1">Type</p>
          <div class="flex gap-1">
            <span
              v-for="label in selectedNode.labels"
              :key="label"
              class="text-xs px-2 py-0.5 bg-surface-100 text-surface-600 rounded-full"
            >
              {{ label }}
            </span>
          </div>
        </div>
        
        <div v-if="selectedNode.properties && Object.keys(selectedNode.properties).length > 0" class="mb-3">
          <p class="text-xs text-surface-400 uppercase mb-1">Properties</p>
          <div class="space-y-1 text-sm">
            <p v-for="(value, key) in selectedNode.properties" :key="key" class="text-surface-600">
              <span class="font-medium text-surface-500">{{ key }}:</span> {{ formatPropertyValue(value) }}
            </p>
          </div>
        </div>
        
        <div class="mt-3 pt-3 border-t border-surface-100">
          <span class="text-xs text-surface-400">
            Connected to {{ getConnectionCount(selectedNode.id) }} nodes
          </span>
        </div>
      </div>

      <div
        class="absolute bottom-4 right-4 text-xs text-surface-400 bg-white/80 px-3 py-1 rounded-full"
      >
        Drag nodes to reposition · Scroll to zoom · Click for details
      </div>
    </div>
  </div>
</template>
