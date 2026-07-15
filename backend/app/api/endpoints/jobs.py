"""
Job monitoring endpoints (Admin only)
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from datetime import datetime
from app.schemas.job import (
    JobsResponse, JobItem, FailedItemsResponse, FailedItem,
    NodeFlowResponse, NodeFlowItem, AlertsResponse, AlertItem,
    TriggerJobRequest, TriggerJobResponse, WorkerStatus, JobStatus, NodeStatus
)
from app.api.deps import get_current_user, get_current_admin_user
from app.database import get_db_cursor

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


def get_node_status_for_job(job: Optional[dict]) -> str:
    """Determine node status based on job status."""
    if not job:
        return NodeStatus.IDLE.value

    status = job.get("status", "").upper()

    if status == JobStatus.RUNNING.value:
        # Check if stuck
        heartbeat = job.get("worker_heartbeat_at")
        if heartbeat:
            if isinstance(heartbeat, str):
                try:
                    heartbeat = datetime.fromisoformat(heartbeat)
                except:
                    pass
            if heartbeat:
                elapsed = (datetime.now() - heartbeat).total_seconds()
                if elapsed > 120:  # 2 minutes
                    return NodeStatus.STUCK.value
        return NodeStatus.RUNNING.value

    status_map = {
        JobStatus.SUCCESS.value: NodeStatus.SUCCESS.value,
        JobStatus.PARTIAL_SUCCESS.value: NodeStatus.WARNING.value,
        JobStatus.FAILED.value: NodeStatus.FAILED.value,
        JobStatus.RATE_LIMITED.value: NodeStatus.WARNING.value,
        JobStatus.QUEUED.value: NodeStatus.IDLE.value,
        JobStatus.SKIPPED.value: NodeStatus.IDLE.value,
    }
    return status_map.get(status, NodeStatus.IDLE.value)


@router.get("/", response_model=JobsResponse)
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Get list of scraping jobs (Admin only).
    """
    with get_db_cursor(commit=False) as cursor:
        query = """
            SELECT * FROM scrape_jobs
        """
        params = []

        if status:
            query += " WHERE status = %s"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        jobs = cursor.fetchall()

        # Count running and queued
        cursor.execute("SELECT COUNT(*) as cnt FROM scrape_jobs WHERE status = 'RUNNING'")
        running_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM scrape_jobs WHERE status = 'QUEUED'")
        queued_count = cursor.fetchone()["cnt"]

    return JobsResponse(
        jobs=[JobItem(**job) for job in jobs],
        total=len(jobs),
        running_count=running_count,
        queued_count=queued_count
    )


@router.get("/current")
async def get_current_job(current_user: dict = Depends(get_current_admin_user)):
    """
    Get currently running job info.
    """
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT * FROM scrape_jobs
            WHERE status = 'RUNNING'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        job = cursor.fetchone()

    if not job:
        return {"running": False, "job": None}

    return {
        "running": True,
        "job": JobItem(**job) if job else None
    }


@router.get("/node-flow", response_model=NodeFlowResponse)
async def get_node_flow(current_user: dict = Depends(get_current_admin_user)):
    """
    Get node workflow status (n8n-like visualization).
    """
    with get_db_cursor(commit=False) as cursor:
        # Get current job
        cursor.execute("""
            SELECT * FROM scrape_jobs
            WHERE status = 'RUNNING'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        current_job = cursor.fetchone()

        # Get last job
        cursor.execute("""
            SELECT * FROM scrape_jobs
            ORDER BY created_at DESC
            LIMIT 1
        """)
        last_job = cursor.fetchone()

        # Worker status from heartbeat
        worker_alive = False
        worker_last_heartbeat = None
        if current_job:
            heartbeat = current_job.get("worker_heartbeat_at")
            if heartbeat:
                if isinstance(heartbeat, str):
                    try:
                        heartbeat = datetime.fromisoformat(heartbeat)
                    except:
                        pass
                if heartbeat:
                    elapsed = (datetime.now() - heartbeat).total_seconds()
                    worker_alive = elapsed < 120  # 2 minutes
                    worker_last_heartbeat = heartbeat

    # Build nodes
    nodes = [
        NodeFlowItem(
            id="scheduler",
            name="Scheduler",
            status=NodeStatus.SUCCESS.value,
            description="Cron job scheduler",
            last_updated=datetime.now()
        ),
        NodeFlowItem(
            id="queue",
            name="Job Queue",
            status=NodeStatus.IDLE.value if not current_job else NodeStatus.RUNNING.value,
            description="Pending jobs" if not current_job else f"Processing: {current_job.get('job_id', '')[:20]}...",
            last_updated=datetime.now()
        ),
        NodeFlowItem(
            id="scraper",
            name="Scraper Worker",
            status=get_node_status_for_job(current_job),
            description=f"Worker PID: {current_job.get('worker_pid')}" if current_job else "Idle",
            last_updated=worker_last_heartbeat,
            details={
                "accounts_processed": current_job.get("total_accounts") if current_job else 0,
                "posts_found": current_job.get("total_posts_found") if current_job else 0
            }
        ),
        NodeFlowItem(
            id="parser",
            name="Parser",
            status=NodeStatus.SUCCESS.value if current_job and current_job.get("total_posts_found", 0) > 0 else NodeStatus.IDLE.value,
            description="Data parsing and normalization",
            last_updated=datetime.now()
        ),
        NodeFlowItem(
            id="database",
            name="Database",
            status=NodeStatus.SUCCESS.value,
            description="MySQL storage",
            last_updated=datetime.now()
        ),
        NodeFlowItem(
            id="telegram",
            name="Telegram Alert",
            status=NodeStatus.IDLE.value,
            description="Notification service",
            last_updated=datetime.now()
        ),
        NodeFlowItem(
            id="export",
            name="Excel Export",
            status=NodeStatus.IDLE.value,
            description="Report generation",
            last_updated=datetime.now()
        ),
    ]

    return NodeFlowResponse(
        nodes=nodes,
        current_job=JobItem(**current_job) if current_job else None,
        worker_status="alive" if worker_alive else "dead",
        worker_last_heartbeat=worker_last_heartbeat
    )


@router.get("/failed", response_model=FailedItemsResponse)
async def get_failed_items(
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Get failed scraping items.
    """
    with get_db_cursor(commit=False) as cursor:
        query = "SELECT * FROM job_failed_items"
        params = []

        if job_id:
            query += " WHERE job_id = %s"
            params.append(job_id)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        items = cursor.fetchall()

        # Total count
        cursor.execute("SELECT COUNT(*) as cnt FROM job_failed_items")
        total = cursor.fetchone()["cnt"]

    return FailedItemsResponse(
        items=[FailedItem(**item) for item in items],
        total=total
    )


@router.get("/worker-status", response_model=WorkerStatus)
async def get_worker_status(current_user: dict = Depends(get_current_admin_user)):
    """
    Get scraper worker status.

    Logic:
    1. If job RUNNING with fresh heartbeat -> status=running, is_alive=true, source=scrape_jobs
    2. Else if settings.worker_last_heartbeat fresh -> status=idle, is_alive=true, source=settings
    3. Else -> status=offline, is_alive=false
    """
    HEARTBEAT_THRESHOLD = 120  # 2 minutes, aligned with scheduler/status

    with get_db_cursor(commit=False) as cursor:
        # Get running job
        cursor.execute("""
            SELECT * FROM scrape_jobs
            WHERE status = 'RUNNING'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        running_job = cursor.fetchone()

    if running_job:
        heartbeat = running_job.get("worker_heartbeat_at")
        worker_alive = False
        if heartbeat:
            if isinstance(heartbeat, str):
                try:
                    heartbeat = datetime.fromisoformat(heartbeat)
                except:
                    pass
            if heartbeat:
                elapsed = (datetime.now() - heartbeat).total_seconds()
                worker_alive = elapsed < HEARTBEAT_THRESHOLD

        return WorkerStatus(
            is_alive=worker_alive,
            last_heartbeat=heartbeat,
            current_job_id=running_job.get("job_id"),
            current_job_status=running_job.get("status"),
            pid=running_job.get("worker_pid"),
            status="running" if worker_alive else "stuck",
            status_source="scrape_jobs"
        )

    # Fallback: check settings.worker_last_heartbeat
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT setting_value FROM settings
            WHERE setting_key = 'worker_last_heartbeat'
        """)
        row = cursor.fetchone()
        settings_heartbeat = row["setting_value"] if row else None

    if settings_heartbeat:
        if isinstance(settings_heartbeat, str):
            try:
                settings_heartbeat = datetime.fromisoformat(settings_heartbeat)
            except:
                settings_heartbeat = None

        if settings_heartbeat:
            elapsed = (datetime.now() - settings_heartbeat).total_seconds()
            if elapsed < HEARTBEAT_THRESHOLD:
                return WorkerStatus(
                    is_alive=True,
                    last_heartbeat=settings_heartbeat,
                    status="idle",
                    status_source="settings"
                )

    return WorkerStatus(is_alive=False, status="offline")




def _select_trigger_accounts(cursor, request: TriggerJobRequest) -> list[str]:
    if request.account_ids or request.usernames:
        clauses, params = [], []
        if request.account_ids:
            clauses.append("id IN (" + ",".join(["%s"] * len(request.account_ids)) + ")")
            params.extend(request.account_ids)
        if request.usernames:
            clauses.append("username IN (" + ",".join(["%s"] * len(request.usernames)) + ")")
            params.extend(request.usernames)
        cursor.execute(
            f"SELECT username FROM accounts WHERE is_active = 1 AND ({' OR '.join(clauses)}) ORDER BY username",
            params,
        )
        usernames = [row["username"] for row in cursor.fetchall()]
    else:
        cursor.execute("SELECT username FROM accounts WHERE is_active = 1 ORDER BY username")
        usernames = [row["username"] for row in cursor.fetchall()]

    return usernames[:request.account_limit] if request.account_limit else usernames



def _normalize_sync_mode(value: Optional[str]) -> str:
    mode = (value or "hot").lower()
    return mode if mode in {"hot", "warm", "cold"} else "hot"

@router.post("/trigger", response_model=TriggerJobResponse)
async def trigger_job(
    request: TriggerJobRequest,
    current_user: dict = Depends(get_current_admin_user)
):
    import json

    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM scrape_jobs WHERE status = 'RUNNING' LIMIT 1")
        if cursor.fetchone():
            return TriggerJobResponse(success=False, message="Job sedang berjalan. Tunggu sampai selesai.")

        selected_usernames = _select_trigger_accounts(cursor, request)
        explicit_selection = bool(request.account_ids or request.usernames)

        if not explicit_selection and len(selected_usernames) > 34 and not request.allow_all_active:
            return TriggerJobResponse(
                success=False,
                message="Default trigger diblokir karena akun aktif terlalu banyak. Gunakan usernames/account_ids.",
                selected_accounts=len(selected_usernames),
                usernames=selected_usernames[:10],
                job_created=False,
                blocked=True,
                reason="too_many_active_accounts",
            )

        if request.dry_run:
            return TriggerJobResponse(
                success=True,
                message=f"Dry run: {len(selected_usernames)} akun dipilih",
                selected_accounts=len(selected_usernames),
                usernames=selected_usernames[:10] if len(selected_usernames) > 10 else selected_usernames,
                job_created=False,
            )

        if not selected_usernames:
            return TriggerJobResponse(
                success=False,
                message="Tidak ada akun yang dipilih. Periksa account_ids atau usernames.",
                reason="empty_selection",
            )

        job_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cursor.execute("""
            INSERT INTO scrape_jobs (job_id, job_type, trigger_type, status, period_start, period_end, requested_by)
            VALUES (%s, %s, 'MANUAL', 'QUEUED', %s, %s, %s)
        """, (
            job_id, request.job_type.value, request.period_start, request.period_end, current_user["username"]
        ))
        cursor.execute("""
            INSERT INTO settings (setting_key, setting_value, description)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE setting_value = %s
        """, (
            f"job_accounts_{job_id}",
            json.dumps(selected_usernames),
            f"Selected accounts for job {job_id}",
            json.dumps(selected_usernames),
        ))
        sync_mode = _normalize_sync_mode(request.sync_mode)
        cursor.execute("""
            INSERT INTO settings (setting_key, setting_value, description)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE setting_value = %s
        """, (f"job_mode_{job_id}", sync_mode, f"Staging mode for job {job_id}", sync_mode))

    return TriggerJobResponse(
        success=True,
        job_id=job_id,
        message=f"Job {request.job_type.value} berhasil dibuat untuk {len(selected_usernames)} akun",
        selected_accounts=len(selected_usernames),
        usernames=selected_usernames,
        job_created=True,
    )


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Get recent alerts/notifications.
    """
    with get_db_cursor(commit=False) as cursor:
        # Get recent failed jobs
        cursor.execute("""
            SELECT * FROM scrape_jobs
            WHERE status IN ('FAILED', 'PARTIAL_SUCCESS')
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        failed_jobs = cursor.fetchall()

        # Get stuck jobs
        cursor.execute("""
            SELECT * FROM scrape_jobs
            WHERE status = 'RUNNING'
            AND worker_heartbeat_at < DATE_SUB(NOW(), INTERVAL 2 MINUTE)
        """)
        stuck_jobs = cursor.fetchall()

        # Get new posts (recent)
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM posts
            WHERE is_new_post = TRUE
            AND first_seen_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
        """)
        new_posts_count = cursor.fetchone()["cnt"]

        # Get failed items count
        cursor.execute("SELECT COUNT(*) as cnt FROM job_failed_items")
        failed_items_count = cursor.fetchone()["cnt"]

    alerts = []
    alert_id = 1

    # Add failed job alerts
    for job in failed_jobs:
        alerts.append(AlertItem(
            id=alert_id,
            alert_type="job_failed",
            title=f"Job Gagal: {job.get('job_type', 'UNKNOWN')}",
            message=job.get('error_message', 'Unknown error')[:200],
            severity="danger",
            created_at=job.get('created_at', datetime.now()),
            metadata={"job_id": job.get("job_id")}
        ))
        alert_id += 1

    # Add stuck job alerts
    for job in stuck_jobs:
        alerts.append(AlertItem(
            id=alert_id,
            alert_type="job_stuck",
            title=f"Job Stuck: {job.get('job_id', '')[:20]}",
            message="Worker heartbeat tidak aktif",
            severity="danger",
            created_at=job.get('created_at', datetime.now()),
            metadata={"job_id": job.get("job_id")}
        ))
        alert_id += 1

    # Add new posts alert
    if new_posts_count > 0:
        alerts.append(AlertItem(
            id=alert_id,
            alert_type="new_post",
            title=f"{new_posts_count} Postingan Baru",
            message=f"Ditemukan {new_posts_count} postingan baru dari scraping terakhir",
            severity="info",
            created_at=datetime.now(),
            metadata={"count": new_posts_count}
        ))
        alert_id += 1

    # Add failed items alert
    if failed_items_count > 0:
        alerts.append(AlertItem(
            id=alert_id,
            alert_type="failed_count",
            title=f"{failed_items_count} Item Gagal",
            message=f"Total {failed_items_count} item gagal diekstrak",
            severity="warning",
            created_at=datetime.now(),
            metadata={"count": failed_items_count}
        ))

    # Sort by created_at desc
    alerts.sort(key=lambda x: x.created_at, reverse=True)

    return AlertsResponse(
        alerts=alerts[:limit],
        total=len(alerts),
        unread_count=len([a for a in alerts if not a.is_read])
    )
