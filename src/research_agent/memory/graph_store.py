"""Graph-based memory store for long-horizon research intelligence.

Uses NetworkX for the in-process graph with JSON persistence.
Provides node/edge CRUD, neighborhood queries, and lineage traversal
for hypotheses, experiments, proxy metrics, and recommendations.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import networkx as nx

from .models import EdgeType, GraphEdge, GraphNode, NodeStatus, NodeType

logger = logging.getLogger(__name__)


class ResearchGraphStore:
    """Persistent graph memory for the research agent.

    Args:
        persist_path: Path to the JSON file for durable persistence.
            If None, the graph is in-memory only.
    """

    def __init__(self, persist_path: str | Path | None = None) -> None:
        self._graph = nx.DiGraph()
        self._persist_path = Path(persist_path) if persist_path else None
        if self._persist_path and self._persist_path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def add_node(self, node: GraphNode) -> GraphNode:
        """Add a node to the graph. Requires provenance_artifact for auditability."""
        if node.provenance_artifact is None:
            logger.warning(
                "Node %s (%s) added without provenance artifact",
                node.id,
                node.title,
            )
        self._graph.add_node(node.id, **node.to_dict())
        self._persist()
        return node

    def get_node(self, node_id: str) -> GraphNode | None:
        if node_id not in self._graph:
            return None
        attrs = dict(self._graph.nodes[node_id])
        attrs.setdefault("id", node_id)
        return GraphNode.from_dict(attrs)

    def update_node(self, node_id: str, **updates: Any) -> GraphNode | None:
        if node_id not in self._graph:
            return None
        data = dict(self._graph.nodes[node_id])
        for key, value in updates.items():
            if key in data:
                if isinstance(value, (NodeStatus, NodeType)):
                    data[key] = value.value
                else:
                    data[key] = value
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._graph.nodes[node_id].update(data)
        self._persist()
        return GraphNode.from_dict(data)

    def list_nodes(
        self,
        node_type: NodeType | None = None,
        status: NodeStatus | None = None,
    ) -> list[GraphNode]:
        results: list[GraphNode] = []
        for nid, attrs in self._graph.nodes(data=True):
            if node_type and attrs.get("node_type") != node_type.value:
                continue
            if status and attrs.get("status") != status.value:
                continue
            d = dict(attrs)
            d.setdefault("id", nid)
            results.append(GraphNode.from_dict(d))
        return results

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------

    def add_edge(self, edge: GraphEdge) -> GraphEdge:
        """Add a typed directed edge between two nodes."""
        if edge.source_id not in self._graph:
            raise ValueError(f"Source node {edge.source_id} not in graph")
        if edge.target_id not in self._graph:
            raise ValueError(f"Target node {edge.target_id} not in graph")
        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            **edge.to_dict(),
        )
        self._persist()
        return edge

    def get_edges(
        self,
        node_id: str,
        direction: str = "outgoing",
        edge_type: EdgeType | None = None,
    ) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        if direction in ("outgoing", "both"):
            for _, target, attrs in self._graph.out_edges(node_id, data=True):
                if edge_type and attrs.get("edge_type") != edge_type.value:
                    continue
                edges.append(GraphEdge.from_dict(attrs))
        if direction in ("incoming", "both"):
            for source, _, attrs in self._graph.in_edges(node_id, data=True):
                if edge_type and attrs.get("edge_type") != edge_type.value:
                    continue
                edges.append(GraphEdge.from_dict(attrs))
        return edges

    # ------------------------------------------------------------------
    # Neighborhood / lineage queries
    # ------------------------------------------------------------------

    def neighborhood(
        self,
        node_id: str,
        max_depth: int = 2,
    ) -> list[GraphNode]:
        """Return all nodes within max_depth hops of node_id (undirected)."""
        if node_id not in self._graph:
            return []
        undirected = self._graph.to_undirected()
        reachable = nx.single_source_shortest_path_length(
            undirected, node_id, cutoff=max_depth
        )
        result: list[GraphNode] = []
        for nid in reachable:
            if nid == node_id:
                continue
            d = dict(self._graph.nodes[nid])
            d.setdefault("id", nid)
            result.append(GraphNode.from_dict(d))
        return result

    def lineage(self, node_id: str) -> list[GraphNode]:
        """Trace all ancestors via 'derived_from' edges (outgoing from this node)."""
        visited: set[str] = set()
        stack = [node_id]
        result: list[GraphNode] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for _, target, attrs in self._graph.out_edges(current, data=True):
                if attrs.get("edge_type") == EdgeType.DERIVED_FROM.value:
                    d = dict(self._graph.nodes[target])
                    d.setdefault("id", target)
                    result.append(GraphNode.from_dict(d))
                    stack.append(target)
        return result

    def invalidated_hypotheses(self) -> list[GraphNode]:
        """Return all hypotheses with status=invalidated for dedup/avoidance."""
        return self.list_nodes(
            node_type=NodeType.HYPOTHESIS, status=NodeStatus.INVALIDATED
        )

    def strongest_evidence_for(self, node_id: str) -> list[tuple[GraphNode, float]]:
        """Return nodes that support this node, sorted by edge weight descending."""
        edges = self.get_edges(node_id, direction="incoming", edge_type=EdgeType.SUPPORTS)
        pairs: list[tuple[GraphNode, float]] = []
        for e in edges:
            node = self.get_node(e.source_id)
            if node:
                pairs.append((node, e.weight))
        return sorted(pairs, key=lambda p: p[1], reverse=True)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self) -> None:
        if self._persist_path is None:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self._graph, edges="links")
        with open(self._persist_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load(self) -> None:
        assert self._persist_path is not None
        with open(self._persist_path) as f:
            data = json.load(f)
        self._graph = nx.node_link_graph(data, directed=True, edges="links")

    def export_summary(self) -> dict[str, Any]:
        """Return a summary of the graph for diagnostic/reporting purposes."""
        type_counts: dict[str, int] = {}
        for _, attrs in self._graph.nodes(data=True):
            nt = attrs.get("node_type", "unknown")
            type_counts[nt] = type_counts.get(nt, 0) + 1
        return {
            "total_nodes": self._graph.number_of_nodes(),
            "total_edges": self._graph.number_of_edges(),
            "node_type_counts": type_counts,
        }
