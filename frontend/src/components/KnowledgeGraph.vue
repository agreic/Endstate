<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from "vue";
import * as d3 from "d3";
import { ZoomIn, ZoomOut, Maximize2, Search, Loader2 } from "lucide-vue-next";
import { fetchGraphData, type ApiNode, type ApiRelationship } from "../services/api";

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
const isLoading = ref(false);
const loadError = ref<string | null>(null);
const graphStats = ref<{ total_nodes: number; total_relationships: number } | null>(null);

const graphData = ref<GraphData>({ nodes: [], links: [] });

const groupColors: Record<string, string> = {
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
  return groupColors[node.labels?.[0] || 'Skill'] || groupColors['Skill'];
};

const getUniqueLabels = (): string[] => {
  const labels = new Set(graphData.value.nodes.map(n => n.labels?.[0] || 'Skill'));
  return Array.from(labels).sort();
};

const getLabelDisplayName = (label: string): string => {
  return label;
};

const getColorForLegendItem = (_index: number, label: string): string => {
  return groupColors[label] || groupColors['Skill'];
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

const loadGraphData = async () => {
  isLoading.value = true;
  loadError.value = null;
  
  try {
    const data = await fetchGraphData();
    
    if (data.total_nodes === 0) {
      loadError.value = "No data found in database.";
      graphData.value = { nodes: [], links: [] };
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
  loadGraphData();
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
        
        <button
          @click="loadGraphData"
          :disabled="isLoading"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors mb-3"
          :class="isLoading ? 'bg-surface-100 text-surface-400' : 'bg-primary-100 text-primary-700 hover:bg-primary-200'"
        >
          <template v-if="isLoading">
            <Loader2 :size="14" class="animate-spin" />
            Loading...
          </template>
          <template v-else>
            Refresh
          </template>
        </button>
        
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
        
        <div v-if="graphStats" class="mt-3 pt-3 border-t border-surface-100">
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
