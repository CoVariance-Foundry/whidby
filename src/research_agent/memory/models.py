"""Typed node and edge schemas for the research knowledge graph.

Node types: hypothesis, experiment, proxy_metric, recommendation, observation.
Edge types: supports, contradicts, derived_from, supersedes, tested_by.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    HYPOTHESIS = "hypothesis"
    EXPERIMENT = "experiment"
    PROXY_METRIC = "proxy_metric"
    RECOMMENDATION = "recommendation"
    OBSERVATION = "observation"


class EdgeType(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DERIVED_FROM = "derived_from"
    SUPERSEDES = "supersedes"
    TESTED_BY = "tested_by"


class NodeStatus(str, Enum):
    ACTIVE = "active"
    VALIDATED = "validated"
    INVALIDATED = "invalidated"
    SUPERSEDED = "superseded"
    PENDING = "pending"


@dataclass
class GraphNode:
    """A node in the research knowledge graph."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: NodeType = NodeType.OBSERVATION
    title: str = ""
    description: str = ""
    status: NodeStatus = NodeStatus.ACTIVE
    confidence: float = 0.0
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance_artifact: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "confidence": self.confidence,
            "version": self.version,
            "metadata": self.metadata,
            "provenance_artifact": self.provenance_artifact,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphNode:
        return cls(
            id=data["id"],
            node_type=NodeType(data["node_type"]),
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=NodeStatus(data.get("status", "active")),
            confidence=data.get("confidence", 0.0),
            version=data.get("version", 1),
            metadata=data.get("metadata", {}),
            provenance_artifact=data.get("provenance_artifact"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class GraphEdge:
    """A typed, directed edge in the research knowledge graph."""

    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphEdge:
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            edge_type=EdgeType(data["edge_type"]),
            weight=data.get("weight", 1.0),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
        )
