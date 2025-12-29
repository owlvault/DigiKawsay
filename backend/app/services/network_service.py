"""Network Analysis Service for RunaMap (SNA)."""

import uuid
import logging
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Optional

import networkx as nx
from community import community_louvain

from app.database import get_database
from app.utils.serializers import serialize_document
from app.models.network import NodeType, EdgeType
from app.models.network import NetworkSnapshot, NetworkMetrics

logger = logging.getLogger(__name__)


class NetworkAnalysisService:
    """Service for Social Network Analysis (SNA) - RunaMap."""
    
    @staticmethod
    async def build_graph_from_campaign(
        campaign_id: str,
        tenant_id: str,
        include_participant_theme: bool = True,
        include_theme_cooccurrence: bool = True,
        include_participant_similarity: bool = True,
        min_edge_weight: float = 1.0
    ) -> Tuple[List[Dict], List[Dict]]:
        """Build network graph from campaign data."""
        db = get_database()
        
        nodes = []
        edges = []
        node_map = {}  # source_id -> node_id
        
        # Get all insights and transcripts for the campaign
        insights = await db.insights.find(
            {"campaign_id": campaign_id, "is_suppressed": {"$ne": True}},
            {"_id": 0}
        ).to_list(500)
        
        transcripts = await db.transcripts.find(
            {"campaign_id": campaign_id},
            {"_id": 0}
        ).to_list(500)
        
        # Get taxonomy categories
        categories = await db.taxonomy_categories.find(
            {"tenant_id": tenant_id, "is_active": True},
            {"_id": 0}
        ).to_list(100)
        
        # Build participant nodes from transcripts
        participant_themes = defaultdict(set)  # pseudonym_id -> set of category_ids
        
        for transcript in transcripts:
            pseudonym_id = transcript.get("pseudonym_id")
            if not pseudonym_id:
                continue
            
            if pseudonym_id not in node_map:
                node_id = str(uuid.uuid4())
                node_map[pseudonym_id] = node_id
                nodes.append({
                    "id": node_id,
                    "tenant_id": tenant_id,
                    "campaign_id": campaign_id,
                    "node_type": NodeType.PARTICIPANT,
                    "label": pseudonym_id,
                    "pseudonym_id": pseudonym_id,
                    "source_id": pseudonym_id,
                    "metadata": {"session_count": 1}
                })
            else:
                # Increment session count
                for n in nodes:
                    if n["id"] == node_map[pseudonym_id]:
                        n["metadata"]["session_count"] = n["metadata"].get("session_count", 0) + 1
        
        # Build theme nodes from categories and link to insights
        category_map = {c["id"]: c for c in categories}
        theme_participants = defaultdict(set)  # category_id -> set of pseudonym_ids
        theme_cooccurrence = defaultdict(lambda: defaultdict(int))  # theme1 -> theme2 -> count
        
        for insight in insights:
            category_id = insight.get("category_id")
            session_id = insight.get("source_session_id")
            
            if category_id and category_id not in node_map:
                cat = category_map.get(category_id, {})
                node_id = str(uuid.uuid4())
                node_map[category_id] = node_id
                nodes.append({
                    "id": node_id,
                    "tenant_id": tenant_id,
                    "campaign_id": campaign_id,
                    "node_type": cat.get("type", NodeType.THEME),
                    "label": cat.get("name", "Tema desconocido"),
                    "source_id": category_id,
                    "metadata": {
                        "color": cat.get("color"),
                        "description": cat.get("description"),
                        "insight_count": 1
                    }
                })
            elif category_id:
                # Increment insight count
                for n in nodes:
                    if n["id"] == node_map[category_id]:
                        n["metadata"]["insight_count"] = n["metadata"].get("insight_count", 0) + 1
            
            # Link participant to theme
            if session_id:
                transcript = next(
                    (t for t in transcripts if t.get("session_id") == session_id),
                    None
                )
                if transcript and transcript.get("pseudonym_id"):
                    pseudonym_id = transcript["pseudonym_id"]
                    if category_id:
                        participant_themes[pseudonym_id].add(category_id)
                        theme_participants[category_id].add(pseudonym_id)
        
        # Build theme co-occurrence from insights in same session
        session_themes = defaultdict(set)
        for insight in insights:
            session_id = insight.get("source_session_id")
            category_id = insight.get("category_id")
            if session_id and category_id:
                session_themes[session_id].add(category_id)
        
        for session_id, themes in session_themes.items():
            themes_list = list(themes)
            for i, t1 in enumerate(themes_list):
                for t2 in themes_list[i+1:]:
                    theme_cooccurrence[t1][t2] += 1
                    theme_cooccurrence[t2][t1] += 1
        
        # Create edges
        edge_counts = defaultdict(int)
        
        # 1. Participant -> Theme edges (HABLA_DE)
        if include_participant_theme:
            for pseudonym_id, themes in participant_themes.items():
                if pseudonym_id not in node_map:
                    continue
                participant_node_id = node_map[pseudonym_id]
                for theme_id in themes:
                    if theme_id not in node_map:
                        continue
                    theme_node_id = node_map[theme_id]
                    edge_key = f"{participant_node_id}_{theme_node_id}_habla_de"
                    if edge_key not in edge_counts:
                        edges.append({
                            "id": str(uuid.uuid4()),
                            "tenant_id": tenant_id,
                            "campaign_id": campaign_id,
                            "source_node_id": participant_node_id,
                            "target_node_id": theme_node_id,
                            "edge_type": EdgeType.HABLA_DE,
                            "weight": 1.0,
                            "evidence_links": []
                        })
                    edge_counts[edge_key] += 1
        
        # 2. Theme <-> Theme edges (CO_OCURRE)
        if include_theme_cooccurrence:
            for t1, cooccs in theme_cooccurrence.items():
                if t1 not in node_map:
                    continue
                for t2, count in cooccs.items():
                    if t2 not in node_map or count < min_edge_weight:
                        continue
                    if t1 < t2:  # Avoid duplicates
                        edges.append({
                            "id": str(uuid.uuid4()),
                            "tenant_id": tenant_id,
                            "campaign_id": campaign_id,
                            "source_node_id": node_map[t1],
                            "target_node_id": node_map[t2],
                            "edge_type": EdgeType.CO_OCURRE,
                            "weight": float(count),
                            "evidence_links": []
                        })
        
        # 3. Participant <-> Participant edges (COMPARTE_TEMA)
        if include_participant_similarity:
            pseudonyms = list(participant_themes.keys())
            for i, p1 in enumerate(pseudonyms):
                if p1 not in node_map:
                    continue
                for p2 in pseudonyms[i+1:]:
                    if p2 not in node_map:
                        continue
                    # Calculate shared themes
                    shared = participant_themes[p1] & participant_themes[p2]
                    if len(shared) >= min_edge_weight:
                        edges.append({
                            "id": str(uuid.uuid4()),
                            "tenant_id": tenant_id,
                            "campaign_id": campaign_id,
                            "source_node_id": node_map[p1],
                            "target_node_id": node_map[p2],
                            "edge_type": EdgeType.COMPARTE_TEMA,
                            "weight": float(len(shared)),
                            "evidence_links": list(shared)
                        })
        
        return nodes, edges
    
    @staticmethod
    def calculate_metrics(nodes: List[Dict], edges: List[Dict]) -> Dict[str, Any]:
        """Calculate network metrics using NetworkX."""
        
        if not nodes:
            return NetworkMetrics().model_dump()
        
        # Build NetworkX graph
        G = nx.Graph()
        
        for node in nodes:
            G.add_node(node["id"], **node)
        
        for edge in edges:
            G.add_edge(
                edge["source_node_id"],
                edge["target_node_id"],
                weight=edge.get("weight", 1.0),
                edge_type=edge.get("edge_type")
            )
        
        # Calculate metrics
        metrics = {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "density": nx.density(G) if G.number_of_nodes() > 1 else 0.0,
            "avg_clustering": 0.0,
            "num_communities": 0,
            "top_brokers": [],
            "communities": [],
            "nodes_by_type": defaultdict(int),
            "edges_by_type": defaultdict(int)
        }
        
        # Count by type
        for node in nodes:
            metrics["nodes_by_type"][node.get("node_type", "unknown")] += 1
        for edge in edges:
            metrics["edges_by_type"][edge.get("edge_type", "unknown")] += 1
        
        metrics["nodes_by_type"] = dict(metrics["nodes_by_type"])
        metrics["edges_by_type"] = dict(metrics["edges_by_type"])
        
        if G.number_of_nodes() < 2:
            return metrics
        
        # Betweenness Centrality (for brokers)
        try:
            betweenness = nx.betweenness_centrality(G, weight="weight")
            top_brokers = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:10]
            metrics["top_brokers"] = [
                {
                    "node_id": node_id,
                    "label": G.nodes[node_id].get("label", ""),
                    "node_type": G.nodes[node_id].get("node_type", ""),
                    "betweenness": round(score, 4)
                }
                for node_id, score in top_brokers if score > 0
            ]
            
            # Update node betweenness
            for node in nodes:
                node["betweenness"] = round(betweenness.get(node["id"], 0.0), 4)
        except Exception as e:
            logger.warning(f"Error calculating betweenness: {e}")
        
        # Degree Centrality
        try:
            in_degree = dict(G.degree())
            for node in nodes:
                node["degree_in"] = in_degree.get(node["id"], 0)
                node["degree_out"] = in_degree.get(node["id"], 0)  # Undirected
        except Exception as e:
            logger.warning(f"Error calculating degree: {e}")
        
        # Clustering Coefficient
        try:
            clustering = nx.clustering(G)
            metrics["avg_clustering"] = round(nx.average_clustering(G), 4)
            for node in nodes:
                node["clustering_coef"] = round(clustering.get(node["id"], 0.0), 4)
        except Exception as e:
            logger.warning(f"Error calculating clustering: {e}")
        
        # Community Detection (Louvain)
        try:
            if G.number_of_edges() > 0:
                partition = community_louvain.best_partition(G, weight="weight")
                communities = defaultdict(list)
                for node_id, comm_id in partition.items():
                    communities[comm_id].append({
                        "node_id": node_id,
                        "label": G.nodes[node_id].get("label", ""),
                        "node_type": G.nodes[node_id].get("node_type", "")
                    })
                    # Update node community
                    for node in nodes:
                        if node["id"] == node_id:
                            node["community_id"] = comm_id
                
                metrics["num_communities"] = len(communities)
                metrics["communities"] = [
                    {"id": comm_id, "size": len(members), "members": members[:5]}
                    for comm_id, members in sorted(
                        communities.items(),
                        key=lambda x: -len(x[1])
                    )
                ]
        except Exception as e:
            logger.warning(f"Error detecting communities: {e}")
        
        return metrics
    
    @staticmethod
    async def save_snapshot(
        campaign_id: str,
        tenant_id: str,
        nodes: List[Dict],
        edges: List[Dict],
        metrics: Dict[str, Any],
        name: str,
        created_by: str,
        description: str = None
    ) -> str:
        """Save a network snapshot."""
        db = get_database()
        
        snapshot = NetworkSnapshot(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            name=name,
            description=description,
            node_count=len(nodes),
            edge_count=len(edges),
            community_count=metrics.get("num_communities", 0),
            metrics=metrics,
            created_by=created_by
        )
        
        await db.network_snapshots.insert_one(
            serialize_document(snapshot.model_dump())
        )
        
        # Save nodes and edges with snapshot reference
        for node in nodes:
            node["snapshot_id"] = snapshot.id
        for edge in edges:
            edge["snapshot_id"] = snapshot.id
        
        if nodes:
            await db.network_nodes.insert_many(
                [serialize_document(n) for n in nodes]
            )
        if edges:
            await db.network_edges.insert_many(
                [serialize_document(e) for e in edges]
            )
        
        return snapshot.id


# Global service instance
network_analysis_service = NetworkAnalysisService()
