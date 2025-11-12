"""Status API endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import psutil

from app.database import get_db
from app.models import Tunnel, Node, Usage
from datetime import datetime, timedelta


router = APIRouter()


@router.get("")
async def get_status(db: AsyncSession = Depends(get_db)):
    """Get system status"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    tunnel_result = await db.execute(select(func.count(Tunnel.id)))
    total_tunnels = tunnel_result.scalar() or 0
    
    active_tunnels_result = await db.execute(
        select(func.count(Tunnel.id)).where(Tunnel.status == "active")
    )
    active_tunnels = active_tunnels_result.scalar() or 0
    
    node_result = await db.execute(select(func.count(Node.id)))
    total_nodes = node_result.scalar() or 0
    
    active_nodes_result = await db.execute(
        select(func.count(Node.id)).where(Node.status == "active")
    )
    active_nodes = active_nodes_result.scalar() or 0
    
    # Get total traffic (sum of all tunnel.used_mb)
    total_traffic_result = await db.execute(
        select(func.sum(Tunnel.used_mb))
    )
    total_traffic_mb = total_traffic_result.scalar() or 0.0
    
    # Get traffic in last hour for current rate
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_traffic_result = await db.execute(
        select(func.sum(Usage.bytes_used))
        .where(Usage.timestamp >= one_hour_ago)
    )
    recent_traffic_bytes = recent_traffic_result.scalar() or 0
    current_rate_mb_per_hour = recent_traffic_bytes / (1024 * 1024)
    
    return {
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_total_gb": memory.total / (1024**3),
            "memory_used_gb": memory.used / (1024**3),
        },
        "tunnels": {
            "total": total_tunnels,
            "active": active_tunnels,
        },
        "nodes": {
            "total": total_nodes,
            "active": active_nodes,
        },
        "traffic": {
            "total_mb": total_traffic_mb,
            "total_bytes": int(total_traffic_mb * 1024 * 1024),
            "current_rate_mb_per_hour": current_rate_mb_per_hour,
        }
    }

