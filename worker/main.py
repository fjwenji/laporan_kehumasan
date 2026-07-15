import argparse
import json
import os
import re
import signal
import sys
import threading
import time
from datetime import date, datetime as dt, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db_cursor, get_setting, set_setting, test_connection
from src.db_repository import (
    get_account_by_username,
    get_eligible_accounts_for_rolling_sync,
    normalize_media_type,
    upsert_post,
)
from src.notification_service import get_telegram_enabled, notify_new_post
from src.parser import AccountRow
from src.scraper import run_scraping

ROOT_DIR = Path(__file__).parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "worker.log"
STAGING_ROOT = ROOT_DIR / "data" / "staging"
STAGING_DIRS = {
    "hot": STAGING_ROOT / "hot",
    "warm": STAGING_ROOT / "warm",
    "cold": STAGING_ROOT / "cold",
}
MAX_DEFAULT_ACCOUNTS = 34
SCHEDULER_IDLE_SECONDS = 30
SCHEDULER_MODES = {"hot", "warm", "cold"}

FAILED_STATUSES = {
    "LOGIN_WALL", "PAGE_NOT_FOUND", "RATE_LIMITED", "PAGE_LOAD_FAILED", "FAILED",
    "INVALID_ACCOUNT_URL", "ACCOUNT_ERROR", "DETAIL_EXTRACTION_FAILED", "DETAIL_ERROR", "NO_POST_LINKS",
}
PARTIAL_STATUSES = {"PARTIAL_SUCCESS", "FIELD_PARTIAL_NULL", "LINK_COLLECTED"}


def _setup_logging():
    try:
        LOG_DIR.mkdir(exist_ok=True)
        import logging
        logging.basicConfig(
            filename=str(LOG_FILE),
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        return logging.getLogger()
    except Exception:
        return None


_logger = _setup_logging()
_idle_heartbeat = None


def _log(message: str, level: str = "INFO"):
    print(f"[{level}] {message}")
    if _logger:
        getattr(_logger, level.lower(), _logger.info)(message)


def ensure_staging_dirs():
    for path in STAGING_DIRS.values():
        path.mkdir(parents=True, exist_ok=True)


def staging_path(job_id: str, mode: str = "hot") -> Path:
    ensure_staging_dirs()
    mode = mode if mode in STAGING_DIRS else "hot"
    return STAGING_DIRS[mode] / f"{job_id}.jsonl"


def write_staging_jsonl(job_id: str, rows: list[dict], mode: str = "hot") -> tuple[bool, str, int]:
    path = staging_path(job_id, mode)
    try:
        with path.open("w", encoding="utf-8") as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        _log(f"[STAGING] JSONL written: {path} ({len(rows)} rows)")
        return True, str(path), len(rows)
    except Exception as exc:
        return False, str(exc), 0


class Heartbeat:
    def __init__(self, job_id: Optional[str] = None):
        self.job_id = job_id
        self._stop_event = threading.Event()
        self._thread = None

    def start(self, interval_seconds: int = 20):
        self._thread = threading.Thread(target=self._loop, args=(interval_seconds,), daemon=True)
        self._thread.start()

    def _loop(self, interval: int):
        while not self._stop_event.is_set():
            try:
                with get_db_cursor() as cursor:
                    if self.job_id:
                        cursor.execute(
                            "UPDATE scrape_jobs SET worker_heartbeat_at = NOW() WHERE job_id = %s AND status = 'RUNNING'",
                            (self.job_id,),
                        )
                    else:
                        cursor.execute("""
                            INSERT INTO settings (setting_key, setting_value, description)
                            VALUES ('worker_last_heartbeat', NOW(), 'Worker idle heartbeat')
                            ON DUPLICATE KEY UPDATE setting_value = NOW()
                        """)
            except Exception as exc:
                _log(f"Heartbeat failed: {exc}", "WARN")
            self._stop_event.wait(interval)

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)


def start_idle_heartbeat():
    global _idle_heartbeat
    if not _idle_heartbeat or not _idle_heartbeat._thread.is_alive():
        _idle_heartbeat = Heartbeat()
        _idle_heartbeat.start(interval_seconds=30)


def stop_idle_heartbeat():
    global _idle_heartbeat
    if _idle_heartbeat:
        _idle_heartbeat.stop()
        _idle_heartbeat = None


def get_next_job() -> Optional[dict]:
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT * FROM scrape_jobs
            WHERE status = 'QUEUED'
            ORDER BY created_at ASC
            LIMIT 1
        """)
        return cursor.fetchone()


def claim_job(job_id: str) -> bool:
    import socket
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE scrape_jobs
                SET status = 'RUNNING', started_at = NOW(), worker_id = %s, worker_pid = %s
                WHERE job_id = %s AND status = 'QUEUED'
            """, (socket.gethostname(), os.getpid(), job_id))
            return cursor.rowcount > 0
    except Exception as exc:
        _log(f"Failed to claim job: {exc}", "WARN")
        return False


def complete_job(job_id: str, status: str, stats: Optional[dict] = None):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("UPDATE scrape_jobs SET status = %s, finished_at = NOW() WHERE job_id = %s", (status, job_id))
            if stats:
                cursor.execute("""
                    UPDATE scrape_jobs SET
                        total_accounts = %s,
                        total_posts_found = %s,
                        total_posts_inserted = %s,
                        total_posts_updated = %s,
                        total_success = %s,
                        total_partial = %s,
                        total_failed = %s
                    WHERE job_id = %s
                """, (
                    stats.get("total_accounts", 0),
                    stats.get("total_posts_found", 0),
                    stats.get("total_posts_inserted", 0),
                    stats.get("total_posts_updated", 0),
                    stats.get("total_success", 0),
                    stats.get("total_partial", 0),
                    stats.get("total_failed", 0),
                    job_id,
                ))
    except Exception as exc:
        _log(f"Failed to complete job: {exc}", "WARN")


def fail_job(job_id: str, error_message: str):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE scrape_jobs
                SET status = 'FAILED', finished_at = NOW(), error_message = %s
                WHERE job_id = %s
            """, (error_message[:500], job_id))
    except Exception as exc:
        _log(f"Failed to mark job as failed: {exc}", "ERROR")


def log_job(job_id: str, level: str, stage: str, message: str):
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO job_logs (job_id, level, stage, message, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (job_id, level.upper()[:20], stage.upper()[:80], str(message)[:500]))
    except Exception:
        pass


def dict_to_account_row(account: dict) -> AccountRow:
    return AccountRow(
        no=account.get("id", 0),
        nama_kanwil=account.get("nama_unit", account.get("nama_kanwil", "")),
        url_akun=account.get("profile_url", account.get("url_akun", "")),
        manual_judul="",
        manual_link="",
        manual_reach="",
        agenda_no="",
        agenda_topic="",
    )


def selected_job_accounts(job_id: str) -> list[dict]:
    raw = get_setting(f"job_accounts_{job_id}", None)
    if not raw:
        return []
    try:
        usernames = json.loads(raw)
    except Exception as exc:
        _log(f"Failed to parse job account setting: {exc}", "WARN")
        return []
    return [account for username in usernames if (account := get_account_by_username(username))]


def accounts_for_job(job_id: str, default_limit: int, skip_hours: int) -> list[dict]:
    selected = selected_job_accounts(job_id)
    if selected:
        _log(f"Processing {len(selected)} explicitly selected accounts")
        return selected
    accounts = get_eligible_accounts_for_rolling_sync(limit=default_limit, skip_hours=skip_hours)
    _log(f"Processing {len(accounts)} eligible accounts")
    return accounts


def staging_status(row) -> str:
    status = getattr(row, "status_scraping", "") or ""
    if status == "FULL_SUCCESS":
        return "VALID"
    if status in FAILED_STATUSES:
        return "FAILED"
    if status in PARTIAL_STATUSES:
        return "INVALID"
    return "INVALID"


def build_staging_row(row, account: dict, job_id: str) -> dict:
    return {
        "job_id": job_id,
        "account_id": account.get("id"),
        "username": account.get("username", "") or getattr(row, "nama_kanwil", ""),
        "unit": account.get("nama_unit", account.get("nama_kanwil", "")) or getattr(row, "nama_kanwil", ""),
        "zona_waktu": account.get("zona_waktu", ""),
        "shortcode": getattr(row, "shortcode", "") or "",
        "post_url": getattr(row, "post_url", "") or "",
        "posted_at": getattr(row, "tanggal_postingan", None),
        "media_type": getattr(row, "media_type", "UNKNOWN") or "UNKNOWN",
        "caption": getattr(row, "caption", "") or "",
        "like_count": getattr(row, "like_count", None),
        "comment_count": getattr(row, "comment_count", None),
        "view_count": getattr(row, "view_count", None),
        "play_count": getattr(row, "play_count", None),
        "share_count": None,
        "save_count": None,
        "status_staging": staging_status(row),
        "catatan": getattr(row, "catatan", "") or "",
        "scraped_at": dt.now().isoformat(),
    }


def account_lookup(accounts: list[dict]) -> dict:
    return {
        (account.get("profile_url") or account.get("url_akun") or ""): account
        for account in accounts
        if account.get("profile_url") or account.get("url_akun")
    }


def save_scraping_results(job_id: str, accounts: list[dict], rows: list, mode: str = "hot") -> dict:
    stats = {
        "total_accounts": len(accounts),
        "total_posts_found": 0,
        "total_posts_inserted": 0,
        "total_posts_updated": 0,
        "total_success": 0,
        "total_partial": 0,
        "total_failed": 0,
        "staging_written": False,
        "staging_row_count": 0,
    }
    by_url = account_lookup(accounts)
    new_posts = []
    staging_rows = []

    for row in rows:
        post_url = getattr(row, "post_url", None)
        if not post_url:
            continue
        account = by_url.get(getattr(row, "url_akun", "") or "", {})
        staging_rows.append(build_staging_row(row, account, job_id))

    if staging_rows:
        ok, message, count = write_staging_jsonl(job_id, staging_rows, mode=mode)
        stats["staging_written"] = ok
        stats["staging_row_count"] = count
        if not ok:
            _log(f"Staging JSONL write failed for {job_id}: {message}", "WARN")

    for row in rows:
        if not getattr(row, "post_url", None):
            stats["total_failed"] += 1
            continue

        account = by_url.get(getattr(row, "url_akun", "") or "", {})
        username = account.get("username", "") or getattr(row, "nama_kanwil", "")
        unit = account.get("nama_unit", account.get("nama_kanwil", "")) or getattr(row, "nama_kanwil", "")
        media_type_normalized, _ = normalize_media_type(
            post_url=getattr(row, "post_url", ""),
            page_data=getattr(row, "_page_data", None),
            existing_media_type=getattr(row, "media_type", None),
        )
        success, is_new, post_id = upsert_post(
            username=username,
            nama_unit=unit,
            shortcode=getattr(row, "shortcode", "") or "",
            post_url=getattr(row, "post_url", ""),
            caption=getattr(row, "caption", "") or "",
            timestamp=getattr(row, "tanggal_postingan", None),
            media_type=getattr(row, "media_type", "UNKNOWN") or "UNKNOWN",
            media_type_normalized=media_type_normalized,
            like_count=getattr(row, "like_count", None),
            comments_count=getattr(row, "comment_count", None),
            total_engagement=getattr(row, "total_engagement", None),
            status_scraping=getattr(row, "status_scraping", "UNKNOWN") or "UNKNOWN",
            status_periode=getattr(row, "status_periode", "") or "",
            source_type="SCRAPED",
            null_reason=getattr(row, "catatan", "") or "",
            account_id=account.get("id"),
            view_count=getattr(row, "view_count", None),
            play_count=getattr(row, "play_count", None),
        )
        update_stats(stats, row, success, is_new)
        if success and is_new:
            new_posts.append(post_payload(row, post_id, username, unit))

    send_new_post_notifications(new_posts)
    return stats


def update_stats(stats: dict, row, success: bool, is_new: bool):
    stats["total_posts_found"] += 1
    if not success:
        stats["total_failed"] += 1
        return
    stats["total_posts_inserted" if is_new else "total_posts_updated"] += 1
    status = getattr(row, "status_scraping", "") or ""
    if status == "FULL_SUCCESS":
        stats["total_success"] += 1
    elif "PARTIAL" in status or "NULL" in status:
        stats["total_partial"] += 1


def post_payload(row, post_id: int, username: str, unit: str) -> dict:
    return {
        "id": post_id,
        "username": username,
        "nama_unit": unit,
        "shortcode": getattr(row, "shortcode", ""),
        "post_url": getattr(row, "post_url", ""),
        "caption": getattr(row, "caption", ""),
        "timestamp": getattr(row, "tanggal_postingan", None),
        "media_type": getattr(row, "media_type", "UNKNOWN"),
        "like_count": getattr(row, "like_count", None),
        "comment_count": getattr(row, "comment_count", None),
    }


def send_new_post_notifications(posts: list[dict]):
    if not posts or not get_telegram_enabled():
        return
    for post in posts:
        try:
            notify_new_post(
                username=post["username"],
                nama_unit=post["nama_unit"],
                shortcode=post["shortcode"],
                post_url=post["post_url"],
                caption=post["caption"],
                timestamp=post["timestamp"],
                media_type=post["media_type"],
                like_count=post["like_count"],
                comment_count=post["comment_count"],
                post_id=post["id"],
            )
        except Exception as exc:
            _log(f"Notification failed: {exc}", "WARN")


def job_status(stats: dict) -> str:
    if stats["total_success"] > 0:
        return "SUCCESS"
    if stats["total_partial"] > 0:
        return "PARTIAL_SUCCESS"
    return "FAILED"


def get_int_setting(key: str, default: int, minimum: int = 0, maximum: int = 1000) -> int:
    try:
        value = int(get_setting(key, str(default)))
        return max(minimum, min(maximum, value))
    except Exception:
        return default


def job_mode(job_id: str, default: str = "hot") -> str:
    mode = (get_setting(f"job_mode_{job_id}", default) or default).lower()
    return mode if mode in SCHEDULER_MODES else default


def mode_options(mode: str) -> dict:
    if mode == "cold":
        return {"days": 120, "max_posts": 120, "scrolls": 30, "skip_hours": 0}
    if mode == "warm":
        return {"days": 14, "max_posts": 40, "scrolls": 12, "skip_hours": 0}
    return {"days": 3, "max_posts": 12, "scrolls": 4, "skip_hours": 6}


def queued_or_running_exists() -> bool:
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT id FROM scrape_jobs WHERE status IN ('QUEUED','RUNNING') LIMIT 1")
        return cursor.fetchone() is not None


def create_scheduled_job(accounts: list[dict], mode: str) -> str:
    job_id = f"scheduler_{dt.now().strftime('%Y%m%d_%H%M%S')}"
    usernames = [account["username"] for account in accounts if account.get("username")]
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO scrape_jobs (job_id, job_type, trigger_type, status, requested_by)
            VALUES (%s, 'LATEST_SYNC', 'SCHEDULED', 'QUEUED', 'scheduler')
        """, (job_id,))
        cursor.execute("""
            INSERT INTO settings (setting_key, setting_value, description)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE setting_value = %s
        """, (
            f"job_accounts_{job_id}",
            json.dumps(usernames),
            f"Selected accounts for scheduled job {job_id}",
            json.dumps(usernames),
        ))
        cursor.execute("""
            INSERT INTO settings (setting_key, setting_value, description)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE setting_value = %s
        """, (f"job_mode_{job_id}", mode, f"Staging mode for job {job_id}", mode))
    return job_id


def parse_time_windows(raw: str) -> list[tuple[str, str]]:
    windows = []
    for item in (raw or "").split(","):
        text = item.strip()
        if not text:
            continue
        if "-" in text:
            start, end = [part.strip() for part in text.split("-", 1)]
        else:
            start, end = text, text
        if re.match(r"^\d{1,2}:\d{2}$", start) and re.match(r"^\d{1,2}:\d{2}$", end):
            windows.append((start.zfill(5), end.zfill(5)))
    return windows


def scheduler_due() -> tuple[bool, str]:
    if str(get_setting("scheduler_enabled", "false")).lower() != "true":
        return False, "disabled"

    mode = (get_setting("scheduler_mode", "daily") or "daily").lower()
    now = dt.now()

    if mode == "interval":
        minutes = get_int_setting("latest_sync_interval_minutes", 60, 15, 1440)
        last = get_setting("scheduler_last_enqueued_at", "")
        if not last:
            return True, f"interval:{minutes}"
        try:
            last_dt = dt.fromisoformat(last)
        except Exception:
            return True, f"interval:{minutes}"
        return (now - last_dt).total_seconds() >= minutes * 60, f"interval:{minutes}"

    current = now.strftime("%H:%M")
    for start, end in parse_time_windows(get_setting("scheduler_times", "22:00-23:00")):
        in_window = start <= current <= end if start <= end else current >= start or current <= end
        if not in_window:
            continue
        key = f"{now.date()}:{start}-{end}"
        if get_setting("scheduler_last_window_key", "") == key:
            return False, "window_already_enqueued"
        return True, key
    return False, "outside_window"


def enqueue_due_scheduler_job() -> Optional[str]:
    if queued_or_running_exists():
        return None

    due, marker = scheduler_due()
    if not due:
        return None

    limit = get_int_setting("scheduler_account_limit", 0, 0, MAX_DEFAULT_ACCOUNTS)
    if not limit:
        limit = get_int_setting("latest_max_posts_per_account", 15, 1, MAX_DEFAULT_ACCOUNTS)
    mode = (get_setting("scheduler_sync_mode", "hot") or "hot").lower()
    mode = mode if mode in SCHEDULER_MODES else "hot"
    opts = mode_options(mode)
    accounts = get_eligible_accounts_for_rolling_sync(limit=limit, skip_hours=opts["skip_hours"])
    if not accounts:
        set_setting("scheduler_last_check_status", "no_eligible_accounts")
        return None

    job_id = create_scheduled_job(accounts, mode)
    now = dt.now().isoformat(timespec="seconds")
    set_setting("scheduler_last_enqueued_at", now)
    set_setting("scheduler_last_job_id", job_id)
    if ":" in marker and not marker.startswith("interval"):
        set_setting("scheduler_last_window_key", marker)
    set_setting("scheduler_last_check_status", f"queued:{job_id}")
    _log(f"[SCHEDULER] Queued {job_id}: {len(accounts)} accounts, mode={mode}")
    return job_id


def rate_limit_active() -> bool:
    until_str = get_setting("global_rate_limited_until", "")
    if not until_str:
        return False
    try:
        until_dt = dt.strptime(until_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return False
    if dt.now() >= until_dt:
        return False
    remaining = int((until_dt - dt.now()).total_seconds())
    _log(f"Global rate limit active. Waiting {remaining}s...")
    time.sleep(min(remaining, 60))
    return True


def run_latest_sync(job_id: str):
    mode = job_mode(job_id)
    opts = mode_options(mode)
    log_job(job_id, "INFO", "SCRAPE", f"Starting latest sync ({mode})")
    accounts = accounts_for_job(job_id, default_limit=15, skip_hours=opts["skip_hours"])
    if not accounts:
        complete_job(job_id, "PARTIAL_SUCCESS", {"total_accounts": 0, "total_posts_found": 0})
        log_job(job_id, "WARN", "SCRAPE", "No eligible accounts")
        return

    today = date.today()
    rows = run_scraping(
        accounts=[dict_to_account_row(account) for account in accounts],
        period_start=dt.combine(today - timedelta(days=opts["days"]), dt.min.time()),
        period_end=dt.combine(today, dt.max.time()),
        max_posts=opts["max_posts"],
        scrolls=opts["scrolls"],
        with_detail=True,
        show_browser=False,
    )
    stats = save_scraping_results(job_id, accounts, rows, mode=mode)
    status = job_status(stats)
    complete_job(job_id, status, stats)
    log_job(job_id, "INFO", "COMPLETE", f"Job complete: {status}")
    _log_job_result("LATEST_SYNC", status, stats)


def run_period_sync(job_id: str, job: dict):
    log_job(job_id, "INFO", "SCRAPE", "Starting period sync")
    period_start = job.get("period_start")
    period_end = job.get("period_end")
    if not period_start or not period_end:
        fail_job(job_id, "Missing period_start or period_end")
        return

    accounts = selected_job_accounts(job_id) or get_eligible_accounts_for_rolling_sync(limit=34, skip_hours=0)
    if not accounts:
        complete_job(job_id, "PARTIAL_SUCCESS", {"total_accounts": 0})
        return

    rows = run_scraping(
        accounts=[dict_to_account_row(account) for account in accounts],
        period_start=dt.combine(period_start, dt.min.time()),
        period_end=dt.combine(period_end, dt.max.time()),
        max_posts=120,
        scrolls=30,
        with_detail=True,
        show_browser=False,
    )
    stats = save_scraping_results(job_id, accounts, rows, mode=job_mode(job_id, "cold"))
    status = job_status(stats)
    complete_job(job_id, status, stats)
    log_job(job_id, "INFO", "COMPLETE", f"Period sync complete: {status}")
    _log_job_result("PERIOD_SYNC", status, stats)


def _log_job_result(job_type: str, status: str, stats: dict):
    _log(f"{job_type} complete: {status}")
    _log(f"  Accounts: {stats['total_accounts']}")
    _log(f"  Posts found: {stats['total_posts_found']}")
    _log(f"  Inserted: {stats['total_posts_inserted']}")
    _log(f"  Failed: {stats['total_failed']}")


def process_job(job: dict) -> bool:
    job_id = job["job_id"]
    job_type = job["job_type"]
    _log(f"Processing job: {job_id} ({job_type})")
    if not claim_job(job_id):
        _log("Failed to claim job", "WARN")
        return False

    heartbeat = Heartbeat(job_id)
    heartbeat.start()
    log_job(job_id, "INFO", "WORKER", f"Job started by worker PID {os.getpid()}")
    try:
        if job_type == "LATEST_SYNC":
            run_latest_sync(job_id)
        elif job_type == "PERIOD_SYNC":
            run_period_sync(job_id, job)
        else:
            fail_job(job_id, f"Unknown job type: {job_type}")
    except Exception as exc:
        _log(f"Job failed: {exc}", "ERROR")
        fail_job(job_id, str(exc)[:500])
    finally:
        heartbeat.stop()
    return True


class Worker:
    def __init__(self):
        self._running = False

    def start(self):
        self._running = True
        _log("MAYZ SCRAPER WORKER - Production Loop")
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        while self._running:
            try:
                self._process_next_job()
            except Exception as exc:
                _log(f"Worker error: {exc}", "ERROR")
                time.sleep(10)
        _log("Worker stopped.")

    def _handle_shutdown(self, *_):
        _log("Shutdown signal received...")
        self._running = False
        stop_idle_heartbeat()

    def _process_next_job(self):
        if rate_limit_active():
            return
        enqueue_due_scheduler_job()
        job = get_next_job()
        if not job:
            _log("No queued job. Worker idle.")
            start_idle_heartbeat()
            time.sleep(SCHEDULER_IDLE_SECONDS)
            return
        stop_idle_heartbeat()
        process_job(job)


def run_job_once():
    _log("MAYZ SCRAPER WORKER - Single Cycle Mode")
    if rate_limit_active():
        return
    job = get_next_job()
    if not job:
        _log("No queued job. Exiting.")
        return
    process_job(job)
    _log("Worker exiting (--once mode).")


def main():
    parser = argparse.ArgumentParser(description="Mayz Scraper Worker")
    parser.add_argument("--once", action="store_true", help="Run one job and exit")
    args = parser.parse_args()

    success, message = test_connection()
    if not success:
        _log(f"Database connection failed: {message}", "ERROR")
        sys.exit(1)

    _log(f"Database connected: {message}")
    run_job_once() if args.once else Worker().start()


if __name__ == "__main__":
    main()
