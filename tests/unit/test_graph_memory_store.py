"""Unit tests for the graph-based memory store."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.research_agent.memory.graph_store import ResearchGraphStore
from src.research_agent.memory.models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeStatus,
    NodeType,
)


@pytest.fixture
def store(tmp_path: Path) -> ResearchGraphStore:
    return ResearchGraphStore(persist_path=str(tmp_path / "test_graph.json"))


@pytest.fixture
def populated_store(store: ResearchGraphStore) -> ResearchGraphStore:
    h1 = GraphNode(
        id="h1",
        node_type=NodeType.HYPOTHESIS,
        title="Hypothesis 1",
        status=NodeStatus.ACTIVE,
        confidence=0.8,
        provenance_artifact="runs/test/experiment_results/e1.json",
    )
    h2 = GraphNode(
        id="h2",
        node_type=NodeType.HYPOTHESIS,
        title="Hypothesis 2",
        status=NodeStatus.INVALIDATED,
        confidence=0.3,
        provenance_artifact="runs/test/experiment_results/e2.json",
    )
    e1 = GraphNode(
        id="e1",
        node_type=NodeType.EXPERIMENT,
        title="Experiment 1",
        status=NodeStatus.VALIDATED,
        provenance_artifact="runs/test/experiment_results/e1.json",
    )
    r1 = GraphNode(
        id="r1",
        node_type=NodeType.RECOMMENDATION,
        title="Recommendation 1",
        provenance_artifact="runs/test/experiment_results/e1.json",
    )
    store.add_node(h1)
    store.add_node(h2)
    store.add_node(e1)
    store.add_node(r1)
    store.add_edge(GraphEdge(source_id="e1", target_id="h1", edge_type=EdgeType.SUPPORTS, weight=0.8))
    store.add_edge(GraphEdge(source_id="e1", target_id="h2", edge_type=EdgeType.CONTRADICTS, weight=0.3))
    store.add_edge(GraphEdge(source_id="r1", target_id="h1", edge_type=EdgeType.DERIVED_FROM, weight=0.8))
    return store


class TestNodeOperations:
    def test_add_and_get_node(self, store: ResearchGraphStore):
        node = GraphNode(
            id="n1",
            node_type=NodeType.HYPOTHESIS,
            title="Test hypothesis",
            provenance_artifact="test.json",
        )
        store.add_node(node)
        retrieved = store.get_node("n1")
        assert retrieved is not None
        assert retrieved.title == "Test hypothesis"
        assert retrieved.node_type == NodeType.HYPOTHESIS

    def test_get_missing_node_returns_none(self, store: ResearchGraphStore):
        assert store.get_node("nonexistent") is None

    def test_update_node(self, store: ResearchGraphStore):
        node = GraphNode(id="n1", node_type=NodeType.HYPOTHESIS, title="Original", provenance_artifact="t.json")
        store.add_node(node)
        updated = store.update_node("n1", title="Updated", confidence=0.9)
        assert updated is not None
        assert updated.title == "Updated"
        assert updated.confidence == 0.9

    def test_update_missing_returns_none(self, store: ResearchGraphStore):
        assert store.update_node("missing", title="x") is None

    def test_list_nodes_by_type(self, populated_store: ResearchGraphStore):
        hypotheses = populated_store.list_nodes(node_type=NodeType.HYPOTHESIS)
        assert len(hypotheses) == 2

    def test_list_nodes_by_status(self, populated_store: ResearchGraphStore):
        invalidated = populated_store.list_nodes(status=NodeStatus.INVALIDATED)
        assert len(invalidated) == 1
        assert invalidated[0].id == "h2"


class TestEdgeOperations:
    def test_add_and_get_edges(self, populated_store: ResearchGraphStore):
        edges = populated_store.get_edges("e1", direction="outgoing")
        assert len(edges) == 2

    def test_filter_edges_by_type(self, populated_store: ResearchGraphStore):
        supports = populated_store.get_edges(
            "e1", direction="outgoing", edge_type=EdgeType.SUPPORTS
        )
        assert len(supports) == 1
        assert supports[0].target_id == "h1"

    def test_incoming_edges(self, populated_store: ResearchGraphStore):
        incoming = populated_store.get_edges("h1", direction="incoming")
        assert len(incoming) == 2

    def test_edge_requires_valid_nodes(self, store: ResearchGraphStore):
        with pytest.raises(ValueError, match="Source node"):
            store.add_edge(
                GraphEdge(source_id="missing", target_id="also_missing", edge_type=EdgeType.SUPPORTS)
            )


class TestGraphQueries:
    def test_neighborhood(self, populated_store: ResearchGraphStore):
        neighbors = populated_store.neighborhood("h1", max_depth=1)
        neighbor_ids = {n.id for n in neighbors}
        assert "e1" in neighbor_ids
        assert "r1" in neighbor_ids

    def test_neighborhood_depth_2(self, populated_store: ResearchGraphStore):
        neighbors = populated_store.neighborhood("r1", max_depth=2)
        neighbor_ids = {n.id for n in neighbors}
        assert "h1" in neighbor_ids
        assert "e1" in neighbor_ids

    def test_neighborhood_missing_node(self, store: ResearchGraphStore):
        assert store.neighborhood("missing") == []

    def test_lineage(self, populated_store: ResearchGraphStore):
        ancestors = populated_store.lineage("r1")
        ancestor_ids = {n.id for n in ancestors}
        assert "h1" in ancestor_ids

    def test_invalidated_hypotheses(self, populated_store: ResearchGraphStore):
        invalidated = populated_store.invalidated_hypotheses()
        assert len(invalidated) == 1
        assert invalidated[0].id == "h2"

    def test_strongest_evidence(self, populated_store: ResearchGraphStore):
        evidence = populated_store.strongest_evidence_for("h1")
        assert len(evidence) >= 1
        node, weight = evidence[0]
        assert node.id == "e1"
        assert weight == 0.8


class TestPersistence:
    def test_persist_and_reload(self, tmp_path: Path):
        path = str(tmp_path / "persist_test.json")
        store1 = ResearchGraphStore(persist_path=path)
        store1.add_node(
            GraphNode(id="p1", node_type=NodeType.HYPOTHESIS, title="Persist test", provenance_artifact="t.json")
        )
        store1.add_node(
            GraphNode(id="p2", node_type=NodeType.EXPERIMENT, title="Persist exp", provenance_artifact="t.json")
        )
        store1.add_edge(
            GraphEdge(source_id="p2", target_id="p1", edge_type=EdgeType.SUPPORTS)
        )

        store2 = ResearchGraphStore(persist_path=path)
        assert store2.get_node("p1") is not None
        assert store2.get_node("p2") is not None
        edges = store2.get_edges("p2", direction="outgoing")
        assert len(edges) == 1

    def test_in_memory_no_persist(self):
        store = ResearchGraphStore(persist_path=None)
        store.add_node(
            GraphNode(id="mem1", node_type=NodeType.OBSERVATION, provenance_artifact="t.json")
        )
        assert store.get_node("mem1") is not None


class TestExportSummary:
    def test_summary(self, populated_store: ResearchGraphStore):
        summary = populated_store.export_summary()
        assert summary["total_nodes"] == 4
        assert summary["total_edges"] == 3
        assert summary["node_type_counts"]["hypothesis"] == 2
