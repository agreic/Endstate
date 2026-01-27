<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from "vue";
import * as d3 from "d3";
import { ZoomIn, ZoomOut, Maximize2, Search, Loader2, Plus, Trash2, BookOpen } from "lucide-vue-next";
import { fetchGraphData, extractFromText, deleteNode, generateNodeLessons, cancelJob, listProjectJobs, fetchGraphProjects, type ApiNode, type ApiRelationship, type GraphProjectsResponse } from "../services/api";

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
  id?: string;
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
const activeLabelFilter = ref<string | null>(null);
const isLoading = ref(false);
const loadError = ref<string | null>(null);
const graphStats = ref<{ total_nodes: number; total_relationships: number } | null>(null);
const isAddingSample = ref(false);
const showDeleteConfirm = ref(false);
const deletingNode = ref<GraphNode | null>(null);
const deleteMessage = ref("");
const lessonLoading = ref(false);
const lessonError = ref<string | null>(null);
const lessonQueued = ref(false);
const lessonJobIds = ref<string[]>([]);
const lessonCanceling = ref(false);
const lessonJobNodeId = ref<string | null>(null);
const lessonQueuedCount = ref(0);

// Project filter state
const selectedProjectId = ref<string | null>(null);
const showAllProjects = ref(false);
const availableProjects = ref<Array<{ id: string; name: string; created_at: string }>>([]);
const filteredProjectId = ref<string | null>(null);

let lessonPollTimer: number | null = null;
const lessonQueuedText = computed(() => {
  if (lessonQueuedCount.value > 0) {
    return `Queued ${lessonQueuedCount.value} lesson(s). Check the Projects tab.`;
  }
  return "Lesson queued. Check the Projects tab.";
});

const clearLessonPoll = () => {
  if (lessonPollTimer !== null) {
    window.clearTimeout(lessonPollTimer);
    lessonPollTimer = null;
  }
};

const pollLessonJobs = () => {
  clearLessonPoll();
  if (!lessonJobNodeId.value) return;
  lessonPollTimer = window.setTimeout(async () => {
    await refreshLessonJobs(lessonJobNodeId.value || "");
    if (lessonQueued.value) {
      pollLessonJobs();
    } else {
      clearLessonPoll();
    }
  }, 3000);
};

const refreshLessonJobs = async (nodeId: string) => {
  const projectId = localStorage.getItem("endstate_active_project_id") || "";
  if (!projectId) {
    lessonQueued.value = false;
    lessonQueuedCount.value = 0;
    return;
  }
  try {
    const response = await listProjectJobs(projectId, { kind: "lesson", nodeId });
    lessonQueuedCount.value = response.jobs.length;
    lessonQueued.value = response.jobs.length > 0;
    lessonJobIds.value = response.jobs.map((job) => job.job_id);
    lessonJobNodeId.value = response.jobs.length > 0 ? nodeId : null;
    if (!lessonQueued.value) {
      clearLessonPoll();
    }
  } catch (e) {
    lessonQueued.value = false;
    lessonQueuedCount.value = 0;
    clearLessonPoll();
  }
};

const graphData = ref<GraphData>({ nodes: [], links: [] });

const groupColors: Record<string, string> = {
  'Skill': "#0ea5e9",
  'Concept': "#8b5cf6",
  'Topic': "#10b981",
  'Project': "#facc15",
  'Resource': "#ef4444",
  'Tool': "#ec4899",
  'Person': "#6366f1",
  'Domain': "#14b8a6",
  'Assessment': "#f97316",
  'Milestone': "#84cc16",
};

const PRIMARY_LABELS = [
  "Project",
  "Milestone",
  "Skill",
  "Concept",
  "Topic",
  "Resource",
  "Assessment",
  "Tool",
  "Person",
  "Domain",
];

const getPrimaryLabel = (labels?: string[]): string => {
  if (!labels || labels.length === 0) return "Skill";
  const match = PRIMARY_LABELS.find((label) => labels.includes(label));
  return match || labels[0] || "Skill";
};

const getNodeColor = (node: GraphNode, isSelected: boolean = false): string => {
  if (isSelected) {
    return "#ef4444";
  }
  const label = getPrimaryLabel(node.labels);
  return groupColors[label] || groupColors['Skill'];
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
let nodesSelection: d3.Selection<SVGGElement, GraphNode, SVGGElement, unknown> | null = null;
let linksSelection: d3.Selection<SVGLineElement, GraphLink, SVGGElement, unknown> | null = null;

const formatPropertyValue = (value: any): string => {
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value);
  }
  return String(value);
};

const getDisplayProperties = (node: GraphNode): Array<{ key: string; value: any }> => {
  const hiddenKeys = new Set(["created_at", "updated_at", "is_default"]);
  return Object.entries(node.properties || {})
    .filter(([key]) => !hiddenKeys.has(key))
    .map(([key, value]) => ({ key, value }));
};

const loadProjects = async () => {
  try {
    const data = await fetchGraphProjects();
    availableProjects.value = data.projects;
  } catch (error) {
    console.error('Failed to load projects:', error);
  }
};

const loadGraphData = async () => {
  isLoading.value = true;
  loadError.value = null;
  
  try {
    // Determine which project_id to pass
    let projectIdParam: string | undefined;
    if (showAllProjects.value) {
      projectIdParam = 'all';
    } else if (selectedProjectId.value) {
      projectIdParam = selectedProjectId.value;
    }
    // If neither, let backend auto-select most recent project
    
    const data = await fetchGraphData(projectIdParam);
    
    // Store the active filtered project ID from response
    filteredProjectId.value = data.filtered_project_id || null;
    
    if (data.total_nodes === 0) {
      if (graphData.value.nodes.length > 0) {
        loadError.value = "No nodes returned. Keeping previous graph.";
        isLoading.value = false;
        return;
      }
      graphData.value = { nodes: [], links: [] };
      graphStats.value = null;
      isLoading.value = false;
      return;
    }

    // Stop any existing simulation only after a successful fetch
    if (simulation) {
      simulation.stop();
      simulation = null;
    }
    if (svgElement) {
      svgElement.selectAll("*").remove();
    }
    selectedNode.value = null;
    
    graphStats.value = {
      total_nodes: data.total_nodes,
      total_relationships: data.total_relationships,
    };
    
    graphData.value.nodes = data.nodes.map((item: ApiNode) => {
      return {
        id: item.id || String(Math.random()),
        group: 1,
        label: item.properties.name || item.labels?.[0] || 'Unknown',
        description: item.properties.description,
        labels: item.labels,
        properties: item.properties,
      };
    });
    
    graphData.value.links = data.relationships.map((rel: ApiRelationship, index: number) => ({
      source: rel.source,
      target: rel.target,
      value: 1,
      type: rel.type,
      label: rel.type,
      id: `link-${index}`,
    }));
    
    setTimeout(() => {
      try {
        initGraph();
      } catch (e) {
        console.error("Failed to initialize graph visualization:", e);
        loadError.value = "Failed to render graph visualization";
      } finally {
        isLoading.value = false;
      }
    }, 200);
    
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Failed to load graph data';
    isLoading.value = false;
  }
};

const addSampleData = async () => {
  isAddingSample.value = true;
  try {
    const sampleText = `
      Machine Learning is a subset of AI that enables systems to learn from data.
      Deep Learning uses neural networks with multiple layers.
      Python is a programming language popular for AI development.
      TensorFlow is an open source ML framework by Google.
      PyTorch is an open source ML framework by Meta.
      Computer Vision enables computers to see and understand images.
      Natural Language Processing processes human language by computers.
      Neural Networks are computing systems inspired by biological brains.
      Large Language Models like GPT are transformer-based models.
    `;
    await extractFromText(sampleText);
    await loadGraphData();
  } catch (error) {
    loadError.value = "Failed to add sample data";
  } finally {
    isAddingSample.value = false;
  }
};

const confirmDelete = (node: GraphNode) => {
  const connections = getConnectionCount(node.id);
  deletingNode.value = node;
  deleteMessage.value = connections > 0
    ? `Delete "${node.label}" and its ${connections} connection${connections === 1 ? '' : 's'}?`
    : `Delete "${node.label}"?`;
  showDeleteConfirm.value = true;
};

const handleDelete = async () => {
  if (!deletingNode.value) return;
  
  const nodeIdToDelete = deletingNode.value.id;
  const nodeLabel = deletingNode.value.label;
  showDeleteConfirm.value = false;
  deletingNode.value = null;
  selectedNode.value = null;
  
  // Stop current simulation to clean up
  if (simulation) {
    simulation.stop();
    simulation = null;
  }
  
  isLoading.value = true;
  
  try {
    await deleteNode(nodeIdToDelete);
    await loadGraphData();
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : `Failed to delete "${nodeLabel}"`;
    isLoading.value = false;
  }
};

const cancelDelete = () => {
  showDeleteConfirm.value = false;
  deletingNode.value = null;
};

const loadLesson = async () => {
  if (!selectedNode.value) return;
  lessonLoading.value = true;
  lessonError.value = null;
  lessonQueued.value = false;
  lessonJobIds.value = [];
  lessonJobNodeId.value = null;
  lessonQueuedCount.value = 0;
  clearLessonPoll();
  try {
    const response = await generateNodeLessons(selectedNode.value.id);
    const jobs = response.jobs || [];
    const skipped = response.skipped || [];
    lessonQueued.value = jobs.length > 0 || skipped.length > 0;
    lessonJobNodeId.value = selectedNode.value.id;
    lessonJobIds.value = jobs.map((job) => job.job_id);
    lessonQueuedCount.value = jobs.length + skipped.length;
    jobs.forEach((job) => {
      window.dispatchEvent(new CustomEvent("endstate:lesson-queued", { detail: { projectId: job.project_id } }));
    });
    skipped.forEach((entry) => {
      window.dispatchEvent(new CustomEvent("endstate:lesson-created", { detail: { projectId: entry.project_id } }));
    });
    if (lessonQueued.value) {
      pollLessonJobs();
    }
  } catch (e) {
    lessonError.value = "Failed to generate lesson";
  } finally {
    lessonLoading.value = false;
  }
};

const cancelLessonJob = async () => {
  if (lessonJobIds.value.length === 0) return;
  lessonCanceling.value = true;
  try {
    await Promise.allSettled(lessonJobIds.value.map((jobId) => cancelJob(jobId)));
    lessonQueued.value = false;
    lessonJobIds.value = [];
    lessonJobNodeId.value = null;
    lessonQueuedCount.value = 0;
    clearLessonPoll();
  } catch (e) {
    lessonError.value = "Failed to cancel lesson generation";
  } finally {
    lessonCanceling.value = false;
  }
};

const isNodeMatching = (node: GraphNode): boolean => {
  if (!searchQuery.value) return true;
  const query = searchQuery.value.toLowerCase();
  return (
    node.label.toLowerCase().includes(query) ||
    node.description?.toLowerCase().includes(query) ||
    node.id === query ||
    (node.labels?.some(l => l.toLowerCase().includes(query)) ?? false)
  );
};

const isNodeInActiveLabel = (node: GraphNode): boolean => {
  if (!activeLabelFilter.value) return true;
  return getPrimaryLabel(node.labels) === activeLabelFilter.value;
};

const updateNodeStyles = () => {
  if (!nodesSelection) return;

  nodesSelection
    .selectAll("circle")
    .attr("fill", (d) => {
      const node = d as GraphNode;
      const isMatch = isNodeMatching(node);
      const isInLabel = isNodeInActiveLabel(node);
      const isHovered = hoveredNodeId.value === node.id;
      const isSelected = selectedNode.value?.id === node.id;
      const baseColor = getNodeColor(node, isSelected);

      if (!isMatch || !isInLabel) {
        return "#d4d4d8";
      }
      if (isHovered || isSelected) {
        return d3.color(baseColor)?.brighter(0.3)?.toString() || baseColor;
      }
      return baseColor;
    })
    .attr("stroke", (d) => {
      const node = d as GraphNode;
      return selectedNode.value?.id === node.id ? "#dc2626" : "#fff";
    })
    .attr("stroke-width", (d) => {
      const node = d as GraphNode;
      return selectedNode.value?.id === node.id ? 4 : 2;
    });

  nodesSelection
    .selectAll("text")
    .attr("opacity", (d) => {
      const node = d as GraphNode;
      return isNodeMatching(node) && isNodeInActiveLabel(node) ? 1 : 0.3;
    })
    .attr("font-weight", (d) => {
      const node = d as GraphNode;
      return hoveredNodeId.value === node.id || selectedNode.value?.id === node.id ? "700" : "500";
    });
};

const updateLinkStyles = () => {
  if (!linksSelection) return;

  linksSelection
    .attr("opacity", (d) => {
      const source = typeof d.source === "string" ? d.source : d.source.id;
      const target = typeof d.target === "string" ? d.target : d.target.id;
      const sourceNode = graphData.value.nodes.find((n) => n.id === source);
      const targetNode = graphData.value.nodes.find((n) => n.id === target);
      if (!sourceNode || !targetNode) return 0.2;
      const labelMatch = !activeLabelFilter.value || (
        getPrimaryLabel(sourceNode.labels) === activeLabelFilter.value &&
        getPrimaryLabel(targetNode.labels) === activeLabelFilter.value
      );
      return labelMatch ? 0.6 : 0.15;
    })
    .attr("stroke", "#d4d4d8");
};

watch(searchQuery, () => {
  updateNodeStyles();
  updateLinkStyles();
});

const showProperties = ref(false);

watch(selectedNode, async () => {
  lessonError.value = null;
  lessonLoading.value = false;
  lessonQueued.value = false;
  lessonJobIds.value = [];
  lessonJobNodeId.value = null;
  lessonQueuedCount.value = 0;
  showProperties.value = false;
  clearLessonPoll();
  if (selectedNode.value) {
    await refreshLessonJobs(selectedNode.value.id);
    if (lessonQueued.value) {
      pollLessonJobs();
    }
  }
});

watch(activeLabelFilter, () => {
  updateNodeStyles();
  updateLinkStyles();
});

const initGraph = () => {
  if (!graphContainer.value || !svgRef.value) {
    console.warn("[Graph] Container not available");
    return;
  }

  const width = graphContainer.value.clientWidth;
  const height = graphContainer.value.clientHeight;

  if (width === 0 || height === 0) {
    console.warn("[Graph] Invalid dimensions", { width, height });
    return;
  }

  console.log("[Graph] Initializing with", graphData.value.nodes.length, "nodes");
  const startTime = performance.now();

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
        if (nodesSelection) {
          const labelOpacity = event.transform.k < 0.6 ? 0 : 1;
          nodesSelection.selectAll("text").attr("opacity", labelOpacity);
        }
      }
    });

  svgElement.call(zoomBehavior);
  svgElement.on("dblclick.zoom", null);

  const nodes: GraphNode[] = graphData.value.nodes.map((d) => ({
    ...d,
    fx: null,
    fy: null,
  }));
  
  const nodeIds = new Set(nodes.map(n => n.id));
  const links: GraphLink[] = graphData.value.links
    .filter(link => {
      const sourceId = typeof link.source === 'object' ? (link.source as any).id : link.source;
      const targetId = typeof link.target === 'object' ? (link.target as any).id : link.target;
      return nodeIds.has(sourceId) && nodeIds.has(targetId);
    })
    .map((d) => ({ ...d }));

  for (const link of links) {
    const sourceNode = nodes.find((n) => n.id === link.source || (link.source as GraphNode)?.id === link.source);
    const targetNode = nodes.find((n) => n.id === link.target || (link.target as GraphNode)?.id === link.target);
    if (sourceNode) link.source = sourceNode;
    if (targetNode) link.target = targetNode;
  }

  simulation = d3
    .forceSimulation<GraphNode>(nodes)
    .alphaDecay(0.05)
    .velocityDecay(0.4)
    .force(
      "link",
      d3
        .forceLink<GraphNode, GraphLink>(links)
        .id((d) => d.id)
        .distance(100),
    )
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(40));

  linksSelection = gElement
    .append("g")
    .selectAll<SVGLineElement, GraphLink>("line")
    .data(links)
    .join("line")
    .attr("stroke", "#d4d4d8")
    .attr("stroke-opacity", 0.6)
    .attr("stroke-width", (d) => d.value * 0.8);

  nodesSelection = gElement
    .append("g")
    .selectAll<SVGGElement, GraphNode>("g")
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
    .on("mouseenter", (_event, d) => {
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
    .attr("paint-order", "stroke")
    .attr("stroke", "white")
    .attr("stroke-width", 3)
    .style("pointer-events", "none");

  nodesSelection.on("click", (event, d) => {
    selectedNode.value = selectedNode.value?.id === d.id ? null : d;
    event.stopPropagation();
    updateNodeStyles();
  });

  svgElement.on("click", () => {
    if (selectedNode.value) {
      selectedNode.value = null;
      updateNodeStyles();
    }
  });

  simulation.on("tick", () => {
    if (!linksSelection || !nodesSelection) return;

    linksSelection
      .attr("x1", (d) => (d.source as GraphNode).x || 0)
      .attr("y1", (d) => (d.source as GraphNode).y || 0)
      .attr("x2", (d) => (d.target as GraphNode).x || 0)
      .attr("y2", (d) => (d.target as GraphNode).y || 0);

    nodesSelection.attr(
      "transform",
      (d) => `translate(${d.x || 0},${d.y || 0})`,
    );
  });

  simulation.on("end", () => {
    const duration = performance.now() - startTime;
    console.log(`[Graph] Simulation stabilized in ${duration.toFixed(0)}ms`);
  });

  setTimeout(() => {
    if (simulation && simulation.alpha() > 0.01) {
      console.log("[Graph] Forcing simulation stop after timeout");
      simulation.stop();
    }
  }, 5000);

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
  loadProjects();
  loadGraphData();
  window.addEventListener("resize", handleResize);
});

// Watch for project filter changes and reload graph
watch([selectedProjectId, showAllProjects], () => {
  loadGraphData();
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  if (simulation) simulation.stop();
  clearTimeout(resizeTimeout);
  clearLessonPoll();
});

const getConnectionCount = (nodeId: string): number => {
  const neighbors = new Set<string>();
  graphData.value.links.forEach((l) => {
    const sourceId = typeof l.source === "string" ? l.source : (l.source as GraphNode).id;
    const targetId = typeof l.target === "string" ? l.target : (l.target as GraphNode).id;
    if (sourceId === nodeId) neighbors.add(targetId);
    if (targetId === nodeId) neighbors.add(sourceId);
  });
  return neighbors.size;
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
  const labels = new Set(graphData.value.nodes.map(n => getPrimaryLabel(n.labels)));
  return Array.from(labels).sort();
});

const toggleLabelFilter = (label: string) => {
  activeLabelFilter.value = activeLabelFilter.value === label ? null : label;
};

const getDisplayLabels = (labels?: string[]): string[] => {
  if (!labels) return [];
  return labels.filter((label) => label !== "__Entity__");
};

const isProjectNode = computed(() => {
  if (!selectedNode.value) return false;
  return selectedNode.value.labels?.includes("Project") || selectedNode.value.labels?.includes("ProjectSummary");
});

const isRemediationNode = computed(() => {
  if (!selectedNode.value) return false;
  return selectedNode.value.properties?.is_remediation === true || 
         selectedNode.value.properties?.node_type === 'remediation';
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
        
        <!-- Project Filter -->
        <div class="mb-3 border-t border-surface-100 pt-3">
          <label class="flex items-center gap-2 text-xs text-surface-600 mb-2 cursor-pointer">
            <input
              type="checkbox"
              v-model="showAllProjects"
              class="form-checkbox rounded text-primary-500"
            />
            <span>Show All Projects</span>
          </label>
          
          <select
            v-if="!showAllProjects && availableProjects.length > 0"
            v-model="selectedProjectId"
            class="w-full text-xs border border-surface-200 rounded-lg p-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-primary-300"
          >
            <option :value="null">Latest Project</option>
            <option v-for="project in availableProjects" :key="project.id" :value="project.id">
              {{ project.name || project.id }}
            </option>
          </select>
          
          <p v-if="filteredProjectId && !showAllProjects" class="text-xs text-surface-400 mt-1">
            Showing: {{ availableProjects.find(p => p.id === filteredProjectId)?.name || filteredProjectId }}
          </p>
        </div>
        
        <div v-if="loadError" class="text-xs text-red-500 mb-2">
          {{ loadError }}
        </div>
        
        <div v-if="graphData.nodes.length === 0 && !isLoading" class="mb-3">
          <p class="text-xs text-surface-500 mb-2">No data in database</p>
          <button
            @click="addSampleData"
            :disabled="isAddingSample"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-100 text-emerald-700 hover:bg-emerald-200 transition-colors"
          >
            <template v-if="isAddingSample">
              <Loader2 :size="14" class="animate-spin" />
              Adding...
            </template>
            <template v-else>
              <Plus :size="14" />
              Add Sample Data
            </template>
          </button>
        </div>
        
        <div class="space-y-1">
          <button
            v-for="(label, index) in legendItems"
            :key="label"
            @click="toggleLabelFilter(label)"
            class="flex items-center gap-2 w-full text-left"
          >
            <span
              class="w-3 h-3 rounded-full"
              :style="{ backgroundColor: getColorForLegendItem(index, label) }"
            ></span>
            <span
              class="text-xs"
              :class="activeLabelFilter === label ? 'text-surface-900 font-semibold' : 'text-surface-600'"
            >
              {{ getLabelDisplayName(label) }}
            </span>
          </button>
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
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-3">
            <span
              class="w-4 h-4 rounded-full"
              :style="{ backgroundColor: getNodeColor(selectedNode, true) }"
            ></span>
            <h3 class="font-semibold text-surface-800">{{ selectedNode.label }}</h3>
          </div>
          <button
            @click="confirmDelete(selectedNode)"
            class="p-1 rounded hover:bg-red-100 text-red-500 transition-colors"
            title="Delete node"
          >
            <Trash2 :size="16" />
          </button>
        </div>
        
        <p v-if="selectedNode.description" class="text-sm text-surface-600 mb-3">
          {{ selectedNode.description }}
        </p>
        
        <div v-if="getDisplayLabels(selectedNode.labels).length" class="mb-3">
          <p class="text-xs text-surface-400 uppercase mb-1">Type</p>
          <div class="flex gap-1 flex-wrap">
            <span
              v-for="label in getDisplayLabels(selectedNode.labels)"
              :key="label"
              class="text-xs px-2 py-0.5 bg-surface-100 text-surface-600 rounded-full"
            >
              {{ label }}
            </span>
          </div>
        </div>

        <div v-if="selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && !isProjectNode" class="mb-3">
          <button
            @click="showProperties = !showProperties"
            class="flex items-center gap-2 text-xs text-surface-500 font-medium"
          >
            <span>Properties</span>
            <span class="text-surface-400">{{ showProperties ? "Hide" : "Show" }}</span>
          </button>
          <div v-if="showProperties" class="mt-2 space-y-1 text-sm">
            <p v-for="item in getDisplayProperties(selectedNode)" :key="item.key" class="text-surface-600">
              <span class="font-medium text-surface-500">{{ item.key }}:</span> {{ formatPropertyValue(item.value) }}
            </p>
          </div>
        </div>

        <div class="mt-3" v-if="!isProjectNode && !isRemediationNode">
          <button
            @click="loadLesson"
            :disabled="lessonLoading"
            class="w-full flex items-center justify-center gap-2 text-xs font-medium px-3 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 transition-colors disabled:opacity-60"
          >
            <BookOpen :size="14" />
            {{ lessonLoading ? 'Generating lesson...' : 'Generate lesson' }}
          </button>
          <p v-if="lessonError" class="mt-2 text-xs text-red-500">{{ lessonError }}</p>
          <p v-else-if="lessonQueued" class="mt-2 text-xs text-surface-500">
            {{ lessonQueuedText }}
          </p>
          <button
            v-if="lessonJobIds.length > 0 && lessonJobNodeId === selectedNode.id"
            @click="cancelLessonJob"
            :disabled="lessonCanceling"
            class="mt-2 w-full text-xs font-medium px-3 py-2 rounded-lg border border-surface-200 text-surface-600 hover:bg-surface-50 transition-colors disabled:opacity-60"
          >
            {{ lessonCanceling ? 'Canceling...' : 'Cancel lesson generation' }}
          </button>
        </div>
        
        <div v-if="isProjectNode" class="p-3 bg-surface-50 rounded-xl border border-surface-100">
          <p class="text-xs text-surface-500 leading-relaxed">
            This is your project node. It represents the target goal of your learning journey.
          </p>
        </div>
        
        <div class="mt-3 pt-3 border-t border-surface-100">
          <span class="text-xs text-surface-400">
            Connected to {{ getConnectionCount(selectedNode.id) }} node{{ getConnectionCount(selectedNode.id) === 1 ? '' : 's' }}
          </span>
        </div>
      </div>

      <div
        class="absolute bottom-4 right-4 text-xs text-surface-400 bg-white/80 px-3 py-1 rounded-full"
      >
        Drag nodes to reposition · Scroll to zoom · Click node for details · Red = Selected
      </div>
    </div>

    <div
      v-if="showDeleteConfirm"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
    >
      <div class="bg-white rounded-xl shadow-xl p-6 max-w-sm mx-4">
        <div class="flex items-center gap-3 mb-4">
          <div class="p-2 bg-red-100 rounded-full">
            <Trash2 :size="24" class="text-red-500" />
          </div>
          <h3 class="text-lg font-semibold text-surface-800">Delete Node?</h3>
        </div>
        <p class="text-surface-600 mb-6">{{ deleteMessage }}</p>
        <div class="flex gap-3 justify-end">
          <button
            @click="cancelDelete"
            class="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            @click="handleDelete"
            class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
