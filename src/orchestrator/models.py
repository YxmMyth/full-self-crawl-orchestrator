"""Pydantic [数据模型定义]"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RefinedRequirement(BaseModel):
    """[精确化需求模型]"""
    topic: str = Field(..., description="[调研主题]")
    target_fields: List[str] = Field(default_factory=list, description="[目标字段列表]")
    scope: str = Field(default="", description="[范围限制]")
    time_range: str = Field(default="", description="[时间范围]")
    quantity: int = Field(default=1000, description="[期望数据量]")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="[其他约束条件]")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "[科技媒体]",
                "target_fields": ["[标题]", "[作者]", "[发布时间]", "[正文]"],
                "scope": "[国内]",
                "time_range": "[近一年]",
                "quantity": 1000,
                "constraints": {}
            }
        }


class CandidateSite(BaseModel):
    """[候选站点模型]"""
    site_name: str = Field(..., description="[站点名称]")
    site_url: str = Field(..., description="[站点] URL")
    description: str = Field(default="", description="[站点描述]")
    priority: int = Field(default=5, ge=1, le=10, description="[优先级] (1-10)")

    class Config:
        json_schema_extra = {
            "example": {
                "site_name": "36[氪]",
                "site_url": "https://36kr.com",
                "description": "[创投科技媒体]",
                "priority": 1
            }
        }


class TaskParams(BaseModel):
    """[任务参数模型]"""
    task_id: str = Field(..., description="[任务]ID")
    site_url: str = Field(..., description="[站点]URL")
    site_name: str = Field(default="", description="[站点名称]")
    requirement: RefinedRequirement = Field(..., description="[需求规格]")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_001:https://36kr.com",
                "site_url": "https://36kr.com",
                "site_name": "36[氪]",
                "requirement": {
                    "topic": "[科技媒体]",
                    "target_fields": ["[标题]", "[作者]", "[发布时间]"],
                    "scope": "[国内]",
                    "time_range": "[近一年]",
                    "quantity": 1000,
                    "constraints": {}
                }
            }
        }


class ProgressUpdate(BaseModel):
    """[进度更新模型]"""
    task_id: str = Field(..., description="[任务]ID")
    agent_id: Optional[str] = Field(default=None, description="Agent ID")
    status: str = Field(default="running", description="[状态]")
    current_url: str = Field(default="", description="[当前处理的] URL")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="[进度] (0-1)")
    collected_count: int = Field(default=0, description="[已采集数量]")
    message: str = Field(default="", description="[状态消息]")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class TaskResult(BaseModel):
    """[任务结果模型]"""
    task_id: str = Field(..., description="[任务]ID")
    agent_id: Optional[str] = Field(default=None, description="Agent ID")
    site_url: str = Field(..., description="[站点]URL")
    site_name: str = Field(default="", description="[站点名称]")

    # [质量评估]
    quality_score: float = Field(default=0.0, ge=0.0, le=100.0, description="[质量评分] (0-100)")
    total_pages: int = Field(default=0, description="[探测页面数]")
    total_records: int = Field(default=0, description="[采集记录数]")

    # [样例数据]
    samples: List[Dict[str, Any]] = Field(default_factory=list, description="[样例数据]")

    # [探测元信息]
    duration_sec: int = Field(default=0, description="[执行时长]([秒])")
    strategy_used: str = Field(default="", description="[使用的策略]")
    difficulty: str = Field(default="", description="[难度级别]")
    anti_bot: List[str] = Field(default_factory=list, description="[反爬措施]")

    # [状态]
    status: str = Field(default="pending", description="[状态]: pending/running/success/failed")
    error_message: str = Field(default="", description="[错误信息]")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_001:https://36kr.com",
                "site_url": "https://36kr.com",
                "site_name": "36[氪]",
                "quality_score": 92.5,
                "total_pages": 5,
                "total_records": 50,
                "samples": [],
                "duration_sec": 120,
                "strategy_used": "api_first",
                "difficulty": "easy",
                "anti_bot": [],
                "status": "success",
                "error_message": ""
            }
        }


class SiteRanking(BaseModel):
    """[站点排行榜项]"""
    rank: int = Field(..., description="[排名]")
    site_name: str = Field(..., description="[站点名称]")
    site_url: str = Field(..., description="[站点]URL")
    quality_score: float = Field(..., description="[质量评分]")
    total_records: int = Field(default=0, description="[数据量]")
    difficulty: str = Field(default="", description="[难度]")
    samples: List[Dict[str, Any]] = Field(default_factory=list, description="[样例数据]")


class FailedSite(BaseModel):
    """[失败站点信息]"""
    site_url: str = Field(..., description="[站点]URL")
    site_name: str = Field(default="", description="[站点名称]")
    reason: str = Field(..., description="[失败原因]")
    error_message: str = Field(default="", description="[详细错误]")


class ResearchResult(BaseModel):
    """[调研结果模型]"""
    query: str = Field(..., description="[用户原始需求]")
    task_id: str = Field(..., description="[任务]ID")
    total_sites: int = Field(default=0, description="[总探测站点数]")
    successful_sites: int = Field(default=0, description="[成功站点数]")
    failed_sites_count: int = Field(default=0, description="[失败站点数]")

    # [排行榜] ([按质量分数排序])
    rankings: List[SiteRanking] = Field(default_factory=list, description="[站点排行榜]")

    # [失败站点列表]
    failed_sites: List[FailedSite] = Field(default_factory=list, description="[失败站点]")

    # [元信息]
    total_duration_sec: int = Field(default=0, description="[总耗时]([秒])")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = Field(default=None, description="[完成时间]")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "[我想找科技媒体的数据源]",
                "task_id": "task_001",
                "total_sites": 10,
                "successful_sites": 8,
                "failed_sites_count": 2,
                "rankings": [],
                "failed_sites": [],
                "total_duration_sec": 1800,
                "created_at": "2026-02-26T10:00:00",
                "completed_at": "2026-02-26T10:30:00"
            }
        }


class TaskInfo(BaseModel):
    """[任务信息模型]"""
    task_id: str = Field(..., description="[任务]ID")
    user_query: str = Field(..., description="[用户原始查询]")
    refined_requirement: Optional[RefinedRequirement] = Field(default=None, description="[精确化需求]")
    candidate_sites: List[CandidateSite] = Field(default_factory=list, description="[候选站点列表]")
    total_sites: int = Field(default=0, description="[总站点数]")
    successful_sites: int = Field(default=0, description="[成功站点数]")
    status: str = Field(default="pending", description="[状态]")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = Field(default=None, description="[完成时间]")
