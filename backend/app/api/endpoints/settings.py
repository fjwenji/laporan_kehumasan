"""
Settings API Endpoints - Telegram and Scheduler Configuration
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from typing import Optional, List
from datetime import datetime, timedelta
import os
import re

from app.api.deps import get_current_admin_user
from app.database import get_db_cursor
from app.schemas.settings import (
    TelegramRecipient, TelegramRecipientCreate, TelegramRecipientUpdate,
    TelegramRecipientsResponse, TelegramSettingsResponse, TelegramSettingsUpdate,
    TelegramTestRequest, TelegramTestResponse, TelegramTokenRequest,
    SchedulerSettingsResponse, SchedulerSettingsUpdate,
    SchedulerStatusResponse, SchedulerSyncResponse,
    SuccessResponse, ErrorResponse
)

router = APIRouter(prefix="/api/admin/settings", tags=["Admin Settings"])


def is_docker_runtime() -> bool:
    return os.path.exists("/.dockerenv") or os.getenv("MAYZ_DOCKER_LOCAL", "").lower() == "true"


def set_scheduler_sync_status(cursor, status: str, error: str = ""):
    for key, value in {"scheduler_last_sync_status": status, "scheduler_last_sync_error": error}.items():
        cursor.execute("""
            INSERT INTO settings (setting_key, setting_value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE setting_value = %s, updated_at = NOW()
        """, (key, value, value))


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def mask_token(token: str) -> str:
    """Mask Telegram bot token for safe display."""
    if not token or len(token) < 10:
        return "***"
    parts = token.split(":")
    if len(parts) >= 2:
        return f"{parts[0]}:{parts[1][:2]}***{parts[1][-3:] if len(parts[1]) > 5 else ''}"
    return f"{token[:4]}***{token[-3:]}"


def validate_chat_id(chat_id: str) -> tuple[bool, str]:
    """Validate Telegram chat ID format."""
    if not chat_id:
        return False, "Chat ID tidak boleh kosong."
    chat_id = chat_id.strip()
    # Chat ID can be numeric or start with -100 (group) or @ (username)
    if chat_id.startswith("@"):
        return True, "Valid"
    if chat_id.startswith("-100"):
        return True, "Valid"
    if chat_id.lstrip("-").isdigit():
        return True, "Valid"
    return False, "Format Chat ID tidak valid. Gunakan numeric ID atau @username."


# ============================================================
# TELEGRAM ENDPOINTS
# ============================================================

@router.get("/telegram", response_model=TelegramSettingsResponse)
async def get_telegram_settings(
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Get Telegram settings and recipients.
    """
    with get_db_cursor(commit=False) as cursor:
        # Get settings
        cursor.execute("SELECT setting_key, setting_value FROM settings WHERE setting_key IN ('TELEGRAM_ENABLED', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_NOTIFY_NEW_POST')")
        settings = {row["setting_key"]: row["setting_value"] for row in cursor.fetchall()}

        # Get recipients
        cursor.execute("SELECT * FROM telegram_recipients ORDER BY name ASC")
        recipients = cursor.fetchall()

    enabled = str(settings.get("TELEGRAM_ENABLED", "false")).lower() == "true"
    bot_token = settings.get("TELEGRAM_BOT_TOKEN", "")
    notify_new_post = str(settings.get("TELEGRAM_NOTIFY_NEW_POST", "true")).lower() == "true"

    return TelegramSettingsResponse(
        enabled=enabled,
        bot_token_masked=mask_token(bot_token),
        notify_new_post=notify_new_post,
        recipient_count=len(recipients),
        recipients=[TelegramRecipient(**r) for r in recipients]
    )


@router.put("/telegram", response_model=SuccessResponse)
async def update_telegram_settings(
    request: TelegramSettingsUpdate,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Update Telegram settings (enabled, notify_new_post).
    Bot token should be set separately via /telegram/token endpoint.
    """
    try:
        with get_db_cursor() as cursor:
            if request.enabled is not None:
                cursor.execute("""
                    INSERT INTO settings (setting_key, setting_value)
                    VALUES ('TELEGRAM_ENABLED', %s)
                    ON DUPLICATE KEY UPDATE setting_value = %s, updated_at = NOW()
                """, (str(request.enabled).lower(), str(request.enabled).lower()))

            if request.notify_new_post is not None:
                cursor.execute("""
                    INSERT INTO settings (setting_key, setting_value)
                    VALUES ('TELEGRAM_NOTIFY_NEW_POST', %s)
                    ON DUPLICATE KEY UPDATE setting_value = %s, updated_at = NOW()
                """, (str(request.notify_new_post).lower(), str(request.notify_new_post).lower()))

        return SuccessResponse(success=True, message="Pengaturan Telegram berhasil diperbarui.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/telegram/token", response_model=SuccessResponse)
async def update_telegram_token(
    request: TelegramTokenRequest,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Update Telegram bot token.
    Token is stored securely in database settings.
    """
    bot_token = request.bot_token
    if not bot_token or len(bot_token) < 10:
        raise HTTPException(status_code=400, detail="Token tidak valid.")

    # Basic format validation
    if ":" not in bot_token:
        raise HTTPException(status_code=400, detail="Format token tidak valid. Seharusnya: 123456:ABCDEF...")

    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO settings (setting_key, setting_value)
                VALUES ('TELEGRAM_BOT_TOKEN', %s)
                ON DUPLICATE KEY UPDATE setting_value = %s, updated_at = NOW()
            """, (bot_token, bot_token))

        return SuccessResponse(success=True, message="Token Telegram berhasil diperbarui.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/telegram/recipients", response_model=TelegramRecipientsResponse)
async def get_telegram_recipients(
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Get Telegram notification targets.
    """
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT * FROM telegram_recipients ORDER BY name ASC")
        recipients = cursor.fetchall()

    return TelegramRecipientsResponse(
        recipients=[TelegramRecipient(**r) for r in recipients],
        total=len(recipients)
    )


@router.post("/telegram/recipients", response_model=TelegramRecipient)
async def create_telegram_recipient(
    request: TelegramRecipientCreate,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Create a Telegram notification target.
    """
    # Validate chat_id
    valid, msg = validate_chat_id(request.chat_id)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    try:
        with get_db_cursor() as cursor:
            # Check for duplicate chat_id
            cursor.execute("SELECT id FROM telegram_recipients WHERE chat_id = %s", (request.chat_id,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Chat ID sudah terdaftar.")

            cursor.execute("""
                INSERT INTO telegram_recipients (name, chat_id, is_active)
                VALUES (%s, %s, TRUE)
            """, (request.name, request.chat_id))
            recipient_id = cursor.lastrowid

        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT * FROM telegram_recipients WHERE id = %s", (recipient_id,))
            recipient = cursor.fetchone()

        return TelegramRecipient(**recipient)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/telegram/recipients/{recipient_id}", response_model=TelegramRecipient)
async def update_telegram_recipient(
    recipient_id: int,
    request: TelegramRecipientUpdate,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Update a Telegram notification target.
    """
    # Validate chat_id if provided
    if request.chat_id:
        valid, msg = validate_chat_id(request.chat_id)
        if not valid:
            raise HTTPException(status_code=400, detail=msg)

    try:
        with get_db_cursor() as cursor:
            # Check recipient exists
            cursor.execute("SELECT id FROM telegram_recipients WHERE id = %s", (recipient_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Penerima notifikasi tidak ditemukan.")

            # Check for duplicate chat_id if changing
            if request.chat_id:
                cursor.execute("SELECT id FROM telegram_recipients WHERE chat_id = %s AND id != %s", (request.chat_id, recipient_id))
                if cursor.fetchone():
                    raise HTTPException(status_code=400, detail="Chat ID sudah terdaftar.")

            # Build update query
            updates = []
            values = []
            if request.name is not None:
                updates.append("name = %s")
                values.append(request.name)
            if request.chat_id is not None:
                updates.append("chat_id = %s")
                values.append(request.chat_id)
            if request.is_active is not None:
                updates.append("is_active = %s")
                values.append(request.is_active)

            if updates:
                values.append(recipient_id)
                cursor.execute(f"""
                    UPDATE telegram_recipients
                    SET {', '.join(updates)}, updated_at = NOW()
                    WHERE id = %s
                """, values)

        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT * FROM telegram_recipients WHERE id = %s", (recipient_id,))
            recipient = cursor.fetchone()

        return TelegramRecipient(**recipient)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/telegram/recipients/{recipient_id}", response_model=SuccessResponse)
async def delete_telegram_recipient(
    recipient_id: int,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Delete a Telegram notification target.
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT id FROM telegram_recipients WHERE id = %s", (recipient_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Penerima notifikasi tidak ditemukan.")

            cursor.execute("DELETE FROM telegram_recipients WHERE id = %s", (recipient_id,))

        return SuccessResponse(success=True, message="Penerima notifikasi berhasil dihapus.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/telegram/recipients/{recipient_id}/toggle", response_model=TelegramRecipient)
async def toggle_telegram_recipient(
    recipient_id: int,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Toggle active status of a Telegram notification target.
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT id, is_active FROM telegram_recipients WHERE id = %s", (recipient_id,))
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Penerima notifikasi tidak ditemukan.")

            new_status = not result["is_active"]
            cursor.execute("UPDATE telegram_recipients SET is_active = %s, updated_at = NOW() WHERE id = %s",
                          (new_status, recipient_id))

        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT * FROM telegram_recipients WHERE id = %s", (recipient_id,))
            recipient = cursor.fetchone()

        return TelegramRecipient(**recipient)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/telegram/test", response_model=TelegramTestResponse)
async def test_telegram(
    request: TelegramTestRequest,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Send a test message to active Telegram targets.
    """
    import requests

    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT setting_key, setting_value
            FROM settings
            WHERE setting_key IN ('TELEGRAM_BOT_TOKEN', 'telegram_bot_token', 'bot_token')
        """)
        settings = {row["setting_key"]: row["setting_value"] for row in cursor.fetchall()}

        cursor.execute("SELECT chat_id FROM telegram_recipients WHERE is_active = TRUE")
        recipients = [row["chat_id"] for row in cursor.fetchall()]

    bot_token = settings.get("TELEGRAM_BOT_TOKEN") or settings.get("telegram_bot_token") or settings.get("bot_token") or ""
    if not bot_token:
        return TelegramTestResponse(
            success=False,
            message="Token bot belum dikonfigurasi.",
            details="Silakan update token bot terlebih dahulu."
        )

    if not recipients:
        return TelegramTestResponse(
            success=False,
            message="Belum ada Chat ID aktif.",
            details="Tambahkan minimal satu Chat ID penerima notifikasi terlebih dahulu."
        )

    message = request.message or "🔔 Test notification from Mayz Monitoring System\n\nWaktu: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    success_count = 0
    failed_count = 0
    errors = []

    for chat_id in recipients:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                },
                timeout=30
            )
            data = response.json()
            if response.status_code == 200 and data.get("ok"):
                success_count += 1
            else:
                failed_count += 1
                errors.append(f"{chat_id}: {data.get('description', 'Unknown error')}")
        except Exception as e:
            failed_count += 1
            errors.append(f"{chat_id}: {str(e)}")

    if success_count > 0:
        return TelegramTestResponse(
            success=True,
            message=f"Pesan berhasil dikirim ke {success_count} penerima.",
            details="\n".join(errors) if errors else None
        )
    else:
        return TelegramTestResponse(
            success=False,
            message="Gagal mengirim pesan Telegram.",
            details="\n".join(errors) if errors else None
        )


# ============================================================
# SCHEDULER ENDPOINTS
# ============================================================

@router.get("/scheduler", response_model=SchedulerSettingsResponse)
async def get_scheduler_settings(
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Get scheduler settings.
    """
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT setting_key, setting_value
            FROM settings
            WHERE setting_key LIKE 'scheduler_%' OR setting_key LIKE 'latest_%'
        """)
        settings = {row["setting_key"]: row["setting_value"] for row in cursor.fetchall()}

    is_enabled = str(settings.get("scheduler_enabled", "true")).lower() == "true"
    schedule_mode = settings.get("scheduler_mode", "interval")
    interval_minutes = int(settings.get("latest_sync_interval_minutes", "60"))
    daily_times_str = settings.get("scheduler_times", "22:00-23:00")
    account_limit = int(settings.get("latest_max_posts_per_account", "15"))
    cooldown_seconds = int(settings.get("delay_between_accounts", "5"))

    # Parse daily times format "HH:mm-HH:mm" pairs (e.g., "11:00-12:00, 20:00-23:00")
    # Split by comma first, then parse each time range
    daily_times = []
    if daily_times_str:
        time_pairs = [t.strip() for t in daily_times_str.split(",") if t.strip()]
        for pair in time_pairs:
            daily_times.append(pair)  # Store as "HH:mm-HH:mm" format

    return SchedulerSettingsResponse(
        is_enabled=is_enabled,
        schedule_mode=schedule_mode,
        interval_minutes=interval_minutes,
        daily_times=daily_times,
        account_scope="all",
        account_limit=account_limit,
        cooldown_seconds=cooldown_seconds,
        updated_at=datetime.now()
    )


@router.put("/scheduler", response_model=SuccessResponse)
async def update_scheduler_settings(
    request: SchedulerSettingsUpdate,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Update scheduler settings.
    """
    try:
        with get_db_cursor() as cursor:
            if request.is_enabled is not None:
                cursor.execute("""
                    INSERT INTO settings (setting_key, setting_value)
                    VALUES ('scheduler_enabled', %s)
                    ON DUPLICATE KEY UPDATE setting_value = %s, updated_at = NOW()
                """, (str(request.is_enabled).lower(), str(request.is_enabled).lower()))

            if request.schedule_mode is not None:
                cursor.execute("""
                    INSERT INTO settings (setting_key, setting_value)
                    VALUES ('scheduler_mode', %s)
                    ON DUPLICATE KEY UPDATE setting_value = %s, updated_at = NOW()
                """, (request.schedule_mode.value, request.schedule_mode.value))

            if request.interval_minutes is not None:
                cursor.execute("""
                    INSERT INTO settings (setting_key, setting_value)
                    VALUES ('latest_sync_interval_minutes', %s)
                    ON DUPLICATE KEY UPDATE setting_value = %s, updated_at = NOW()
                """, (str(request.interval_minutes), str(request.interval_minutes)))

            if request.daily_times is not None:
                cursor.execute("""
                    INSERT INTO settings (setting_key, setting_value)
                    VALUES ('scheduler_times', %s)
                    ON DUPLICATE KEY UPDATE setting_value = %s, updated_at = NOW()
                """, (request.daily_times, request.daily_times))

            if request.account_limit is not None:
                cursor.execute("""
                    INSERT INTO settings (setting_key, setting_value)
                    VALUES ('latest_max_posts_per_account', %s)
                    ON DUPLICATE KEY UPDATE setting_value = %s, updated_at = NOW()
                """, (str(request.account_limit), str(request.account_limit)))

            if request.cooldown_seconds is not None:
                cursor.execute("""
                    INSERT INTO settings (setting_key, setting_value)
                    VALUES ('delay_between_accounts', %s)
                    ON DUPLICATE KEY UPDATE setting_value = %s, updated_at = NOW()
                """, (str(request.cooldown_seconds), str(request.cooldown_seconds)))

        return SuccessResponse(success=True, message="Pengaturan scheduler berhasil diperbarui.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status(
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Get detailed scheduler status including worker heartbeat.
    """
    with get_db_cursor(commit=False) as cursor:
        # Get settings
        cursor.execute("""
            SELECT setting_key, setting_value
            FROM settings
            WHERE setting_key LIKE 'scheduler_%' OR setting_key LIKE 'latest_%'
        """)
        settings = {row["setting_key"]: row["setting_value"] for row in cursor.fetchall()}

        # Get running job
        cursor.execute("""
            SELECT * FROM scrape_jobs
            WHERE status = 'RUNNING'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        running_job = cursor.fetchone()

        # Get last completed job
        cursor.execute("""
            SELECT * FROM scrape_jobs
            WHERE status IN ('SUCCESS', 'FAILED', 'PARTIAL_SUCCESS')
            ORDER BY finished_at DESC
            LIMIT 1
        """)
        last_job = cursor.fetchone()

        # Get sync status
        cursor.execute("""
            SELECT setting_key, setting_value
            FROM settings
            WHERE setting_key IN ('scheduler_last_sync_status', 'scheduler_last_sync_error')
        """)
        sync_settings = {row["setting_key"]: row["setting_value"] for row in cursor.fetchall()}

    is_enabled = str(settings.get("scheduler_enabled", "true")).lower() == "true"
    schedule_mode = settings.get("scheduler_mode", "interval")
    interval_minutes = int(settings.get("latest_sync_interval_minutes", "60"))
    daily_times_str = settings.get("scheduler_times", "22:00-23:00")
    # Parse daily times format "HH:mm-HH:mm" pairs (e.g., "11:00-12:00, 20:00-23:00")
    daily_times = []
    if daily_times_str:
        daily_times = [t.strip() for t in daily_times_str.split(",") if t.strip()]

    # For next_run calculation, extract start times from pairs
    schedule_start_times = []
    for pair in daily_times:
        parts = pair.split("-")
        if len(parts) >= 2:
            schedule_start_times.append(parts[0].strip())

    # Determine worker status
    worker_status = "idle"
    worker_heartbeat = None
    current_job_id = None

    if running_job:
        worker_status = "running"
        current_job_id = running_job.get("job_id")
        heartbeat = running_job.get("worker_heartbeat_at")
        if heartbeat:
            if isinstance(heartbeat, str):
                try:
                    heartbeat = datetime.fromisoformat(heartbeat)
                except:
                    pass
            if heartbeat:
                elapsed = (datetime.now() - heartbeat).total_seconds()
                if elapsed > 120:  # 2 minutes
                    worker_status = "stuck"
                worker_heartbeat = heartbeat

    # Calculate next run
    next_run = None
    if is_enabled:
        if schedule_mode == "interval":
            next_run = datetime.now() + timedelta(minutes=interval_minutes)
        else:
            # Calculate next daily time using start times from pairs
            now = datetime.now()
            for time_str in schedule_start_times:
                parts = time_str.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if candidate > now:
                    next_run = candidate
                    break
            if not next_run:
                # Next day - use first schedule start time
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                if schedule_start_times:
                    parts = schedule_start_times[0].split(":")
                    hour = int(parts[0])
                    minute = int(parts[1]) if len(parts) > 1 else 0
                    next_run = tomorrow.replace(hour=hour, minute=minute)

    is_synced = False
    if is_docker_runtime():
        is_synced = is_enabled
    else:
        try:
            import sys
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            from src.scheduler_service import check_sync_status
            sync_status = check_sync_status()
            is_synced = sync_status.get("status") in ("SYNCED", "SYNCED_WITH_ERRORS")
        except Exception:
            import subprocess
            task_prefix = "Mayz_Worker_Sync"
            try:
                result = subprocess.run('schtasks', shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
                os_tasks = [line.strip().split()[0] for line in result.stdout.split('\n') if task_prefix in line and line.strip().split()]
                expected_tasks = [f"{task_prefix}_{t.replace(':', '')}" for t in schedule_start_times]
                is_synced = set(os_tasks) == set(expected_tasks) and len(os_tasks) > 0
            except Exception:
                is_synced = False

    last_run = last_job.get("finished_at") if last_job else None
    last_run_status = last_job.get("status") if last_job else None

    return SchedulerStatusResponse(
        status="SYNCED" if (is_enabled and is_synced) else ("NOT_SYNCED" if is_enabled else "DISABLED"),
        message=("Scheduler aktif via worker internal" if is_docker_runtime() and is_enabled else ("Scheduler aktif" if is_enabled else "Scheduler dinonaktifkan")),
        is_enabled=is_enabled,
        is_synced=is_synced,
        schedule_mode=schedule_mode,
        interval_minutes=interval_minutes,
        daily_times=daily_times,
        next_run=next_run,
        last_run=last_run,
        last_run_status=last_run_status,
        worker_status=worker_status,
        worker_last_heartbeat=worker_heartbeat,
        current_job_id=current_job_id
    )


@router.post("/scheduler/sync", response_model=SchedulerSyncResponse)
async def sync_scheduler(
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Sync scheduler settings to Windows Task Scheduler.
    """
    try:
        if is_docker_runtime():
            with get_db_cursor() as cursor:
                set_scheduler_sync_status(cursor, "INTERNAL", "")
            return SchedulerSyncResponse(
                success=True,
                message="Docker Local memakai scheduler internal worker. Windows Task Scheduler tidak diperlukan.",
                tasks_synced=0,
                errors=[]
            )

        import sys

        # Get project root: backend/app/api/endpoints/settings.py -> project root (4 levels up)
        current_file = os.path.abspath(__file__)
        # backend/app/api/endpoints/settings.py
        # -> backend/app/api/endpoints
        # -> backend/app/api
        # -> backend/app
        # -> backend
        # -> project root
        endpoints_dir = os.path.dirname(current_file)  # backend/app/api/endpoints
        api_dir = os.path.dirname(endpoints_dir)        # backend/app/api
        app_dir = os.path.dirname(api_dir)              # backend/app
        backend_dir = os.path.dirname(app_dir)          # backend
        project_root = os.path.dirname(backend_dir)     # project root

        # Add project root to path so we can import src.scheduler_service
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        from src.scheduler_service import sync_scheduler_to_windows

        success, message, results = sync_scheduler_to_windows()
        tasks_synced = len([r for r in results if r.get("action") in ("CREATE", "UPDATE")])

        return SchedulerSyncResponse(
            success=success,
            message=message,
            tasks_synced=tasks_synced,
            errors=[r.get("message", "") for r in results if not r.get("success", True)]
        )
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Scheduler service tidak tersedia: {str(e)}")
    except Exception as e:
        return SchedulerSyncResponse(
            success=False,
            message="Gagal sinkronisasi scheduler.",
            errors=[str(e)]
        )
