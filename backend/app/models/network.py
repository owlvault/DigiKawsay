"""Network analysis models for RunaMap."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
import uuid

from app.models.base import TimestampMixin


# --- Node and Edge Types ---
class NodeType:
    PARTICIPANT = "participant"
    THEME = "theme"
    TENSION = "tension"
    SYMBOL = "symbol"
    CATEGORY = "category"


class EdgeType:
    HABLA_DE = "habla_de"
    CO_OCURRE = "co_ocurre"
    CONSULTA = "consulta"
    COLABORA = "colabora"
    COMPARTE_TEMA = "comparte_tema"


# --- Network Entities ---
class NetworkNode(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    campaign_id: str
    node_type: str
    label: str
    pseudonym_id: Optional[str] = None
    source_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    degree_in: int = 0
    degree_out: int = 0
    betweenness: float = 0.0
    clustering_coef: float = 0.0
    community_id: Optional[int] = None


class NetworkEdge(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    campaign_id: str
    source_node_id: str
    target_node_id: str
    edge_type: str
    weight: float = 1.0
    evidence_links: List[str] = []
    metadata: Dict[str, Any] = {}


class NetworkSnapshot(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    campaign_id: str
    name: str
    description: Optional[str] = None
    node_count: int = 0
    edge_count: int = 0
    community_count: int = 0
    metrics: Dict[str, Any] = {}
    created_by: str


# --- Metrics and Responses ---
class NetworkMetrics(BaseModel):
    total_nodes: int = 0
    total_edges: int = 0
    density: float = 0.0
    avg_clustering: float = 0.0
    num_communities: int = 0
    top_brokers: List[Dict[str, Any]] = []
    communities: List[Dict[str, Any]] = []
    nodes_by_type: Dict[str, int] = {}
    edges_by_type: Dict[str, int] = {}


class GraphResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    metrics: NetworkMetrics
    snapshot_id: Optional[str] = None


class GenerateNetworkRequest(BaseModel):
    campaign_id: str
    include_participant_theme: bool = True
    include_theme_cooccurrence: bool = True
    include_participant_similarity: bool = True
    min_edge_weight: float = 1.0
    snapshot_name: Optional[str] = None
