"""
Job Service - Business logic untuk scrape job management.
Rule-based intelligence untuk job scheduling dan deduplication.
"""

import uuid
from datetime import datetime, date, time
from typing import Tuple, Optional, Dict, List
from src.db_repository import (
    create_scrape_job,
    update_scrape_job,
    get_running_job,
    get_queued_job,
    get_last_success_latest_sync,
    get_recent_jobs,
    get_job_by_id,
    add_job_log,
)
from src.database import get_setting


def generate_job_id(prefix: str = "job") -> str:
    """Generate unique job ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{prefix}_{timestamp}_{unique_id}"


def request_latest_sync(requested_by: str = "system") -> Tuple[bool, str]:
    """
    Request a latest sync job.
    Returns: (success: bool, message: str)
    """
    # Check if there's already a running job
    running = get_running_job()
    if running:
        return False, f"Job sedang berjalan ({running['job_id']}). Tunggu sampai selesai."

    # Check if there's a queued job
    queued = get_queued_job()
    if queued:
        return False, f"Job sudah dalam antrian ({queued['job_id']}). Tidak perlu membuat job baru."

    # Create new job
    job_id = generate_job_id("latest_sync")
    success, job_num = create_scrape_job(
        job_id=job_id,
        job_type="LATEST_SYNC",
        trigger_type="MANUAL" if requested_by != "system" else "SCHEDULED",
        requested_by=requested_by,
    )

    if success:
        return True, f"Job sinkronisasi terbaru berhasil dibuat: {job_id}"
    return False, "Gagal membuat job sinkronisasi."


def request_period_sync(
    period_start: date,
    period_end: date,
    requested_by: str = "system"
) -> Tuple[bool, str]:
    """
    Request a period sync job.
    Returns: (success: bool, message: str)
    """
    # Validate dates
    if period_start > period_end:
        return False, "Tanggal mulai tidak boleh lebih besar dari tanggal selesai."

    # Limit period to 90 days
    delta = (period_end - period_start).days
    if delta > 90:
        return False, "Periode maksimal adalah 90 hari."

    # Check if there's already a running job
    running = get_running_job()
    if running:
        return False, f"Job sedang berjalan ({running['job_id']}). Tunggu sampai selesai."

    # Check for duplicate running/queued job for same period
    recent_jobs = get_recent_jobs(limit=5)
    for job in recent_jobs:
        if job["status"] in ["QUEUED", "RUNNING"]:
            if job["job_type"] == "PERIOD_SYNC":
                job_start = job.get("period_start")
                job_end = job.get("period_end")
                if job_start and job_end:
                    # Check if periods overlap
                    if (period_start <= job_end and period_end >= job_start):
                        return False, f"Job untuk periode ini sudah ada ({job['job_id']})."

    # Create new job
    job_id = generate_job_id("period_sync")
    success, job_num = create_scrape_job(
        job_id=job_id,
        job_type="PERIOD_SYNC",
        trigger_type="MANUAL" if requested_by != "system" else "SCHEDULED",
        period_start=period_start,
        period_end=period_end,
        requested_by=requested_by,
    )

    if success:
        return True, f"Job sinkronisasi periode berhasil dibuat: {job_id}"
    return False, "Gagal membuat job sinkronisasi."


def request_scheduled_sync() -> Tuple[bool, str]:
    """
    Request a scheduled sync (called by cron job).
    Returns: (success: bool, message: str)
    """
    # Check if nightly sync is enabled
    enabled = get_setting("nightly_sync_enabled", "true").lower()
    if enabled != "true":
        return False, "Sinkronisasi otomatis dinonaktifkan."

    return request_latest_sync(requested_by="cron")


def prevent_duplicate_running_job() -> Tuple[bool, Optional[str]]:
    """
    Check if a job is already running.
    Returns: (should_proceed: bool, running_job_id: Optional[str])
    """
    running = get_running_job()
    if running:
        return False, running["job_id"]
    return True, None


def should_show_today_data_warning() -> Tuple[bool, str]:
    """
    Check if we should show warning that today's data is not yet available.
    Returns: (should_show: bool, message: str)
    """
    today = date.today()

    # Check if today's latest sync was successful
    last_success = get_last_success_latest_sync()
    if last_success:
        finished_at = last_success.get("finished_at")
        if finished_at:
            # Check if it was today
            job_date = finished_at.date() if isinstance(finished_at, datetime) else finished_at
            if job_date == today and last_success["status"] == "SUCCESS":
                return False, ""  # No warning needed

    # Check if there's a running job for today
    running = get_running_job()
    if running:
        created_at = running.get("created_at")
        if created_at:
            job_date = created_at.date() if isinstance(created_at, datetime) else created_at
            if job_date == today:
                return True, "Sinkronisasi data terbaru sedang berjalan."

    # Check cron times
    cron_times_str = get_setting("cron_execution_times", "08:00, 12:00, 16:30")
    
    return True, (
        "Data scraping terbaru untuk hari ini belum tersedia (atau belum ada data baru yang ditemukan). "
        f"Worker dijadwalkan mengecek otomatis pada jam: {cron_times_str}."
    )


def get_job_status(job_id: str) -> Optional[Dict]:
    """Get job status and details."""
    return get_job_by_id(job_id)


def get_current_job_status() -> Dict:
    """Get current job status for display."""
    running = get_running_job()

    if running:
        started_at = running.get("started_at") or running.get("created_at")

        return {
            "status": "RUNNING",
            "job_id": running["job_id"],
            "job_type": running["job_type"],
            "started_at": started_at,
            "message": f"Job sedang berjalan: {running['job_id']}",
        }

    queued = get_queued_job()

    if queued:
        return {
            "status": "QUEUED",
            "job_id": queued["job_id"],
            "job_type": queued["job_type"],
            "created_at": queued.get("created_at"),
            "message": f"Job dalam antrian: {queued['job_id']}",
        }

    recent = get_recent_jobs(limit=1)

    if recent:
        last = recent[0]

        return {
            "status": last["status"],
            "job_id": last["job_id"],
            "job_type": last["job_type"],
            "finished_at": last.get("finished_at"),
            "total_posts": last.get("total_posts_inserted", 0),
            "message": f"Job terakhir: {last['job_id']} - {last['status']}",
        }

    return {
        "status": "IDLE",
        "message": "Tidak ada job yang aktif.",
    }
def claim_next_job() -> Optional[Dict]:
    """
    Claim the next queued job for execution.
    Returns job dict if available, None otherwise.
    """
    # Prevent duplicate running
    should_proceed, running_id = prevent_duplicate_running_job()
    if not should_proceed:
        return None

    # Get queued job
    queued = get_queued_job()
    if not queued:
        return None

    # Mark as running
    job_id = queued["job_id"]
    update_scrape_job(
        job_id=job_id,
        status="RUNNING",
        started_at=datetime.now(),
    )

    # Return updated job
    return get_job_by_id(job_id)


def complete_job(
    job_id: str,
    status: str,
    stats: Dict = None,
    error_message: str = None,
) -> bool:
    """Mark job as complete with statistics."""
    ok = update_scrape_job(
        job_id=job_id,
        status=status,
        finished_at=datetime.now(),
        total_accounts=stats.get("total_accounts", 0) if stats else None,
        total_posts_found=stats.get("total_posts_found", 0) if stats else None,
        total_posts_inserted=stats.get("total_posts_inserted", 0) if stats else None,
        total_posts_updated=stats.get("total_posts_updated", 0) if stats else None,
        total_success=stats.get("total_success", 0) if stats else None,
        total_partial=stats.get("total_partial", 0) if stats else None,
        total_failed=stats.get("total_failed", 0) if stats else None,
        error_message=error_message,
    )

    try:
        if status in ("SUCCESS", "PARTIAL_SUCCESS"):
            add_job_log(
                job_id,
                "INFO",
                "COMPLETE",
                f"Job selesai dengan status {status}.",
            )
        elif status in ("FAILED", "SKIPPED"):
            add_job_log(
                job_id,
                "ERROR" if status == "FAILED" else "WARN",
                "COMPLETE",
                error_message or f"Job selesai dengan status {status}.",
            )
    except Exception:
        pass

    return ok
def get_pipeline_status() -> List[Dict]:
    """Get pipeline node status for UI."""
    current = get_current_job_status()
    status = current.get("status", "IDLE")

    if status == "RUNNING":
        trigger_status = "SUCCESS"
        queue_status = "SUCCESS"
        scraper_status = "RUNNING"
        parser_status = "RUNNING"
        validator_status = "RUNNING"
        storage_status = "IDLE"
        notification_status = "IDLE"
        dashboard_status = "SUCCESS"
        overall_status = "RUNNING"

    elif status == "QUEUED":
        trigger_status = "SUCCESS"
        queue_status = "RUNNING"
        scraper_status = "IDLE"
        parser_status = "IDLE"
        validator_status = "IDLE"
        storage_status = "IDLE"
        notification_status = "IDLE"
        dashboard_status = "SUCCESS"
        overall_status = "QUEUED"

    elif status == "FAILED":
        trigger_status = "SUCCESS"
        queue_status = "SUCCESS"
        scraper_status = "FAILED"
        parser_status = "FAILED"
        validator_status = "FAILED"
        storage_status = "FAILED"
        notification_status = "FAILED"
        dashboard_status = "SUCCESS"
        overall_status = "FAILED"

    elif status == "PARTIAL_SUCCESS":
        # PARTIAL_SUCCESS = ada sebagian data yang berhasil
        # Ini BUKAN error sistem, tapi data incomplete
        # Pipeline tetap SUCCESS karena sistem berjalan normal
        trigger_status = "SUCCESS"
        queue_status = "SUCCESS"
        scraper_status = "SUCCESS"  # Scraper jalan, tapi ada partial data
        parser_status = "SUCCESS"   # Parser jalan, tapi ada yang null
        validator_status = "SUCCESS"  # Validator mendeteksi null - ini normal
        storage_status = "SUCCESS"
        notification_status = "SUCCESS"
        dashboard_status = "SUCCESS"
        overall_status = "SUCCESS"  # Pipeline SUCCESS, data incomplete bukan error

    elif status == "SUCCESS":
        trigger_status = "SUCCESS"
        queue_status = "SUCCESS"
        scraper_status = "SUCCESS"
        parser_status = "SUCCESS"
        validator_status = "SUCCESS"
        storage_status = "SUCCESS"
        notification_status = "SUCCESS"
        dashboard_status = "SUCCESS"
        overall_status = "SUCCESS"

    else:  # IDLE, SKIPPED, etc.
        trigger_status = "IDLE"
        queue_status = "IDLE"
        scraper_status = "IDLE"
        parser_status = "IDLE"
        validator_status = "IDLE"
        storage_status = "IDLE"
        notification_status = "IDLE"
        dashboard_status = "SUCCESS"
        overall_status = "IDLE"

    return [
        {
            "id": "account_registry",
            "name": "Account Registry",
            "status": "SUCCESS",
            "description": "Database akun aktif",
        },
        {
            "id": "trigger",
            "name": "Trigger",
            "status": trigger_status,
            "description": "Cron / Manual",
        },
        {
            "id": "scrape_queue",
            "name": "Scrape Queue",
            "status": queue_status,
            "description": "Antrian job",
        },
        {
            "id": "instagram_scraper",
            "name": "Instagram Scraper",
            "status": scraper_status,
            "description": "Playwright + BeautifulSoup",
        },
        {
            "id": "html_parser",
            "name": "HTML Parser",
            "status": parser_status,
            "description": "Extraction logic",
        },
        {
            "id": "field_validator",
            "name": "Field Validator",
            "status": validator_status,
            "description": "Anti-null validation",
        },
        {
            "id": "mysql_storage",
            "name": "MySQL Storage",
            "status": storage_status,
            "description": "Simpan hasil",
        },
        {
            "id": "notification",
            "name": "Notification",
            "status": notification_status,
            "description": "Telegram alert",
        },
        {
            "id": "dashboard",
            "name": "Dashboard",
            "status": dashboard_status,
            "description": "Report & Export",
        },
    ]