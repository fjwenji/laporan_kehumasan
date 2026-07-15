"""
Staging Data Preview API - Read-only endpoints for viewing staging JSONL files.
"""
import json
import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.database import get_db_cursor

router = APIRouter(prefix="/api/staging", tags=["Staging"])

# Staging directories - absolute paths for Docker container
# Container mounts host's data/staging to /app/data/staging
_STAGING_ROOT_HOST = os.environ.get("STAGING_ROOT_HOST", "/app/data/staging")
STAGING_ROOT = Path(_STAGING_ROOT_HOST)
STAGING_HOT = STAGING_ROOT / "hot"
STAGING_WARM = STAGING_ROOT / "warm"
STAGING_COLD = STAGING_ROOT / "cold"


def ensure_staging_dirs():
    """Ensure staging directories exist."""
    for d in [STAGING_ROOT, STAGING_HOT, STAGING_WARM, STAGING_COLD]:
        d.mkdir(parents=True, exist_ok=True)


def get_staging_file_path(job_id: str, mode: str = "hot") -> Path:
    """Get staging file path for a job."""
    ensure_staging_dirs()
    if mode == "warm":
        return STAGING_WARM / f"{job_id}.jsonl"
    elif mode == "cold":
        return STAGING_COLD / f"{job_id}.jsonl"
    else:
        return STAGING_HOT / f"{job_id}.jsonl"


def parse_jsonl_line(line: str) -> Optional[dict]:
    """Parse a single JSONL line, return None if invalid."""
    try:
        return json.loads(line.strip())
    except (json.JSONDecodeError, TypeError):
        return None


def read_jsonl_file(file_path: Path, skip: int = 0, limit: int = 100) -> tuple:
    """
    Read JSONL file with pagination.

    Returns: (rows, total_count, error_message)
    """
    if not file_path.exists():
        return [], 0, "File not found"

    rows = []
    total_count = 0
    errors = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                total_count += 1
                parsed = parse_jsonl_line(line)

                if parsed is None:
                    errors.append(f"Invalid JSON at line {total_count}")
                    continue

                # Apply pagination
                if skip > 0:
                    skip -= 1
                    continue

                rows.append(parsed)

                if limit > 0 and len(rows) >= limit:
                    break

        return rows, total_count, None

    except Exception as e:
        return [], 0, f"Error reading file: {str(e)}"


def read_jsonl_summary(file_path: Path) -> dict:
    """
    Read JSONL file and compute summary statistics.

    Returns: dict with summary counts
    """
    if not file_path.exists():
        return None

    stats = {
        "total_rows": 0,
        "valid_count": 0,
        "invalid_count": 0,
        "failed_count": 0,
        "by_username": {},
        "by_media_type": {},
        "by_status": {},
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parsed = parse_jsonl_line(line)
                if parsed is None:
                    continue

                stats["total_rows"] += 1

                # Count by status_staging
                status = parsed.get("status_staging", "UNKNOWN")
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

                if status == "VALID":
                    stats["valid_count"] += 1
                elif status == "INVALID":
                    stats["invalid_count"] += 1
                elif status == "FAILED":
                    stats["failed_count"] += 1

                # Count by username
                username = parsed.get("username", "unknown")
                if username not in stats["by_username"]:
                    stats["by_username"][username] = 0
                stats["by_username"][username] += 1

                # Count by media_type
                media_type = parsed.get("media_type", "UNKNOWN")
                if media_type not in stats["by_media_type"]:
                    stats["by_media_type"][media_type] = 0
                stats["by_media_type"][media_type] += 1

        return stats

    except Exception as e:
        return None


def list_staging_jobs() -> List[dict]:
    """
    List all available staging job files.

    Returns list of dict with job info
    """
    ensure_staging_dirs()

    jobs = []

    for mode, mode_dir in [("hot", STAGING_HOT), ("warm", STAGING_WARM), ("cold", STAGING_COLD)]:
        if not mode_dir.exists():
            continue

        for file_path in mode_dir.glob("*.jsonl"):
            try:
                stat = file_path.stat()
                job_id = file_path.stem  # filename without extension

                # Quick count without reading entire file
                line_count = 0
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            line_count += 1

                jobs.append({
                    "job_id": job_id,
                    "mode": mode,
                    "file_path": str(file_path.relative_to(STAGING_ROOT)),  # Relative path only
                    "file_size_bytes": stat.st_size,
                    "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "row_count": line_count,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except Exception as e:
                # Skip files that can't be read
                continue

    # Sort by modified_at descending
    jobs.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

    return jobs


@router.get("/jobs")
async def list_staging_jobs_endpoint(
    current_user: dict = Depends(get_current_user)
):
    """
    List all available staging job files.

    Accessible by all authenticated users (admin and user).
    """
    jobs = list_staging_jobs()

    return {
        "jobs": jobs,
        "total": len(jobs),
        "staging_root": str(Path("data/staging").as_posix()),  # Relative path
    }


@router.get("/jobs/{job_id}")
async def get_staging_job_rows(
    job_id: str,
    mode: str = Query("hot", description="Staging mode: hot, warm, or cold"),
    limit: int = Query(100, ge=1, le=500, description="Number of rows to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    username: Optional[str] = Query(None, description="Filter by username"),
    status: Optional[str] = Query(None, description="Filter by status_staging"),
    media_type: Optional[str] = Query(None, description="Filter by media_type"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get rows from a staging job JSONL file.

    Accessible by all authenticated users (admin and user).
    """
    file_path = get_staging_file_path(job_id, mode)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Staging file not found: {job_id}")

    # Read with pagination
    all_rows, total_count, error = read_jsonl_file(file_path, skip=0, limit=10000)

    if error:
        raise HTTPException(status_code=500, detail=error)

    # Apply filters
    filtered_rows = []
    for row in all_rows:
        if username and row.get("username", "").lower() != username.lower():
            continue
        if status and row.get("status_staging", "") != status:
            continue
        if media_type and row.get("media_type", "").lower() != media_type.lower():
            continue
        filtered_rows.append(row)

    # Apply pagination on filtered results
    paginated_rows = filtered_rows[offset:offset + limit]

    return {
        "job_id": job_id,
        "mode": mode,
        "rows": paginated_rows,
        "total": len(filtered_rows),
        "total_raw": total_count,
        "limit": limit,
        "offset": offset,
        "filters": {
            "username": username,
            "status": status,
            "media_type": media_type,
        }
    }


@router.get("/jobs/{job_id}/summary")
async def get_staging_job_summary(
    job_id: str,
    mode: str = Query("hot", description="Staging mode: hot, warm, or cold"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get summary statistics for a staging job.

    Accessible by all authenticated users (admin and user).
    """
    file_path = get_staging_file_path(job_id, mode)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Staging file not found: {job_id}")

    summary = read_jsonl_summary(file_path)

    if summary is None:
        raise HTTPException(status_code=500, detail="Failed to read staging file")

    return {
        "job_id": job_id,
        "mode": mode,
        "summary": summary,
    }


@router.get("/jobs/{job_id}/download")
async def download_staging_job(
    job_id: str,
    mode: str = Query("hot", description="Staging mode: hot, warm, or cold"),
    current_user: dict = Depends(get_current_user)
):
    """
    Download a staging job JSONL file.

    Accessible by all authenticated users (admin and user).
    """
    file_path = get_staging_file_path(job_id, mode)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Staging file not found: {job_id}")

    # Stream the file
    def iterfile():
        with open(file_path, 'r', encoding='utf-8') as f:
            for chunk in iter(lambda: f.read(4096), ''):
                yield chunk.encode('utf-8')

    filename = f"staging_{mode}_{job_id}.jsonl"

    return StreamingResponse(
        iterfile(),
        media_type="application/jsonl",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(file_path.stat().st_size),
        }
    )
