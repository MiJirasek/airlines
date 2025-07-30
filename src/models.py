from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class AirlineAction(BaseModel):
    action_type: str
    description: str
    cost: float
    parameters: Dict[str, Any]


class SemesterPlan(BaseModel):
    team_id: str
    semester: str
    actions: List[AirlineAction]
    total_budget: float
    submission_timestamp: datetime


class AirlineState(BaseModel):
    team_id: str
    name: str
    cash: float
    aircraft_count: int
    routes: List[str]
    market_share: float
    reputation: float
    last_updated: datetime


class MarketState(BaseModel):
    total_passengers: int
    competition_level: float
    economic_conditions: str
    events: List[str]
    last_updated: datetime


class AgentResponse(BaseModel):
    approved_actions: List[AirlineAction]
    rejected_actions: List[AirlineAction]
    cash_used: float
    reasoning: str


class EvaluationFeedback(BaseModel):
    team_id: str
    score: float
    feedback_text: str
    strengths: List[str]
    improvement_areas: List[str]
    created_at: datetime