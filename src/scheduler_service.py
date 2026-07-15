"""
Scheduler Service - Windows Task Scheduler integration.
Syncs database schedule to Windows Task Scheduler.
Source of truth: Database/Settings.
"""

import os
import sys
import subprocess
import re
from datetime import datetime
from typing import Tuple, List, Dict, Optional
from src.database import get_setting, set_setting


TASK_PREFIX = "Mayz_Worker_Sync"
TASK_NAME_PATTERN = re.compile(r"^Mayz_Worker_Sync_\d{4}$")

# Default values
DEFAULT_TIMEZONE = "Asia/Jakarta"
DEFAULT_TIME = "22:00-23:00"  # Format: "HH:mm-HH:mm" pairs


def get_project_root() -> str:
    """Get project root directory dynamically."""
    # Try to find project root from current file location
    current_file = os.path.abspath(__file__)
    # src/scheduler_service.py -> project root
    project_root = os.path.dirname(os.path.dirname(current_file))
    return project_root


def get_python_executable() -> str:
    """Get Python executable path for virtualenv."""
    project_root = get_project_root()
    venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")

    if os.path.exists(venv_python):
        return venv_python

    # Fallback to current Python
    return sys.executable


def get_worker_script_path() -> str:
    """Get worker script path."""
    return os.path.join(get_project_root(), "worker", "main.py")


def get_worker_command() -> str:
    """Build worker command for Windows Task Scheduler."""
    python_path = get_python_executable()
    worker_script = get_worker_script_path()

    # Return the full path to python and script
    return python_path, worker_script


def get_worker_batch_command() -> str:
    """
    Build command using a batch file to handle paths with spaces.
    Returns the batch file path.
    """
    project_root = get_project_root()
    batch_path = os.path.join(project_root, "mayz_sync.bat")
    python_path = get_python_executable()
    worker_script = get_worker_script_path()

    # Create batch file content
    batch_content = f'@echo off\ncd /d "{project_root}"\n"{python_path}" "{worker_script}" --once\n'

    with open(batch_path, 'w') as f:
        f.write(batch_content)

    return batch_path


def get_worker_command_for_display() -> str:
    """Get worker command for display purposes."""
    python_path = get_python_executable()
    worker_script = get_worker_script_path()
    project_root = get_project_root()

    # For display, show the full command
    cmd = f'cd /d "{project_root}" && "{python_path}" "{worker_script}" --once'
    return cmd


def get_scheduler_enabled() -> bool:
    """Check if scheduler is enabled."""
    val = get_setting("scheduler_enabled", "true")
    return val.lower() == "true"


def get_scheduler_times() -> List[str]:
    """Get list of scheduled times from database.
    Returns list of "HH:mm-HH:mm" pairs (e.g., ["11:00-12:00", "20:00-23:00"]).
    """
    times_str = get_setting("scheduler_times", DEFAULT_TIME)
    times = [t.strip() for t in times_str.split(",") if t.strip()]
    return times


def get_scheduler_start_times() -> List[str]:
    """Get list of start times from database for task scheduler.
    Returns list of "HH:mm" start times (e.g., ["11:00", "20:00"]).
    """
    pairs = get_scheduler_times()
    start_times = []
    for pair in pairs:
        parts = pair.split("-")
        if len(parts) >= 1:
            start_times.append(parts[0].strip())
    return start_times


def get_scheduler_timezone() -> str:
    """Get scheduler timezone."""
    return get_setting("scheduler_timezone", DEFAULT_TIMEZONE)


def save_scheduler_settings(
    enabled: bool,
    times: List[str],
    timezone: str = DEFAULT_TIMEZONE
) -> bool:
    """Save scheduler settings to database."""
    try:
        times_str = ", ".join(sorted(set(times)))  # Dedupe and sort
        set_setting("scheduler_enabled", "true" if enabled else "false")
        set_setting("scheduler_times", times_str)
        set_setting("scheduler_timezone", timezone)
        set_setting("scheduler_updated_at", datetime.now().isoformat())
        # Set default mode to DIRECT (not queue)
        set_setting("scheduler_mode", "direct")
        return True
    except Exception:
        return False


def update_scheduler_sync_status(status: str, error: str = None) -> None:
    """Update last sync status in database."""
    set_setting("scheduler_last_sync_status", status)
    set_setting("scheduler_last_sync_error", error or "")


def validate_time_format(time_str: str) -> bool:
    """Validate HH:MM format."""
    if not time_str:
        return False

    # Must match HH:MM
    match = re.match(r"^(\d{1,2}):(\d{1,2})$", time_str.strip())
    if not match:
        return False

    hour = int(match.group(1))
    minute = int(match.group(2))

    return 0 <= hour <= 23 and 0 <= minute <= 59


def validate_times_input(times_input: str) -> Tuple[bool, str, List[str]]:
    """
    Validate and parse times input.
    Returns: (is_valid, error_message, cleaned_times_list)
    """
    if not times_input or not times_input.strip():
        return False, "Input waktu tidak boleh kosong.", []

    # Split by comma
    times = [t.strip() for t in times_input.split(",") if t.strip()]

    if not times:
        return False, "Minimal harus ada 1 jadwal waktu.", []

    invalid_times = []
    valid_times = []

    for t in times:
        if not validate_time_format(t):
            invalid_times.append(t)
        else:
            # Normalize format (pad single digit)
            parts = t.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            valid_times.append(f"{hour:02d}:{minute:02d}")

    if invalid_times:
        return False, f"Format waktu tidak valid: {', '.join(invalid_times)}. Gunakan format HH:MM (contoh: 09:00, 22:00).", []

    # Dedupe and sort
    valid_times = sorted(set(valid_times))

    return True, "", valid_times


def task_exists(task_name: str) -> bool:
    """Check if a task exists in Windows Task Scheduler."""
    try:
        cmd = f'schtasks /query /tn "{task_name}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def delete_task(task_name: str) -> Tuple[bool, str]:
    """Delete a task from Windows Task Scheduler."""
    try:
        cmd = f'schtasks /delete /tn "{task_name}" /f'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            return True, f"Task '{task_name}' berhasil dihapus."
        else:
            error = result.stderr or result.stdout
            return False, f"Gagal hapus task '{task_name}': {error}"

    except Exception as e:
        return False, f"Error delete task: {str(e)}"


def disable_task(task_name: str) -> Tuple[bool, str]:
    """Disable a task in Windows Task Scheduler."""
    try:
        cmd = f'schtasks /change /tn "{task_name}" /disable'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            return True, f"Task '{task_name}' berhasil dinonaktifkan."
        else:
            error = result.stderr or result.stdout
            return False, f"Gagal nonaktifkan task '{task_name}': {error}"

    except Exception as e:
        return False, f"Error disable task: {str(e)}"


def create_task(
    task_name: str,
    time_hhmm: str,
    command: str = None
) -> Tuple[bool, str]:
    """
    Create a one-time daily task in Windows Task Scheduler.
    Time format: HH:MM

    Uses cmd.exe /c to run the .bat file properly.
    """
    try:
        batch_path = get_worker_batch_command()
        cmd = f'schtasks /create /tn "{task_name}" /sc DAILY /st {time_hhmm} /tr \"{batch_path}\" /f'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return True, f"Task '{task_name}' berhasil dibuat untuk jam {time_hhmm}."
        else:
            error = result.stderr or result.stdout
            if "Access is denied" in error or "requires elevation" in error.lower():
                return False, f"PERMISSION_DENIED: Task Scheduler butuh akses Administrator."
            elif "already exists" in error.lower():
                return True, f"Task '{task_name}' sudah ada."
            else:
                return False, f"Gagal buat task '{task_name}': {error}"

    except Exception as e:
        return False, f"Error create task: {str(e)}"


def get_task_info(task_name: str) -> Optional[Dict]:
    """Get task information from Windows Task Scheduler."""
    try:
        cmd = f'schtasks /query /tn "{task_name}" /fo LIST /v'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')

        if result.returncode != 0:
            return None

        info = {}
        for line in result.stdout.split("\n"):
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip()] = value.strip()

        # Parse Last Result code
        last_result = info.get("Last Result", "")
        if last_result:
            try:
                info["_last_result_code"] = int(last_result)
                info["_last_result_interpreted"] = interpret_result_code(last_result)
            except ValueError:
                info["_last_result_code"] = None
                info["_last_result_interpreted"] = f"Unknown: {last_result}"

        return info

    except Exception:
        return None

def interpret_result_code(result_code: str) -> str:
    """Interpret Windows Task Scheduler Last Result code."""
    try:
        code = int(result_code)
    except ValueError:
        return f"Invalid: {result_code}"

    if code == 0:
        return "Berhasil"
    elif code == -2147024894 or code == 0x80070002:
        return "FILE_NOT_FOUND: File/path tidak ditemukan"
    elif code == -2147943785 or code == 0x8007007E:
        return "MODULE_NOT_FOUND: Module tidak ditemukan"
    elif code == 267009:
        return "Task disabled"
    elif code == 267011:
        return "Task not started"
    elif code == 1:
        return "Incorrect function called"
    else:
        return f"Gagal (code: {code})"


def get_scheduler_mode() -> str:
    """Get scheduler mode: 'direct' or 'queue'."""
    return get_setting("scheduler_mode", "direct")


def set_scheduler_mode(mode: str) -> bool:
    """Set scheduler mode."""
    if mode not in ["direct", "queue"]:
        return False
    try:
        set_setting("scheduler_mode", mode)
        return True
    except Exception:
        return False


def get_all_mayz_tasks() -> List[str]:
    """Get all Mayz tasks from Windows Task Scheduler."""
    tasks = []

    try:
        # Query all tasks
        cmd = 'schtasks /query /fo LIST'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')

        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                line = line.strip()
                if "TaskName:" in line:
                    task_name = line.replace("TaskName:", "").strip()
                    if TASK_NAME_PATTERN.match(task_name.replace("\\", "")):
                        tasks.append(task_name.replace("\\", ""))

    except Exception:
        pass

    return tasks


def sync_scheduler_to_windows() -> Tuple[bool, str, List[Dict]]:
    """
    Sync database scheduler settings to Windows Task Scheduler.

    Returns: (overall_success, summary_message, task_results)
    """
    results = []
    errors = []

    # Get settings from database
    enabled = get_scheduler_enabled()
    time_pairs = get_scheduler_times()  # Format: "HH:mm-HH:mm"
    start_times = get_scheduler_start_times()  # Format: "HH:mm" for task creation

    if not enabled:
        # If disabled, we might want to disable all tasks
        # But for safety, we don't auto-delete - just log
        return True, "Scheduler dinonaktifkan. Task OS tidak dihapus otomatis.", []

    # Get all existing Mayz tasks
    existing_tasks = get_all_mayz_tasks()

    # Expected tasks based on database start times
    expected_tasks = [f"{TASK_PREFIX}_{t.replace(':', '')}" for t in start_times]

    # Tasks to delete (exist but not in expected)
    tasks_to_delete = [t for t in existing_tasks if t not in expected_tasks]

    # Delete old tasks
    for task_name in tasks_to_delete:
        success, msg = delete_task(task_name)
        results.append({
            "task": task_name,
            "action": "DELETE",
            "success": success,
            "message": msg
        })
        if not success:
            errors.append(msg)

    # Create/update tasks for each time
    command = get_worker_command()

    for i, start_hhmm in enumerate(start_times):
        task_name = f"{TASK_PREFIX}_{start_hhmm.replace(':', '')}"
        pair = time_pairs[i] if i < len(time_pairs) else start_hhmm

        if task_exists(task_name):
            # Task exists - verify it has correct schedule
            info = get_task_info(task_name)
            if info:
                current_time = info.get("Start Time", "")
                if start_hhmm in current_time or current_time == start_hhmm:
                    results.append({
                        "task": task_name,
                        "action": "VERIFY",
                        "success": True,
                        "message": f"Task '{task_name}' sudah ada dengan jadwal yang benar ({pair})."
                    })
                else:
                    # Time mismatch - recreate
                    delete_task(task_name)
                    success, msg = create_task(task_name, start_hhmm, command)
                    results.append({
                        "task": task_name,
                        "action": "UPDATE",
                        "success": success,
                        "message": msg
                    })
                    if not success:
                        errors.append(msg)
        else:
            # Create new task
            success, msg = create_task(task_name, start_hhmm, command)
            results.append({
                "task": task_name,
                "action": "CREATE",
                "success": success,
                "message": msg
            })
            if not success:
                errors.append(msg)

    # Update sync status in database
    if errors:
        update_scheduler_sync_status("FAILED", "; ".join(errors[:3]))  # Limit error length
    else:
        update_scheduler_sync_status("SUCCESS")

    overall_success = len(errors) == 0
    summary = f"Disinkronkan {len(start_times)} jadwal. {'Semua task berhasil.' if overall_success else f'{len(errors)} task gagal.'}"

    return overall_success, summary, results


def check_sync_status() -> Dict:
    """
    Check if database schedule matches Windows Task Scheduler.

    Returns status dict with detailed information:
    - database_times: list of time pairs in database
    - os_tasks: list of task names in OS
    - synced: bool
    - message: str
    - details: list of issues
    - last_result: interpreted result code
    - last_result_code: raw code
    - scheduler_mode: 'direct' or 'queue'
    """
    db_enabled = get_scheduler_enabled()
    db_time_pairs = get_scheduler_times()  # Format: "HH:mm-HH:mm"
    db_start_times = get_scheduler_start_times()  # Format: "HH:mm"
    os_tasks = get_all_mayz_tasks()
    scheduler_mode = get_scheduler_mode()

    expected_tasks = [f"{TASK_PREFIX}_{t.replace(':', '')}" for t in db_start_times]

    issues = []
    last_result = None
    last_result_code = None
    last_result_interpreted = None
    task_info = None

    if not db_enabled:
        status = "DISABLED"
        message = "Scheduler dinonaktifkan di database."
    elif not os_tasks and db_start_times:
        status = "NOT_SYNCED"
        message = f"Jadwal aktif di database ({len(db_time_pairs)} jadwal), tetapi task OS belum tersinkron."
        issues.append("Task OS tidak ditemukan")
    elif os_tasks:
        # Get info from first task (we only have one task per schedule)
        task_name = os_tasks[0] if os_tasks else None
        if task_name:
            task_info = get_task_info(task_name)
            last_result_code = task_info.get("_last_result_code") if task_info else None
            last_result_interpreted = task_info.get("_last_result_interpreted") if task_info else None

        # Check each expected task
        missing_tasks = [t for t in expected_tasks if t not in os_tasks]
        extra_tasks = [t for t in os_tasks if t not in expected_tasks]

        if missing_tasks:
            issues.append(f"Task missing: {', '.join(missing_tasks)}")
        if extra_tasks:
            issues.append(f"Task ekstra (sudah dihapus dari database): {', '.join(extra_tasks)}")

        # Check last result ONLY if there are missing/extra tasks (sync issue)
        # Note: Last Result 267011 (Task not started) is NORMAL for new tasks
        # Only flag as issue if tasks are missing/extra or last_result indicates real failure
        if missing_tasks or extra_tasks:
            # Sync issue - tasks don't match
            if issues:
                status = "NOT_SYNCED"
                message = "Task OS tidak sesuai dengan jadwal database."
        else:
            # Tasks match - sync is successful
            # Note: Last Result code 267011 (not started) or empty is normal for new tasks
            # Real failures are: 0x80070002 (file not found), 0x8007007E (module not found), etc.
            if last_result_code is not None and last_result_code != 0 and last_result_code != 267011:
                # Real execution failure, but sync itself is OK
                issues.append(f"Task Scheduler Last Result: {last_result_code} ({last_result_interpreted})")
                status = "SYNCED_WITH_ERRORS"
                message = f"Sinkron. {len(db_time_pairs)} jadwal aktif. (Eksekusi terakhir gagal)"
            else:
                status = "SYNCED"
                message = f"Sinkron. {len(db_time_pairs)} jadwal aktif."

    # Get last job from database
    last_job = None
    try:
        from src.db_repository import get_recent_jobs
        recent = get_recent_jobs(limit=1)
        if recent:
            last_job = recent[0]
    except Exception:
        pass

    return {
        "status": status,
        "message": message,
        "database_enabled": db_enabled,
        "database_times": db_time_pairs,
        "os_tasks": os_tasks,
        "expected_tasks": expected_tasks,
        "issues": issues,
        "last_sync_status": get_setting("scheduler_last_sync_status", ""),
        "last_sync_error": get_setting("scheduler_last_sync_error", ""),
        "last_updated": get_setting("scheduler_updated_at", ""),
        "scheduler_mode": scheduler_mode,
        "task_info": task_info,
        "last_result_code": last_result_code,
        "last_result_interpreted": last_result_interpreted,
        "last_job": last_job,
    }


def get_manual_command() -> str:
    """Get manual schtasks command for user to run manually if sync fails."""
    times = get_scheduler_times()
    command = get_worker_command()

    lines = [
        "# Windows Task Scheduler Manual Commands",
        "# Jalankan command berikut di Command Prompt (Admin) jika sinkronisasi otomatis gagal:",
        "",
    ]

    for time_hhmm in times:
        task_name = f"{TASK_PREFIX}_{time_hhmm.replace(':', '')}"
        lines.append(f'schtasks /create /tn "{task_name}" /sc DAILY /st {time_hhmm} /tr "{command}" /f')

    return "\n".join(lines)


if __name__ == "__main__":
    print("=== Scheduler Service Test ===")
    print(f"Project Root: {get_project_root()}")
    print(f"Python: {get_python_executable()}")
    print(f"Command: {get_worker_command()}")
    print()
    print(f"Scheduler Enabled: {get_scheduler_enabled()}")
    print(f"Scheduler Times: {get_scheduler_times()}")
    print()
    print("=== Sync Status ===")
    status = check_sync_status()
    for k, v in status.items():
        print(f"  {k}: {v}")