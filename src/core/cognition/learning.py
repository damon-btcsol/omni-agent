from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
from enum import Enum
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)


class ExperienceType(Enum):
    MARKET_DECISION = "market_decision"
    TRADING_ACTION = "trading_action"
    SOCIAL_INTERACTION = "social_interaction"
    ERROR_HANDLING = "error_handling"
    USER_FEEDBACK = "user_feedback"


@dataclass
class Experience:
    """Individual learning experience"""

    type: ExperienceType
    action: str
    context: Dict[str, Any]
    outcome: Dict[str, Any]
    timestamp: datetime
    success_score: float  # 0.0 to 1.0
    importance: float  # 0.0 to 1.0
    metadata: Optional[Dict] = None


class LearningManager:
    """Manages agent learning and improvement"""

    def __init__(self, memory_size: int = 1000, learning_rate: float = 0.1):
        self.memory_size = memory_size
        self.learning_rate = learning_rate
        self.experiences: deque = deque(maxlen=memory_size)
        self.patterns: Dict[str, Dict] = {}
        self.performance_history: List[Dict] = []

    async def record_experience(
        self,
        exp_type: ExperienceType,
        action: str,
        context: Dict[str, Any],
        outcome: Dict[str, Any],
        success_score: float,
        importance: float = 0.5,
        metadata: Optional[Dict] = None,
    ) -> Experience:
        """Record new learning experience"""
        try:
            experience = Experience(
                type=exp_type,
                action=action,
                context=context,
                outcome=outcome,
                timestamp=datetime.now(),
                success_score=success_score,
                importance=importance,
                metadata=metadata or {},
            )

            self.experiences.append(experience)
            await self._analyze_pattern(experience)
            await self._update_performance_metrics(experience)

            return experience

        except Exception as e:
            logger.error(f"Error recording experience: {e}")
            raise

    async def get_similar_experiences(
        self,
        context: Dict[str, Any],
        exp_type: Optional[ExperienceType] = None,
        limit: int = 5,
    ) -> List[Experience]:
        """Find similar past experiences"""
        try:
            relevant_experiences = []

            for exp in self.experiences:
                if exp_type and exp.type != exp_type:
                    continue

                similarity = await self._calculate_similarity(context, exp.context)

                relevant_experiences.append((similarity, exp))

            # Sort by similarity
            relevant_experiences.sort(key=lambda x: x[0], reverse=True)

            return [exp for _, exp in relevant_experiences[:limit]]

        except Exception as e:
            logger.error(f"Error finding similar experiences: {e}")
            raise

    async def get_recommendation(
        self, context: Dict[str, Any], exp_type: ExperienceType
    ) -> Dict[str, Any]:
        """Get action recommendation based on past experiences"""
        try:
            similar_experiences = await self.get_similar_experiences(context, exp_type)

            if not similar_experiences:
                return {
                    "confidence": 0.0,
                    "recommendation": None,
                    "reason": "No similar experiences found",
                }

            # Analyze successful actions
            action_scores = {}
            for exp in similar_experiences:
                action = exp.action
                if action not in action_scores:
                    action_scores[action] = {
                        "count": 0,
                        "total_score": 0,
                        "importance": 0,
                    }

                action_scores[action]["count"] += 1
                action_scores[action]["total_score"] += exp.success_score
                action_scores[action]["importance"] += exp.importance

            # Find best action
            best_action = max(
                action_scores.items(),
                key=lambda x: (x[1]["total_score"] / x[1]["count"], x[1]["importance"]),
            )[0]

            avg_score = (
                action_scores[best_action]["total_score"]
                / action_scores[best_action]["count"]
            )

            return {
                "confidence": avg_score,
                "recommendation": best_action,
                "supporting_experiences": len(similar_experiences),
                "average_success": avg_score,
            }

        except Exception as e:
            logger.error(f"Error getting recommendation: {e}")
            raise

    async def _analyze_pattern(self, experience: Experience):
        """Analyze and store patterns from experience"""
        pattern_key = f"{experience.type.value}_{experience.action}"

        if pattern_key not in self.patterns:
            self.patterns[pattern_key] = {
                "success_count": 0,
                "total_count": 0,
                "avg_success": 0.0,
                "contexts": [],
            }

        pattern = self.patterns[pattern_key]
        pattern["total_count"] += 1

        if experience.success_score >= 0.7:
            pattern["success_count"] += 1
            pattern["contexts"].append(experience.context)

        pattern["avg_success"] = pattern["success_count"] / pattern["total_count"]

        # Keep only recent contexts
        pattern["contexts"] = pattern["contexts"][-50:]

    async def _update_performance_metrics(self, experience: Experience):
        """Update performance tracking metrics"""
        self.performance_history.append(
            {
                "timestamp": experience.timestamp.isoformat(),
                "type": experience.type.value,
                "action": experience.action,
                "success_score": experience.success_score,
                "importance": experience.importance,
            }
        )

    async def _calculate_similarity(
        self, context1: Dict[str, Any], context2: Dict[str, Any]
    ) -> float:
        """Calculate context similarity"""
        # Simple matching coefficient for now
        total_keys = set(context1.keys()) | set(context2.keys())
        matching_values = sum(
            1
            for k in total_keys
            if k in context1 and k in context2 and context1[k] == context2[k]
        )

        return matching_values / len(total_keys) if total_keys else 0.0

    async def get_performance_summary(
        self, timeframe: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Get learning performance summary"""
        if timeframe:
            cutoff = datetime.now() - timeframe
            history = [
                p
                for p in self.performance_history
                if datetime.fromisoformat(p["timestamp"]) > cutoff
            ]
        else:
            history = self.performance_history

        if not history:
            return {
                "average_success": 0.0,
                "experience_count": 0,
                "patterns_identified": 0,
            }

        return {
            "average_success": np.mean([p["success_score"] for p in history]),
            "experience_count": len(history),
            "patterns_identified": len(self.patterns),
            "type_breakdown": {
                exp_type.value: len([p for p in history if p["type"] == exp_type.value])
                for exp_type in ExperienceType
            },
        }
