"""
Pydantic schemas for job/monitoring data
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    SKIPPED = "SKIPPED"


class JobType(str, Enum):
    LATEST_SYNC = "LATEST_SYNC"
    PERIOD_SYNC = "PERIOD_SYNC"
    METRICS_REFRESH = "METRICS_REFRESH"


class NodeStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    STUCK = "stuck"


class JobItem(BaseModel):
    """Single job item."""
    id: int
    job_id: str
    job_type: str
    trigger_type: str
    status: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    worker_heartbeat_at: Optional[datetime] = None
    total_accounts: int = 0
    total_posts_found: int = 0
    total_posts_inserted: int = 0
    total_posts_updated: int = 0
    total_success: int = 0
    total_partial: int = 0
    total_failed: int = 0
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobsResponse(BaseModel):
    """Jobs list response."""
    jobs: List[JobItem]
    total: int
    running_count: int = 0
    queued_count: int = 0


class FailedItem(BaseModel):
    """Failed scraping item."""
    id: int
    job_id: str
    username: Optional[str] = None
    post_url: Optional[str] = None
    reason: Optional[str] = None
    error_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FailedItemsResponse(BaseModel):
    """Failed items list response."""
    items: List[FailedItem]
    total: int


class NodeFlowItem(BaseModel):
    """Node in the workflow visualization."""
    id: str
    name: str
    status: str  # idle, running, success, warning, failed, stuck
    description: Optional[str] = None
    last_updated: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None


class NodeFlowResponse(BaseModel):
    """Node flow visualization response."""
    nodes: List[NodeFlowItem]
    current_job: Optional[JobItem] = None
    worker_status: str  # "alive", "dead", "unknown"
    worker_last_heartbeat: Optional[datetime] = None


class AlertItem(BaseModel):
    """Alert notification item."""
    id: int
    alert_type: str  # "new_post", "job_failed", "job_stuck", "worker_dead", "failed_count"
    title: str
    message: str
    severity: str  # "info", "warning", "danger"
    is_read: bool = False
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class AlertsResponse(BaseModel):
    """Alerts list response."""
    alerts: List[AlertItem]
    total: int
    unread_count: int


class TriggerJobRequest(BaseModel):
    job_type: JobType = Field(..., description="Type of job to trigger")
    period_start: Optional[str] = Field(None, description="Start date (YYYY-MM-DD) for PERIOD_SYNC")
    period_end: Optional[str] = Field(None, description="End date (YYYY-MM-DD) for PERIOD_SYNC")
    account_limit: Optional[int] = Field(None, description="Limit accounts to process")
    account_ids: Optional[List[int]] = Field(None, description="Specific account IDs to process")
    usernames: Optional[List[str]] = Field(None, description="Specific usernames to process")
    dry_run: Optional[bool] = Field(False, description="Preview selection without creating job")
    allow_all_active: bool = Field(False, description="Allow default trigger to process all active accounts")
    sync_mode: Optional[str] = Field("hot", description="Staging/scraping mode: hot, warm, or cold")


class TriggerJobResponse(BaseModel):
    success: bool
    job_id: Optional[str] = None
    message: str
    selected_accounts: int = 0
    usernames: Optional[List[str]] = None
    job_created: bool = False
    blocked: bool = False
    reason: Optional[str] = None


class WorkerStatus(BaseModel):
    """Worker status information."""
    is_alive: bool
    last_heartbeat: Optional[datetime] = None
    current_job_id: Optional[str] = None
    current_job_status: Optional[str] = None
    pid: Optional[int] = None
    status: Optional[str] = None  # "running" | "idle" | "offline"
    status_source: Optional[str] = None  # "scrape_jobs" | "settings"
