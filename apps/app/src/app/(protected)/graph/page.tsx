"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  GitFork,
  Search,
  Filter,
  X,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface GraphNode {
  id: string;
  node_type: string;
  title: string;
  description: string;
  status: string;
  confidence: number;
  provenance_artifact?: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}

interface GraphEdge {
  source_id: string;
  target_id: string;
  edge_type: string;
  weight: number;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  summary: { total_nodes: number; total_edges: number; node_type_counts: Record<string, number> };
}

const NODE_COLORS: Record<string, string> = {
  hypothesis: "var(--color-node-hypothesis)",
  experiment: "var(--color-node-experiment)",
  recommendation: "var(--color-node-recommendation)",
  observation: "var(--color-node-observation)",
  proxy_metric: "var(--color-node-proxy)",
};

const EDGE_STYLES: Record<string, { color: string; label: string }> = {
  supports: { color: "var(--color-positive)", label: "supports" },
  contradicts: { color: "var(--color-negative)", label: "contradicts" },
  derived_from: { color: "var(--color-info)", label: "derived from" },
  supersedes: { color: "var(--color-warning)", label: "supersedes" },
  tested_by: { color: "var(--color-node-experiment)", label: "tested by" },
};

export default function GraphPage() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [filterType, setFilterType] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    fetch("/api/agent/graph")
      .then((r) => r.json())
      .then(setGraphData)
      .catch(() => setGraphData({ nodes: [], edges: [], summary: { total_nodes: 0, total_edges: 0, node_type_counts: {} } }))
      .finally(() => setLoading(false));
  }, []);

  const filteredNodes = graphData?.nodes.filter((n) => {
    if (filterType !== "all" && n.node_type !== filterType) return false;
    if (filterStatus !== "all" && n.status !== filterStatus) return false;
    return true;
  }) || [];

  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));
  const filteredEdges = graphData?.edges.filter(
    (e) => filteredNodeIds.has(e.source_id) && filteredNodeIds.has(e.target_id)
  ) || [];

  const nodeTypes = [...new Set(graphData?.nodes.map((n) => n.node_type) || [])];
  const statuses = [...new Set(graphData?.nodes.map((n) => n.status) || [])];

  return (
    <div className="flex h-full">
      {/* Graph area */}
      <div className="flex-1 flex flex-col">
        <header className="flex items-center justify-between border-b border-[var(--color-dark-border)] px-6 py-4">
          <div>
            <h1 className="text-xl font-semibold">Knowledge Graph</h1>
            <p className="text-sm text-[var(--color-text-muted)]">
              {graphData?.summary.total_nodes || 0} nodes, {graphData?.summary.total_edges || 0} edges
            </p>
          </div>
          <div className="flex gap-2">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark-alt)] px-3 py-1.5 text-xs"
            >
              <option value="all">All types</option>
              {nodeTypes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark-alt)] px-3 py-1.5 text-xs"
            >
              <option value="all">All statuses</option>
              {statuses.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </header>

        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">
              Loading graph...
            </div>
          ) : filteredNodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-[var(--color-text-muted)] gap-2">
              <GitFork size={48} strokeWidth={1} />
              <p className="text-sm">No graph data yet.</p>
              <p className="text-xs">Run a research session to populate the knowledge graph.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 auto-rows-min">
              {filteredNodes.map((node) => (
                <button
                  key={node.id}
                  onClick={() => setSelectedNode(node)}
                  className={cn(
                    "text-left rounded-lg border p-4 transition-colors",
                    selectedNode?.id === node.id
                      ? "border-[var(--color-accent)] bg-[var(--color-accent-bg)]"
                      : "border-[var(--color-dark-border)] bg-[var(--color-dark-card)] hover:border-[var(--color-dark-hover)]"
                  )}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: NODE_COLORS[node.node_type] || "#666" }}
                    />
                    <span className="text-xs text-[var(--color-text-muted)] uppercase tracking-wide">
                      {node.node_type}
                    </span>
                    <span
                      className={cn(
                        "ml-auto text-xs rounded-full px-1.5 py-0.5",
                        node.status === "validated"
                          ? "text-[var(--color-positive)] bg-[var(--color-positive)]/10"
                          : node.status === "invalidated"
                            ? "text-[var(--color-negative)] bg-[var(--color-negative)]/10"
                            : "text-[var(--color-text-muted)] bg-[var(--color-dark)]"
                      )}
                    >
                      {node.status}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-[var(--color-text-primary)] line-clamp-2">
                    {node.title || node.id}
                  </p>
                  {node.confidence > 0 && (
                    <p className="text-xs text-[var(--color-text-muted)] mt-1">
                      Confidence: {(node.confidence * 100).toFixed(0)}%
                    </p>
                  )}
                </button>
              ))}
            </div>
          )}

          {/* Edge legend */}
          {filteredEdges.length > 0 && (
            <div className="mt-6 flex flex-wrap gap-4">
              {Object.entries(EDGE_STYLES).map(([type, style]) => {
                const count = filteredEdges.filter((e) => e.edge_type === type).length;
                if (count === 0) return null;
                return (
                  <div key={type} className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)]">
                    <span className="h-0.5 w-4 rounded" style={{ backgroundColor: style.color }} />
                    {style.label} ({count})
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Detail panel */}
      {selectedNode && (
        <div className="w-80 border-l border-[var(--color-dark-border)] bg-[var(--color-dark-alt)] overflow-y-auto">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-dark-border)]">
            <h3 className="text-sm font-medium">Node Detail</h3>
            <button onClick={() => setSelectedNode(null)} className="text-[var(--color-text-muted)]">
              <X size={16} />
            </button>
          </div>
          <div className="p-4 space-y-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: NODE_COLORS[selectedNode.node_type] || "#666" }}
                />
                <span className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                  {selectedNode.node_type}
                </span>
              </div>
              <h4 className="text-sm font-medium">{selectedNode.title || selectedNode.id}</h4>
            </div>

            <div>
              <p className="text-xs text-[var(--color-text-muted)] mb-1">Description</p>
              <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                {selectedNode.description || "No description"}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-[var(--color-text-muted)]">Status</p>
                <p className="text-sm">{selectedNode.status}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--color-text-muted)]">Confidence</p>
                <p className="text-sm">{(selectedNode.confidence * 100).toFixed(0)}%</p>
              </div>
              <div>
                <p className="text-xs text-[var(--color-text-muted)]">ID</p>
                <p className="text-xs font-mono text-[var(--color-text-secondary)]">{selectedNode.id}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--color-text-muted)]">Created</p>
                <p className="text-xs text-[var(--color-text-secondary)]">
                  {selectedNode.created_at ? new Date(selectedNode.created_at).toLocaleDateString() : "—"}
                </p>
              </div>
            </div>

            {selectedNode.provenance_artifact && (
              <div>
                <p className="text-xs text-[var(--color-text-muted)] mb-1">Provenance</p>
                <p className="text-xs font-mono text-[var(--color-text-secondary)] break-all">
                  {selectedNode.provenance_artifact}
                </p>
              </div>
            )}

            {/* Connected edges */}
            <div>
              <p className="text-xs text-[var(--color-text-muted)] mb-2">Connections</p>
              <div className="space-y-1">
                {filteredEdges
                  .filter((e) => e.source_id === selectedNode.id || e.target_id === selectedNode.id)
                  .map((e, i) => {
                    const isSource = e.source_id === selectedNode.id;
                    const otherId = isSource ? e.target_id : e.source_id;
                    const style = EDGE_STYLES[e.edge_type];
                    return (
                      <div
                        key={i}
                        className="flex items-center gap-2 rounded border border-[var(--color-dark-border)] bg-[var(--color-dark)] px-2 py-1.5 text-xs"
                      >
                        <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: style?.color || "#666" }} />
                        <span className="text-[var(--color-text-muted)]">
                          {isSource ? "→" : "←"} {style?.label || e.edge_type}
                        </span>
                        <button
                          onClick={() => {
                            const target = filteredNodes.find((n) => n.id === otherId);
                            if (target) setSelectedNode(target);
                          }}
                          className="ml-auto font-mono text-[var(--color-accent)] hover:underline"
                        >
                          {otherId.slice(0, 8)}
                        </button>
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
