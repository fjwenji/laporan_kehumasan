"""
Dashboard endpoints
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from datetime import date, datetime
from app.schemas.dashboard import (
    DashboardSummary, PostsResponse, PostItem, ChartData,
    EngagementData, MediaTypeData, FollowerData,
    AccountOption, AccountFilterResponse
)
from app.api.deps import get_current_user
from app.database import get_db_cursor
from app.schemas.instagram_accounts import InstagramAccount, InstagramAccountResponse

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def normalize_media_type(raw_type: str) -> str:
    """
    Normalize media type to standard values.
    Never return 'unknown' - use fallback values instead.
    """
    if not raw_type:
        return "UNCLASSIFIED_REVIEW"

    normalized = raw_type.lower().strip()

    # Direct mappings
    if normalized in ["image", "foto", "gambar", "img"]:
        return "IMAGE"
    elif normalized in ["carousel", "album", "sidecar", "graphsidecar"]:
        return "CAROUSEL"
    elif normalized in ["reels", "reel"]:
        return "REELS"
    elif normalized in ["video", "tv"]:
        return "VIDEO"
    elif normalized in ["unknown", "", "none", "null"]:
        return "UNCLASSIFIED_REVIEW"

    return "UNCLASSIFIED_REVIEW"


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(..., description="End date (YYYY-MM-DD)"),
    username: Optional[str] = Query(None, description="Filter by specific account"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get dashboard summary for a given period.
    """
    with get_db_cursor(commit=False) as cursor:
        # Base query for posts in period
        base_query = """
            FROM posts p
            LEFT JOIN accounts a ON p.username = a.username
            WHERE DATE(p.timestamp) BETWEEN %s AND %s
        """
        params = [start, end]

        if username:
            base_query += " AND p.username = %s"
            params.append(username)

        # Total accounts
        if username:
            cursor.execute("SELECT COUNT(*) as cnt FROM accounts WHERE is_active = TRUE AND username = %s", (username,))
        else:
            cursor.execute("SELECT COUNT(*) as cnt FROM accounts WHERE is_active = TRUE")
        total_accounts = cursor.fetchone()["cnt"]

        # Active accounts (accounts with posts in period)
        cursor.execute(f"""
            SELECT COUNT(DISTINCT p.username) as cnt
            {base_query}
        """, params)
        active_accounts = cursor.fetchone()["cnt"]

        # Profile metrics from accounts table
        if username:
            cursor.execute("""
                SELECT
                    COALESCE(SUM(followers_count), 0) as total_followers,
                    COALESCE(SUM(following_count), 0) as total_following,
                    COUNT(CASE WHEN followers_count IS NOT NULL THEN 1 END) as accounts_with_followers
                FROM accounts
                WHERE is_active = TRUE AND username = %s
            """, (username,))
        else:
            cursor.execute("""
                SELECT
                    COALESCE(SUM(followers_count), 0) as total_followers,
                    COALESCE(SUM(following_count), 0) as total_following,
                    COUNT(CASE WHEN followers_count IS NOT NULL THEN 1 END) as accounts_with_followers
                FROM accounts
                WHERE is_active = TRUE
            """)
        profile_metrics = cursor.fetchone()
        total_followers = int(profile_metrics["total_followers"])
        total_following = int(profile_metrics["total_following"])
        accounts_with_followers = int(profile_metrics["accounts_with_followers"])
        avg_followers = round(total_followers / accounts_with_followers, 1) if accounts_with_followers > 0 else 0.0

        # Total posts
        cursor.execute(f"SELECT COUNT(*) as cnt {base_query}", params)
        total_posts = cursor.fetchone()["cnt"]

        # New posts
        cursor.execute(f"SELECT COUNT(*) as cnt {base_query} AND p.is_new_post = TRUE", params)
        new_posts = cursor.fetchone()["cnt"]

        # Engagement metrics - only sum if not NULL
        cursor.execute(f"""
            SELECT
                COALESCE(SUM(p.like_count), 0) as total_likes,
                COALESCE(SUM(p.comments_count), 0) as total_comments,
                COALESCE(SUM(p.total_engagement), 0) as total_engagement,
                COALESCE(SUM(CASE WHEN p.view_count IS NOT NULL THEN p.view_count ELSE 0 END), 0) as total_views
            {base_query}
        """, params)
        engagement = cursor.fetchone()

        # Failed posts
        cursor.execute(f"""
            SELECT COUNT(*) as cnt {base_query}
            AND p.status_scraping IN ('LOGIN_WALL', 'PAGE_NOT_FOUND', 'RATE_LIMITED', 'PAGE_LOAD_FAILED', 'FAILED')
        """, params)
        failed_posts = cursor.fetchone()["cnt"]

        # Partial posts
        cursor.execute(f"""
            SELECT COUNT(*) as cnt {base_query}
            AND p.status_scraping IN ('PARTIAL_SUCCESS', 'FIELD_PARTIAL_NULL')
        """, params)
        partial_posts = cursor.fetchone()["cnt"]

        # Media type breakdown
        cursor.execute(f"""
            SELECT
                COALESCE(p.media_type_normalized, 'unknown') as media_type,
                COUNT(*) as cnt
            {base_query}
            GROUP BY COALESCE(p.media_type_normalized, 'unknown')
        """, params)
        media_breakdown = cursor.fetchall()

        # Initialize counters
        media_image = 0
        media_carousel = 0
        media_reels = 0
        media_video = 0
        media_unclassified = 0

        for row in media_breakdown:
            normalized = normalize_media_type(row["media_type"])
            count = row["cnt"]
            if normalized == "IMAGE":
                media_image = count
            elif normalized == "CAROUSEL":
                media_carousel = count
            elif normalized == "REELS":
                media_reels = count
            elif normalized == "VIDEO":
                media_video = count
            else:
                media_unclassified += count

    return DashboardSummary(
        total_accounts=total_accounts,
        active_accounts=active_accounts,
        total_followers=total_followers,
        total_following=total_following,
        avg_followers=avg_followers,
        accounts_with_followers=accounts_with_followers,
        total_posts=total_posts,
        new_posts=new_posts,
        failed_posts=failed_posts,
        partial_posts=partial_posts,
        total_likes=int(engagement["total_likes"]),
        total_comments=int(engagement["total_comments"]),
        total_engagement=int(engagement["total_engagement"]),
        total_views=int(engagement["total_views"]),
        media_image=media_image,
        media_carousel=media_carousel,
        media_reels=media_reels,
        media_video=media_video,
        media_unclassified=media_unclassified
    )


@router.get("/posts", response_model=PostsResponse)
async def get_posts(
    start: date = Query(..., description="Start date"),
    end: date = Query(..., description="End date"),
    username: Optional[str] = Query(None, description="Filter by account"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get posts for a given period with pagination.
    """
    with get_db_cursor(commit=False) as cursor:
        # Build query
        where_clause = "WHERE DATE(p.timestamp) BETWEEN %s AND %s"
        params = [start, end]

        if username:
            where_clause += " AND p.username = %s"
            params.append(username)

        # Get total count
        cursor.execute(f"SELECT COUNT(*) as cnt FROM posts p {where_clause}", params)
        total = cursor.fetchone()["cnt"]

        # Get posts
        cursor.execute(f"""
            SELECT
                p.id, p.username, p.nama_unit, p.post_url, p.shortcode,
                p.caption, p.timestamp,
                COALESCE(p.media_type_normalized, 'unknown') as media_type,
                p.like_count, p.comments_count, p.total_engagement,
                p.view_count, p.play_count, p.share_count, p.save_count,
                p.view_parse_status,
                p.status_scraping, p.status_periode, p.is_new_post
            FROM posts p
            {where_clause}
            ORDER BY p.timestamp DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        posts_raw = cursor.fetchall()

    posts = []
    for p in posts_raw:
        normalized = normalize_media_type(p["media_type"])
        posts.append(PostItem(
            id=p["id"],
            username=p["username"],
            nama_unit=p.get("nama_unit"),
            post_url=p["post_url"] or "",
            shortcode=p["shortcode"] or "",
            caption=p.get("caption"),
            timestamp=p.get("timestamp"),
            media_type=normalized,
            media_type_normalized=normalized,
            like_count=p.get("like_count"),
            comment_count=p.get("comments_count"),
            total_engagement=p.get("total_engagement"),
            view_count=p.get("view_count"),  # Keep NULL as NULL, don't convert to 0
            play_count=p.get("play_count"),
            share_count=p.get("share_count"),
            save_count=p.get("save_count"),
            view_parse_status=p.get("view_parse_status"),
            status_scraping=p.get("status_scraping") or "UNKNOWN",
            status_periode=p.get("status_periode"),
            is_new_post=p.get("is_new_post", False)
        ))

    return PostsResponse(
        posts=posts,
        total=total,
        period_start=str(start),
        period_end=str(end)
    )


@router.get("/charts", response_model=ChartData)
async def get_chart_data(
    start: date = Query(..., description="Start date"),
    end: date = Query(..., description="End date"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get chart data for dashboard visualization.
    """
    with get_db_cursor(commit=False) as cursor:
        # Engagement by account with followers
        cursor.execute("""
            SELECT
                p.username,
                a.nama_unit,
                a.followers_count,
                COALESCE(SUM(p.total_engagement), 0) as total_engagement,
                COALESCE(SUM(p.like_count), 0) as like_count,
                COALESCE(SUM(p.comments_count), 0) as comment_count,
                COUNT(*) as post_count
            FROM posts p
            LEFT JOIN accounts a ON p.username = a.username
            WHERE DATE(p.timestamp) BETWEEN %s AND %s
            GROUP BY p.username, a.nama_unit, a.followers_count
            ORDER BY total_engagement DESC
        """, [start, end])
        engagement_data = cursor.fetchall()

        # Posts by account
        cursor.execute("""
            SELECT
                p.username,
                a.nama_unit,
                COUNT(*) as post_count
            FROM posts p
            LEFT JOIN accounts a ON p.username = a.username
            WHERE DATE(p.timestamp) BETWEEN %s AND %s
            GROUP BY p.username, a.nama_unit
            ORDER BY post_count DESC
        """, [start, end])
        posts_data = cursor.fetchall()

        # Media type breakdown
        cursor.execute("""
            SELECT
                COALESCE(p.media_type_normalized, 'unknown') as media_type,
                COUNT(*) as cnt
            FROM posts p
            WHERE DATE(p.timestamp) BETWEEN %s AND %s
            GROUP BY COALESCE(p.media_type_normalized, 'unknown')
        """, [start, end])
        media_raw = cursor.fetchall()

        # Followers by account
        cursor.execute("""
            SELECT
                username,
                nama_unit,
                followers_count,
                following_count,
                profile_posts_count,
                is_active
            FROM accounts
            WHERE is_active = TRUE
            ORDER BY COALESCE(followers_count, 0) DESC
        """)
        followers_data = cursor.fetchall()

    # Process engagement data with engagement rate
    engagement_by_account = []
    for row in engagement_data:
        followers = row.get("followers_count")
        total_eng = int(row["total_engagement"])
        engagement_rate = None

        if followers and followers > 0:
            # engagement_rate = (likes + comments) / followers * 100
            engagement_rate = round((total_eng / followers) * 100, 2)

        engagement_by_account.append(EngagementData(
            username=row["username"],
            nama_unit=row.get("nama_unit") or row["username"],
            total_engagement=total_eng,
            like_count=int(row["like_count"]),
            comment_count=int(row["comment_count"]),
            post_count=row["post_count"],
            followers_count=followers,
            engagement_rate=engagement_rate
        ))

    # Process posts data
    posts_by_account = [
        {
            "username": row["username"],
            "nama_unit": row.get("nama_unit") or row["username"],
            "count": row["post_count"]
        }
        for row in posts_data
    ]

    # Process media type breakdown
    total_posts = sum(row["cnt"] for row in media_raw)
    media_type_breakdown = []
    interaction_tiers = {"high": 0, "medium": 0, "low": 0}

    for row in media_raw:
        normalized = normalize_media_type(row["media_type"])
        count = row["cnt"]
        percentage = (count / total_posts * 100) if total_posts > 0 else 0

        media_type_breakdown.append(MediaTypeData(
            media_type=normalized,
            count=count,
            percentage=round(percentage, 1)
        ))

        # Interaction tiers based on engagement
        if normalized in ["IMAGE", "CAROUSEL", "VIDEO"]:
            interaction_tiers["medium"] += count
        elif normalized == "REELS":
            interaction_tiers["high"] += count
        else:
            interaction_tiers["low"] += count

    # Process followers data
    followers_by_account = [
        FollowerData(
            username=row["username"],
            nama_unit=row.get("nama_unit") or row["username"],
            followers_count=row.get("followers_count"),
            following_count=row.get("following_count"),
            profile_posts_count=row.get("profile_posts_count"),
            is_active=bool(row.get("is_active", True))
        )
        for row in followers_data
    ]

    return ChartData(
        engagement_by_account=engagement_by_account,
        posts_by_account=posts_by_account,
        media_type_breakdown=media_type_breakdown,
        interaction_tiers=interaction_tiers,
        followers_by_account=followers_by_account
    )


@router.get("/accounts", response_model=AccountFilterResponse)
async def get_accounts(
    kategori: Optional[str] = Query(None, description="Filter by kategori (KANWIL, PUSAT, etc)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get accounts for filter dropdown.
    """
    with get_db_cursor(commit=False) as cursor:
        query = """
            SELECT username, nama_unit, kategori_unit, wilayah
            FROM accounts
            WHERE is_active = TRUE
        """
        params = []

        if kategori:
            query += " AND kategori_unit = %s"
            params.append(kategori)

        query += " ORDER BY nama_unit ASC"

        cursor.execute(query, params)
        accounts = cursor.fetchall()

    return AccountFilterResponse(
        accounts=[
            AccountOption(
                username=row["username"],
                nama_unit=row.get("nama_unit") or row["username"],
                kategori_unit=row.get("kategori_unit"),
                wilayah=row.get("wilayah")
            )
            for row in accounts
        ],
        total=len(accounts)
    )


@router.get("/instagram-accounts", response_model=InstagramAccountResponse)
async def get_instagram_accounts(
    search: Optional[str] = Query(None, description="Search username or nama_unit"),
    jenis_akun: Optional[str] = Query(None, description="Filter by jenis akun"),
    status: Optional[str] = Query(None, description="Filter by status (aktif/nonaktif)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of Instagram accounts (read-only, accessible by all authenticated users).
    """
    def map_jenis(jenis: str) -> str:
        mapping = {
            "kanwil": "KANWIL", "kppn": "KPPN", "pusat": "PUSAT", "kanver_lainnya": "KANVER_LAINNYA",
        }
        return mapping.get(jenis.lower().strip(), "KANWIL")

    with get_db_cursor(commit=False) as cursor:
        # Build query
        query = "SELECT * FROM accounts WHERE 1=1"
        count_query = "SELECT COUNT(*) as cnt FROM accounts WHERE 1=1"
        params = []
        count_params = []

        if search:
            query += " AND (username LIKE %s OR nama_unit LIKE %s)"
            count_query += " AND (username LIKE %s OR nama_unit LIKE %s)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern])
            count_params.extend([search_pattern, search_pattern])

        if jenis_akun:
            query += " AND kategori_unit = %s"
            count_query += " AND kategori_unit = %s"
            mapped_jenis = map_jenis(jenis_akun)
            params.append(mapped_jenis)
            count_params.append(mapped_jenis)

        if status is not None:
            if status.lower() == "aktif":
                query += " AND is_active = TRUE"
                count_query += " AND is_active = TRUE"
            elif status.lower() == "nonaktif":
                query += " AND is_active = FALSE"
                count_query += " AND is_active = FALSE"

        # Get total count
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()["cnt"]

        # Get active/inactive counts
        cursor.execute("SELECT COUNT(*) as cnt FROM accounts WHERE is_active = TRUE")
        active_count = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM accounts WHERE is_active = FALSE")
        inactive_count = cursor.fetchone()["cnt"]

        # Get accounts
        query += " ORDER BY nama_unit ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        cursor.execute(query, params)
        accounts = cursor.fetchall()

    result_accounts = []
    for acc in accounts:
        result_accounts.append(InstagramAccount(
            id=acc["id"],
            username=acc["username"],
            nama_unit=acc["nama_unit"],
            jenis_akun=acc.get("kategori_unit", "KANWIL").lower(),
            status="aktif" if acc.get("is_active", True) else "nonaktif",
            notes=acc.get("notes"),
            is_active=acc.get("is_active", True),
            created_at=acc.get("created_at"),
            updated_at=acc.get("updated_at")
        ))

    return InstagramAccountResponse(
        accounts=result_accounts,
        total=total,
        active_count=active_count,
        inactive_count=inactive_count
    )
