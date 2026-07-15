"""
Pydantic schemas for Telegram and Scheduler Settings
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============================================================
# ENUMS
# ============================================================

class ScheduleMode(str, Enum):
    INTERVAL = "interval"
    DAILY = "daily"


class AccountScope(str, Enum):
    KANWIL = "kanwil"
    KPPN = "kppn"
    PUSAT = "pusat"
    ALL = "all"


class WorkerStatusEnum(str, Enum):
    ALIVE = "alive"
    IDLE = "idle"
    RUNNING = "running"
    STUCK = "stuck"
    STOPPED = "stopped"
    ERROR = "error"


# ============================================================
# TELEGRAM SCHEMAS
# ============================================================

class TelegramRecipientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    chat_id: str = Field(..., min_length=1, max_length=100)


class TelegramRecipientCreate(TelegramRecipientBase):
    pass


class TelegramRecipientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    chat_id: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None


class TelegramRecipient(TelegramRecipientBase):
    id: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TelegramRecipientsResponse(BaseModel):
    recipients: List[TelegramRecipient]
    total: int


class TelegramSettingsBase(BaseModel):
    enabled: bool = False
    notify_new_post: bool = True


class TelegramSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    bot_token: Optional[str] = Field(None, max_length=200)
    notify_new_post: Optional[bool] = None


class TelegramTokenRequest(BaseModel):
    bot_token: str = Field(..., min_length=10, max_length=200)


class TelegramSettingsResponse(BaseModel):
    enabled: bool
    bot_token_masked: str  # Masked for display
    notify_new_post: bool
    recipient_count: int
    recipients: List[TelegramRecipient]


class TelegramTestRequest(BaseModel):
    message: Optional[str] = Field(
        default="🔔 Test notification from Mayz Monitoring System",
        max_length=500
    )


class TelegramTestResponse(BaseModel):
    success: bool
    message: str
    details: Optional[str] = None


# ============================================================
# SCHEDULER SCHEMAS
# ============================================================

class SchedulerSettingsBase(BaseModel):
    is_enabled: bool = True
    schedule_mode: ScheduleMode = ScheduleMode.INTERVAL
    interval_minutes: int = Field(default=60, ge=15, le=1440)
    daily_times: Optional[str] = None  # Comma-separated HH:MM
    account_scope: AccountScope = AccountScope.ALL
    account_limit: int = Field(default=15, ge=1, le=100)
    cooldown_seconds: int = Field(default=5, ge=0, le=60)


class SchedulerSettingsUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    schedule_mode: Optional[ScheduleMode] = None
    interval_minutes: Optional[int] = Field(None, ge=15, le=1440)
    daily_times: Optional[str] = Field(None, max_length=200)
    account_scope: Optional[AccountScope] = None
    account_limit: Optional[int] = Field(None, ge=1, le=100)
    cooldown_seconds: Optional[int] = Field(None, ge=0, le=60)


class SchedulerSettingsResponse(BaseModel):
    is_enabled: bool
    schedule_mode: ScheduleMode
    interval_minutes: int
    daily_times: List[str]
    account_scope: AccountScope
    account_limit: int
    cooldown_seconds: int
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class SchedulerStatusResponse(BaseModel):
    status: str  # SYNCED, NOT_SYNCED, DISABLED, ERROR
    message: str
    is_enabled: bool
    is_synced: bool  # Whether OS task scheduler is in sync with database
    schedule_mode: ScheduleMode
    interval_minutes: int
    daily_times: List[str]
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    last_run_status: Optional[str] = None
    worker_status: WorkerStatusEnum
    worker_last_heartbeat: Optional[datetime] = None
    current_job_id: Optional[str] = None


class SchedulerSyncResponse(BaseModel):
    success: bool
    message: str
    tasks_synced: int = 0
    errors: List[str] = []


# ============================================================
# COMMON SCHEMAS
# ============================================================

class SuccessResponse(BaseModel):
    success: bool
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None
