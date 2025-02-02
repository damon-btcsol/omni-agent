from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)

class GoalPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class GoalStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"

class GoalType(Enum):
    MARKET_ANALYSIS = "market_analysis"
    PORTFOLIO_MANAGEMENT = "portfolio_management"
    RISK_MANAGEMENT = "risk_management"
    SOCIAL_ENGAGEMENT = "social_engagement"
    LEARNING = "learning"
    SYSTEM_OPTIMIZATION = "system_optimization"

@dataclass
class Goal:
    """Individual goal definition"""

    id: str
    priority: GoalPriority
    type: str
    description: str
    deadline: Optional[datetime] = None
    status: GoalStatus = GoalStatus.PENDING

class GoalGenerator:
    """Handles goal generation with proper JSON handling"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_goals(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate goals from context data"""
        try:
            # Convert context to JSON string first
            context_json = json.dumps(context)
            
            # Generate goals based on context
            goals = [
                {
                    'id': 'market_analysis',
                    'priority': self._calculate_priority(context),
                    'type': 'analysis',
                    'description': 'Analyze current market conditions',
                    'deadline': None
                },
                {
                    'id': 'portfolio_management',
                    'priority': self._calculate_priority(context),
                    'type': 'management',
                    'description': 'Optimize portfolio based on market analysis',
                    'deadline': None
                }
            ]
            
            return goals
            
        except Exception as e:
            self.logger.error(f"Error generating goals: {str(e)}")
            return []
    
    def _calculate_priority(self, context: Dict[str, Any]) -> str:
        """Calculate goal priority based on context"""
        try:
            # Priority calculation logic here
            return GoalPriority.MEDIUM.value
        except Exception as e:
            self.logger.error(f"Error calculating priority: {str(e)}")
            return GoalPriority.MEDIUM.value

class GoalManager:
    def __init__(self, max_concurrent_goals: int = 5):
        self.max_concurrent_goals = max_concurrent_goals
        self.active_goals: List[Goal] = []
        self.completed_goals: List[Goal] = []
        self.failed_goals: List[Goal] = []
        self.goals: Dict[str, Goal] = {}
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the goal manager"""
        try:
            # Load any persistent goals from storage
            # Initialize goal tracking systems
            self._initialized = True
            logger.info("Goal Manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Goal Manager: {e}")
            raise

    async def add_goal(self, 
                      goal_id: str,
                      goal_type: str,
                      priority: float = 0.5) -> Goal:
        """Add a new goal to the system"""
        if not self._initialized:
            raise RuntimeError("Goal Manager not initialized")
            
        try:
            if goal_id in self.goals:
                logger.warning(f"Goal with ID {goal_id} already exists.")
                return
            goal = Goal(
                id=goal_id,
                type=goal_type,
                progress=0.0,
                priority=priority
            )
            
            if len(self.active_goals) >= self.max_concurrent_goals:
                await self._reprioritize_goals()
                
            self.active_goals.append(goal)
            self.goals[goal_id] = goal
            logger.info(f"Added new goal: {goal.id} - {goal_type}")
            return goal
            
        except Exception as e:
            logger.error(f"Failed to add goal: {e}")
            raise

    async def create_goal(
        self,
        goal_type: GoalType,
        description: str,
        priority: float,
        deadline: Optional[datetime] = None,
        dependencies: Optional[List[str]] = None,
        success_criteria: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Goal:
        """Create new goal"""
        try:
            goal_id = f"goal_{len(self.goals) + 1}_{datetime.now().timestamp()}"

            goal = Goal(
                id=goal_id,
                type=goal_type,
                description=description,
                priority=priority,
                status=GoalStatus.PENDING,
                created_at=datetime.now(),
                deadline=deadline,
                dependencies=dependencies or [],
                success_criteria=success_criteria or {},
                metadata=metadata or {},
            )

            self.goals[goal_id] = goal
            await self._check_goal_dependencies(goal)

            return goal

        except Exception as e:
            logger.error(f"Error creating goal: {e}")
            raise

    async def update_goal_progress(
        self, goal_id: str, progress: float, metrics: Optional[Dict[str, Any]] = None
    ) -> Goal:
        """Update goal progress"""
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")

        goal = self.goals[goal_id]
        goal.progress = min(max(progress, 0.0), 1.0)

        if metrics:
            if not goal.metadata.get("metrics"):
                goal.metadata["metrics"] = []
            goal.metadata["metrics"].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "progress": progress,
                    **metrics,
                }
            )

        # Check if goal is completed
        if progress >= 1.0:
            await self.complete_goal(goal_id)

        return goal

    async def complete_goal(self, goal_id: str) -> Goal:
        """Mark goal as completed"""
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")

        goal = self.goals[goal_id]
        goal.status = GoalStatus.COMPLETED
        goal.progress = 1.0

        # Move to completed goals
        self.completed_goals.append(goal)
        del self.goals[goal_id]

        # Update dependent goals
        await self._update_dependent_goals(goal_id)

        return goal

    async def fail_goal(self, goal_id: str, reason: str) -> Goal:
        """Mark goal as failed"""
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")

        goal = self.goals[goal_id]
        goal.status = GoalStatus.FAILED
        goal.metadata["failure_reason"] = reason

        # Move to failed goals
        self.failed_goals.append(goal)
        del self.goals[goal_id]

        return goal

    async def get_active_goals(
        self, goal_type: Optional[GoalType] = None
    ) -> List[Goal]:
        """Get active goals"""
        goals = [
            goal for goal in self.goals.values() if goal.status == GoalStatus.ACTIVE
        ]

        if goal_type:
            goals = [goal for goal in goals if goal.type == goal_type]

        return sorted(goals, key=lambda x: x.priority, reverse=True)

    async def get_goal_status(self, goal_id: str) -> Dict[str, Any]:
        """Get detailed goal status"""
        if goal_id not in self.goals:
            # Check completed and failed goals
            for goal in self.completed_goals + self.failed_goals:
                if goal.id == goal_id:
                    return {
                        "id": goal.id,
                        "status": goal.status.value,
                        "progress": goal.progress,
                        "metrics": goal.metadata.get("metrics", []),
                        "completed_at": goal.metadata.get("completed_at"),
                    }
            raise ValueError(f"Goal {goal_id} not found")

        goal = self.goals[goal_id]
        return {
            "id": goal.id,
            "type": goal.type.value,
            "status": goal.status.value,
            "progress": goal.progress,
            "priority": goal.priority,
            "created_at": goal.created_at.isoformat(),
            "deadline": goal.deadline.isoformat() if goal.deadline else None,
            "dependencies": goal.dependencies,
            "metrics": goal.metadata.get("metrics", []),
        }

    async def _check_goal_dependencies(self, goal: Goal):
        """Check and update goal dependencies"""
        if not goal.dependencies:
            goal.status = GoalStatus.ACTIVE
            return

        # Check if all dependencies are completed
        can_activate = True
        for dep_id in goal.dependencies:
            if dep_id in self.goals:
                can_activate = False
                break

        if can_activate:
            goal.status = GoalStatus.ACTIVE
        else:
            goal.status = GoalStatus.PENDING

    async def _update_dependent_goals(self, completed_goal_id: str):
        """Update goals that depend on completed goal"""
        for goal in self.goals.values():
            if completed_goal_id in (goal.dependencies or []):
                goal.dependencies.remove(completed_goal_id)
                await self._check_goal_dependencies(goal)

    async def get_goal_progress_report(self) -> Dict[str, Any]:
        """Generate goal progress report"""
        return {
            "active_goals": len(self.goals),
            "completed_goals": len(self.completed_goals),
            "failed_goals": len(self.failed_goals),
            "progress_by_type": {
                goal_type.value: {
                    "count": len(
                        [g for g in self.goals.values() if g.type == goal_type]
                    ),
                    "avg_progress": sum(
                        g.progress for g in self.goals.values() if g.type == goal_type
                    )
                    / len(
                        [g for g in self.goals.values() if g.type == goal_type] or [1]
                    ),
                }
                for goal_type in GoalType
            },
            "high_priority_goals": [
                {"id": g.id, "type": g.type.value, "progress": g.progress}
                for g in sorted(
                    self.goals.values(), key=lambda x: x.priority, reverse=True
                )[:5]
            ],
        }

    def remove_goal(self, goal_id: str):
        """Remove a goal from the manager"""
        if goal_id in self.goals:
            del self.goals[goal_id]
            logger.info(f"Removed goal with ID {goal_id}.")
        else:
            logger.warning(f"Goal with ID {goal_id} does not exist.")
