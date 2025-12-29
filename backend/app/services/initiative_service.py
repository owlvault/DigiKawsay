"""Initiative and Ritual Services for RunaFlow."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

from app.database import get_database


class InitiativeService:
    """Service for managing initiatives (RunaFlow)."""
    
    @staticmethod
    def calculate_ice_score(impact: int, confidence: int, ease: int) -> float:
        """Calculate ICE score: Impact × Confidence × Ease / 10."""
        return round((impact * confidence * ease) / 10, 2)
    
    @staticmethod
    def calculate_rice_score(
        reach: int,
        impact: int,
        confidence: int,
        effort: int
    ) -> float:
        """Calculate RICE score: (Reach × Impact × Confidence) / Effort."""
        if effort <= 0:
            effort = 1
        # Normalize: reach in hundreds, impact/confidence 1-10, effort 1-10
        return round((reach * impact * (confidence / 10)) / effort, 2)
    
    @staticmethod
    def calculate_score(initiative: dict) -> float:
        """Calculate score based on scoring method."""
        method = initiative.get("scoring_method", "ice")
        if method == "rice":
            return InitiativeService.calculate_rice_score(
                initiative.get("reach_score", 100),
                initiative.get("impact_score", 5),
                initiative.get("confidence_score", 5),
                initiative.get("effort_score", 5)
            )
        else:  # ICE
            return InitiativeService.calculate_ice_score(
                initiative.get("impact_score", 5),
                initiative.get("confidence_score", 5),
                initiative.get("ease_score", 5)
            )
    
    @staticmethod
    async def get_initiative_leaders(campaign_id: str) -> List[Dict]:
        """Get users who lead initiatives for network visualization."""
        db = get_database()
        
        initiatives = await db.initiatives.find(
            {"campaign_id": campaign_id, "assigned_to": {"$ne": None}},
            {"_id": 0}
        ).to_list(500)
        
        leader_stats = defaultdict(lambda: {
            "count": 0,
            "completed": 0,
            "in_progress": 0
        })
        
        for init in initiatives:
            user_id = init.get("assigned_to")
            if user_id:
                leader_stats[user_id]["count"] += 1
                if init.get("status") == "completada":
                    leader_stats[user_id]["completed"] += 1
                elif init.get("status") == "en_progreso":
                    leader_stats[user_id]["in_progress"] += 1
        
        # Get user details
        leaders = []
        for user_id, stats in leader_stats.items():
            user = await db.users.find_one(
                {"id": user_id},
                {"_id": 0, "hashed_password": 0}
            )
            if user:
                leaders.append({
                    "user_id": user_id,
                    "name": user.get("full_name", "Unknown"),
                    "pseudonym_id": user.get("pseudonym_id"),
                    "initiatives_count": stats["count"],
                    "completed_count": stats["completed"],
                    "in_progress_count": stats["in_progress"],
                    "is_initiative_leader": True
                })
        
        return sorted(leaders, key=lambda x: -x["initiatives_count"])


class RitualService:
    """Service for managing rituals (RunaFlow)."""
    
    @staticmethod
    def calculate_next_occurrence(ritual: dict) -> Optional[datetime]:
        """Calculate next occurrence based on ritual type."""
        now = datetime.now(timezone.utc)
        ritual_type = ritual.get("ritual_type")
        time_str = ritual.get("time_of_day", "09:00")
        
        try:
            hour, minute = map(int, time_str.split(":"))
        except:
            hour, minute = 9, 0
        
        if ritual_type == "daily":
            next_date = now.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            if next_date <= now:
                next_date += timedelta(days=1)
            return next_date
        
        elif ritual_type == "weekly":
            day_of_week = ritual.get("day_of_week", 0)
            days_ahead = day_of_week - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_date = now + timedelta(days=days_ahead)
            return next_date.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
        
        elif ritual_type == "monthly":
            day_of_month = ritual.get("day_of_month", 1)
            next_date = now.replace(
                day=min(day_of_month, 28),
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )
            if next_date <= now:
                if now.month == 12:
                    next_date = next_date.replace(year=now.year + 1, month=1)
                else:
                    next_date = next_date.replace(month=now.month + 1)
            return next_date
        
        elif ritual_type == "quarterly":
            current_quarter = (now.month - 1) // 3
            next_quarter_start_month = ((current_quarter + 1) % 4) * 3 + 1
            year = now.year if next_quarter_start_month > now.month else now.year + 1
            day_of_month = ritual.get("day_of_month", 1)
            return datetime(
                year,
                next_quarter_start_month,
                min(day_of_month, 28),
                hour,
                minute,
                tzinfo=timezone.utc
            )
        
        return None


# Global service instances
initiative_service = InitiativeService()
ritual_service = RitualService()
