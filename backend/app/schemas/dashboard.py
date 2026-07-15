"""
Pydantic schemas for dashboard data
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AccountSummary(BaseModel):
    """Summary for one account."""
    username: str
    nama_unit: str
    wilayah: Optional[str] = None
    kategori_unit: Optional[str] = None


class DashboardSummary(BaseModel):
    """Dashboard summary response."""
    # Account metrics
    total_accounts: int = 0
    active_accounts: int = 0

    # Profile metrics (from accounts table)
    total_followers: int = 0
    total_following: int = 0
    avg_followers: float = 0.0
    accounts_with_followers: int = 0

    # Post metrics
    total_posts: int = 0
    new_posts: int = 0
    failed_posts: int = 0
    partial_posts: int = 0

    # Engagement metrics
    total_likes: int = 0
    total_comments: int = 0
    total_engagement: int = 0
    total_views: int = 0  # Only for reels/video posts

    # Media type breakdown
    media_image: int = 0
    media_carousel: int = 0
    media_reels: int = 0
    media_video: int = 0
    media_unclassified: int = 0  # Fallback for unknown


class PostItem(BaseModel):
    """Single post item."""
    id: int
    username: str
    nama_unit: Optional[str] = None
    post_url: str
    shortcode: str
    caption: Optional[str] = None
    timestamp: Optional[datetime] = None
    media_type: str = "UNCLASSIFIED_REVIEW"  # Never show "unknown"
    media_type_normalized: str = "UNCLASSIFIED_REVIEW"
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    total_engagement: Optional[int] = None
    view_count: Optional[int] = None  # NULL = not available, not 0
    play_count: Optional[int] = None
    share_count: Optional[int] = None
    save_count: Optional[int] = None
    view_parse_status: Optional[str] = None  # AVAILABLE, NOT_EXPOSED, PARSE_FAILED, NOT_REELS
    status_scraping: str
    status_periode: Optional[str] = None
    is_new_post: bool = False

    class Config:
        from_attributes = True


class PostsResponse(BaseModel):
    """Posts list response."""
    posts: List[PostItem]
    total: int
    period_start: str
    period_end: str


class EngagementData(BaseModel):
    """Engagement data for chart."""
    username: str
    nama_unit: str
    total_engagement: int
    like_count: int
    comment_count: int
    post_count: int
    followers_count: Optional[int] = None
    engagement_rate: Optional[float] = None  # (like + comment) / followers * 100


class MediaTypeData(BaseModel):
    """Media type data for pie chart."""
    media_type: str
    count: int
    percentage: float


class FollowerData(BaseModel):
    """Follower data for chart."""
    username: str
    nama_unit: str
    followers_count: Optional[int] = None
    following_count: Optional[int] = None
    profile_posts_count: Optional[int] = None
    is_active: bool = True


class ChartData(BaseModel):
    """All chart data for dashboard."""
    engagement_by_account: List[EngagementData]
    posts_by_account: List[Dict[str, Any]]  # username, nama_unit, count
    media_type_breakdown: List[MediaTypeData]
    interaction_tiers: Dict[str, int]  # high, medium, low
    followers_by_account: List[FollowerData]


class AccountOption(BaseModel):
    """Account option for filter."""
    username: str
    nama_unit: str
    kategori_unit: Optional[str] = None
    wilayah: Optional[str] = None


class AccountFilterResponse(BaseModel):
    """Account filter response."""
    accounts: List[AccountOption]
    total: int


class AccountWithMetrics(BaseModel):
    """Account with profile metrics for detailed view."""
    username: str
    nama_unit: str
    kategori_unit: Optional[str] = None
    wilayah: Optional[str] = None
    followers_count: Optional[int] = None
    following_count: Optional[int] = None
    profile_posts_count: Optional[int] = None
    profile_metric_status: Optional[str] = None
    is_active: bool = True


class AccountsWithMetricsResponse(BaseModel):
    """Response for accounts with metrics."""
    accounts: List[AccountWithMetrics]
    total: int
    total_followers: int = 0
    total_following: int = 0
    avg_followers: float = 0.0
