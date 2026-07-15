"""
Monitoring Engine - Monitoring dan alerting untuk proses scraping.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import json

@dataclass
class ScrapeMetrics:
    """Metrics untuk satu proses scraping."""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    total_accounts: int = 0
    total_posts: int = 0

    accounts_processed: int = 0
    accounts_failed: int = 0
    accounts_login_wall: int = 0

    posts_collected: int = 0
    posts_detail_extracted: int = 0

    full_success: int = 0
    partial_success: int = 0
    field_null: int = 0
    failed: int = 0

    debug_html_saved: int = 0
    debug_screenshots_saved: int = 0

    total_likes: int = 0
    total_comments: int = 0
    total_engagement: int = 0

    caption_recovery_rate: float = 0.0
    timestamp_recovery_rate: float = 0.0

    errors: List[str] = field(default_factory=list)

    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()

    def success_rate(self) -> float:
        if self.posts_collected == 0:
            return 0.0
        return (self.full_success + self.partial_success) / self.posts_collected * 100

    def to_dict(self) -> Dict:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds(),
            "total_accounts": self.total_accounts,
            "total_posts": self.total_posts,
            "accounts_processed": self.accounts_processed,
            "accounts_failed": self.accounts_failed,
            "accounts_login_wall": self.accounts_login_wall,
            "posts_collected": self.posts_collected,
            "posts_detail_extracted": self.posts_detail_extracted,
            "full_success": self.full_success,
            "partial_success": self.partial_success,
            "field_null": self.field_null,
            "failed": self.failed,
            "debug_html_saved": self.debug_html_saved,
            "debug_screenshots_saved": self.debug_screenshots_saved,
            "total_likes": self.total_likes,
            "total_comments": self.total_comments,
            "total_engagement": self.total_engagement,
            "caption_recovery_rate": self.caption_recovery_rate,
            "timestamp_recovery_rate": self.timestamp_recovery_rate,
            "success_rate": self.success_rate(),
            "errors": self.errors,
        }


@dataclass
class AlertRule:
    """Rule untuk alert."""
    name: str
    condition: Callable[[ScrapeMetrics], bool]
    message: str
    severity: str = "warning"  # info, warning, error


ALERT_RULES = [
    AlertRule(
        name="low_caption_recovery",
        condition=lambda m: m.caption_recovery_rate < 50,
        message="Caption recovery rate di bawah 50%",
        severity="error",
    ),
    AlertRule(
        name="high_account_failure",
        condition=lambda m: m.total_accounts > 0 and m.accounts_failed / m.total_accounts > 0.3,
        message="Lebih dari 30% akun gagal diproses",
        severity="error",
    ),
    AlertRule(
        name="login_wall_detected",
        condition=lambda m: m.accounts_login_wall > 0,
        message="Ada akun yang terdetect login wall",
        severity="warning",
    ),
    AlertRule(
        name="many_debug_saves",
        condition=lambda m: m.debug_html_saved > 10,
        message=f" Banyak debug HTML tersimpan ({0}+)",
        severity="info",
    ),
]


class ScrapingMonitor:
    """
    Monitor untuk tracking proses scraping.
    Usage:
        monitor = ScrapingMonitor()
        monitor.start()
        # ... run scraping ...
        monitor.end()
        alerts = monitor.check_alerts()
    """

    def __init__(self):
        self.metrics = ScrapeMetrics()
        self._running = False
        self._callbacks: List[Callable] = []

    def start(self, total_accounts: int = 0):
        """Start monitoring."""
        self.metrics = ScrapeMetrics(total_accounts=total_accounts)
        self._running = True

    def end(self):
        """End monitoring dan calculate final stats."""
        self.metrics.end_time = datetime.now()
        self._running = False
        self._calculate_rates()

    def add_callback(self, callback: Callable[[ScrapeMetrics], None]):
        """Add callback yang dipanggil setiap update."""
        self._callbacks.append(callback)

    def _notify_callbacks(self):
        """Notify all callbacks."""
        for callback in self._callbacks:
            try:
                callback(self.metrics)
            except Exception:
                pass

    def update_account_processed(self, success: bool = True, login_wall: bool = False):
        """Update metrics saat account selesai diproses."""
        self.metrics.accounts_processed += 1
        if login_wall:
            self.metrics.accounts_login_wall += 1
        elif not success:
            self.metrics.accounts_failed += 1
        self._notify_callbacks()

    def update_posts_collected(self, count: int):
        """Update jumlah posts yang dikumpulkan."""
        self.metrics.posts_collected += count

    def update_post_extracted(self, status: str):
        """Update metrics saat post detail selesai di-extract."""
        self.metrics.posts_detail_extracted += 1

        if status == "FULL_SUCCESS":
            self.metrics.full_success += 1
        elif status in ("PARTIAL_SUCCESS", "FIELD_PARTIAL_NULL"):
            self.metrics.partial_success += 1
        elif "NULL" in status or "REVIEW" in status:
            self.metrics.field_null += 1
        else:
            self.metrics.failed += 1

        self._notify_callbacks()

    def update_debug_saved(self, html: bool = False, screenshot: bool = False):
        """Update debug files saved."""
        if html:
            self.metrics.debug_html_saved += 1
        if screenshot:
            self.metrics.debug_screenshots_saved += 1

    def update_engagement(self, likes: int = 0, comments: int = 0):
        """Update engagement totals."""
        self.metrics.total_likes += likes or 0
        self.metrics.total_comments += comments or 0
        self.metrics.total_engagement += (likes or 0) + (comments or 0)

    def add_error(self, error: str):
        """Add error message."""
        self.metrics.errors.append(error)

    def _calculate_rates(self):
        """Calculate recovery rates."""
        if self.metrics.posts_collected > 0:
            # Caption recovery (posts with caption / posts collected)
            caption_count = self.metrics.full_success + self.metrics.partial_success
            self.metrics.caption_recovery_rate = caption_count / self.metrics.posts_collected * 100

            # Timestamp recovery (same logic)
            self.metrics.timestamp_recovery_rate = self.metrics.caption_recovery_rate

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check semua alert rules."""
        alerts = []

        for rule in ALERT_RULES:
            try:
                if rule.condition(self.metrics):
                    # Format message dengan actual value
                    message = rule.message
                    if "{0}" in message:
                        if "debug" in rule.name:
                            message = message.format(self.metrics.debug_html_saved)

                    alerts.append({
                        "rule": rule.name,
                        "severity": rule.severity,
                        "message": message,
                    })
            except Exception:
                pass

        return alerts

    def get_summary(self) -> Dict[str, Any]:
        """Get summary dari metrics."""
        return {
            "metrics": self.metrics.to_dict(),
            "alerts": self.check_alerts(),
            "status": "running" if self._running else "completed",
        }

    def save_report(self, output_dir: Path) -> Path:
        """Save monitoring report ke JSON."""
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = output_dir / f"monitoring_report_{timestamp}.json"

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": self.get_summary(),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return path


def create_progress_callback(monitor: ScrapingMonitor) -> Callable:
    """Create progress callback untuk scraping function."""
    def callback(event: Dict):
        stage = event.get("stage", "")
        message = event.get("message", "")

        if stage == "scrape":
            # Account processing
            pass
        elif stage == "detail":
            # Post detail extraction
            pass
        elif stage == "scroll":
            # Scroll progress
            pass
        elif stage == "stop":
            monitor.add_error(f"Stopped: {message}")

    return callback


class NullReasonTracker:
    """
    Tracker untuk null reason patterns.
    Berguna untuk identifikasi masalah recurring.
    """

    def __init__(self):
        self.reasons: Dict[str, int] = {}

    def record(self, field_name: str, null_reason: str):
        """Record sebuah null reason."""
        key = f"{field_name}:{null_reason}"
        self.reasons[key] = self.reasons.get(key, 0) + 1

    def get_top_reasons(self, limit: int = 10) -> List[tuple]:
        """Get top N null reasons."""
        sorted_reasons = sorted(self.reasons.items(), key=lambda x: x[1], reverse=True)
        return sorted_reasons[:limit]

    def get_field_reasons(self, field_name: str) -> Dict[str, int]:
        """Get reasons untuk field tertentu."""
        return {
            k.split(":", 1)[1]: v
            for k, v in self.reasons.items()
            if k.startswith(f"{field_name}:")
        }

    def to_dict(self) -> Dict:
        return {
            "total_records": sum(self.reasons.values()),
            "unique_reasons": len(self.reasons),
            "top_reasons": self.get_top_reasons(),
            "all_reasons": self.reasons,
        }
