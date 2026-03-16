from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime


class ImpactMetrics(BaseModel):
    """影响力指标模型"""
    technology_penetration: float = Field(ge=0.0, le=1.0, default=0.0)
    economic_disruption: float = Field(ge=0.0, le=1.0, default=0.0)
    employment_volatility: float = Field(ge=0.0, le=1.0, default=0.0)
    process_reconstruction: float = Field(ge=0.0, le=1.0, default=0.0)
    ethical_risk: float = Field(ge=0.0, le=1.0, default=0.0)
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return self.dict()
    
    def calculate_composite_score(self) -> float:
        """计算综合得分"""
        weights = {
            "technology_penetration": 0.25,
            "economic_disruption": 0.25,
            "employment_volatility": 0.15,
            "process_reconstruction": 0.20,
            "ethical_risk": 0.15
        }
        
        score = 0.0
        for field_name, weight in weights.items():
            score += getattr(self, field_name) * weight
        
        return score


class EventModel(BaseModel):
    """事件模型"""
    id: str
    name: str
    description: str
    category: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    source: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class SimulationRound(BaseModel):
    """推演轮次模型"""
    round_number: int
    agent_opinions: List[dict]  # AgentOpinion 使用字典形式以避免循环导入
    consensus_points: List[str] = Field(default_factory=list)
    conflict_points: List[str] = Field(default_factory=list)
    metrics_snapshot: Dict[str, float] = Field(default_factory=dict)


class SimulationResult(BaseModel):
    """推演结果模型"""
    event_id: str
    event_name: str
    event_description: str
    total_rounds: int
    rounds: List[SimulationRound] = Field(default_factory=list)
    final_metrics: Dict[str, float] = Field(default_factory=dict)
    composite_score: float = 0.0
    consensus_summary: str = ""
    conflict_summary: str = ""
    recommendations: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    visualization_files: List[str] = Field(default_factory=list)