"""Network analysis routes for RunaMap."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.core.dependencies import get_current_user
from app.services.network_service import network_analysis_service
from app.services.initiative_service import initiative_service
from app.models.network import (
    GenerateNetworkRequest,
    GraphResponse,
    NetworkMetrics,
)

network_router = APIRouter(prefix="/network", tags=["Network Analysis"])


@network_router.post("/generate")
async def generate_network(
    request_data: GenerateNetworkRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate network graph from campaign data."""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos para análisis de red")
    
    db = get_database()
    campaign = await db.campaigns.find_one({"id": request_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    tenant_id = campaign.get("tenant_id", "default")
    
    # Build graph
    nodes, edges = await network_analysis_service.build_graph_from_campaign(
        campaign_id=request_data.campaign_id,
        tenant_id=tenant_id,
        include_participant_theme=request_data.include_participant_theme,
        include_theme_cooccurrence=request_data.include_theme_cooccurrence,
        include_participant_similarity=request_data.include_participant_similarity,
        min_edge_weight=request_data.min_edge_weight
    )
    
    # Calculate metrics
    metrics = network_analysis_service.calculate_metrics(nodes, edges)
    
    # Transform edges for React Flow compatibility
    transformed_edges = []
    for edge in edges:
        transformed_edge = {
            **edge,
            "source": edge.get("source_node_id"),
            "target": edge.get("target_node_id")
        }
        transformed_edges.append(transformed_edge)
    
    # Save snapshot if name provided
    snapshot_id = None
    if request_data.snapshot_name:
        snapshot_id = await network_analysis_service.save_snapshot(
            campaign_id=request_data.campaign_id,
            tenant_id=tenant_id,
            nodes=nodes,
            edges=edges,
            metrics=metrics,
            name=request_data.snapshot_name,
            created_by=current_user["id"]
        )
    
    return GraphResponse(
        nodes=nodes,
        edges=transformed_edges,
        metrics=NetworkMetrics(**metrics),
        snapshot_id=snapshot_id
    )


@network_router.get("/campaign/{campaign_id}")
async def get_campaign_network(
    campaign_id: str,
    include_participant_theme: bool = True,
    include_theme_cooccurrence: bool = True,
    include_participant_similarity: bool = True,
    min_edge_weight: float = 1.0,
    current_user: dict = Depends(get_current_user)
):
    """Get network graph for a campaign (without saving snapshot)."""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos para análisis de red")
    
    db = get_database()
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    tenant_id = campaign.get("tenant_id", "default")
    
    nodes, edges = await network_analysis_service.build_graph_from_campaign(
        campaign_id=campaign_id,
        tenant_id=tenant_id,
        include_participant_theme=include_participant_theme,
        include_theme_cooccurrence=include_theme_cooccurrence,
        include_participant_similarity=include_participant_similarity,
        min_edge_weight=min_edge_weight
    )
    
    metrics = network_analysis_service.calculate_metrics(nodes, edges)
    
    # Transform edges for React Flow compatibility
    transformed_edges = []
    for edge in edges:
        transformed_edge = {
            **edge,
            "source": edge.get("source_node_id"),
            "target": edge.get("target_node_id")
        }
        transformed_edges.append(transformed_edge)
    
    return GraphResponse(
        nodes=nodes,
        edges=transformed_edges,
        metrics=NetworkMetrics(**metrics)
    )


@network_router.get("/snapshots/{campaign_id}")
async def list_network_snapshots(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all network snapshots for a campaign."""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    snapshots = await db.network_snapshots.find(
        {"campaign_id": campaign_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return snapshots


@network_router.get("/snapshot/{snapshot_id}")
async def get_network_snapshot(
    snapshot_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific network snapshot with its nodes and edges."""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    snapshot = await db.network_snapshots.find_one(
        {"id": snapshot_id},
        {"_id": 0}
    )
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot no encontrado")
    
    nodes = await db.network_nodes.find(
        {"snapshot_id": snapshot_id},
        {"_id": 0}
    ).to_list(1000)
    
    edges = await db.network_edges.find(
        {"snapshot_id": snapshot_id},
        {"_id": 0}
    ).to_list(2000)
    
    # Transform edges for React Flow
    transformed_edges = []
    for edge in edges:
        transformed_edge = {
            **edge,
            "source": edge.get("source_node_id"),
            "target": edge.get("target_node_id")
        }
        transformed_edges.append(transformed_edge)
    
    return {
        "snapshot": snapshot,
        "nodes": nodes,
        "edges": transformed_edges
    }


@network_router.delete("/snapshot/{snapshot_id}")
async def delete_network_snapshot(
    snapshot_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a network snapshot."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    
    # Delete snapshot and related data
    await db.network_snapshots.delete_one({"id": snapshot_id})
    await db.network_nodes.delete_many({"snapshot_id": snapshot_id})
    await db.network_edges.delete_many({"snapshot_id": snapshot_id})
    
    return {"message": "Snapshot eliminado"}


@network_router.get("/initiative-leaders/{campaign_id}")
async def get_initiative_leaders(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get users who lead initiatives for network visualization."""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    leaders = await initiative_service.get_initiative_leaders(campaign_id)
    return leaders
