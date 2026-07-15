"""
Unit Tests for Monitoring Engine Module (src/monitoring_engine.py)
Test Case IDs: ME-001 to ME-003

Metodologi: Speech-Driven Development (SDD)
Format: Given-When-Then (GWT)
"""

import pytest
import pytest
from datetime import datetime, timedelta

from src.monitoring_engine import (
    ScrapingMonitor,
    ScrapeMetrics,
    AlertRule,
    ALERT_RULES,
    NullReasonTracker,
    create_progress_callback,
)


# ============================================================
# Test Case: ME-001 - Track Metrics
# ============================================================

class TestScrapingMonitor:
    """ME-001: System tracks scraping metrics correctly"""

    def test_monitor_start(self):
        """
        Scenario: Monitor initializes with correct values

        When saya memanggil monitor.start(total_accounts=5)

        Then metrics.total_accounts = 5
        And metrics.start_time di-set
        """
        monitor = ScrapingMonitor()
        monitor.start(total_accounts=5)

        assert monitor.metrics.total_accounts == 5
        assert monitor.metrics.start_time is not None
        assert monitor._running is True

    def test_update_account_processed_success(self):
        """
        Scenario: Account processed successfully

        When saya memanggil update_account_processed(success=True)

        Then accounts_processed += 1
        """
        monitor = ScrapingMonitor()
        monitor.start(total_accounts=3)
        monitor.update_account_processed(success=True)

        assert monitor.metrics.accounts_processed == 1
        assert monitor.metrics.accounts_failed == 0

    def test_update_account_processed_failure(self):
        """
        Scenario: Account processing failed

        When saya memanggil update_account_processed(success=False)

        Then accounts_failed += 1
        """
        monitor = ScrapingMonitor()
        monitor.start(total_accounts=3)
        monitor.update_account_processed(success=False)

        assert monitor.metrics.accounts_processed == 1
        assert monitor.metrics.accounts_failed == 1

    def test_update_account_login_wall(self):
        """
        Scenario: Account encountered login wall

        When saya memanggil update_account_processed(login_wall=True)

        Then accounts_login_wall += 1
        """
        monitor = ScrapingMonitor()
        monitor.start(total_accounts=3)
        monitor.update_account_processed(login_wall=True)

        assert monitor.metrics.accounts_processed == 1
        assert monitor.metrics.accounts_login_wall == 1
        assert monitor.metrics.accounts_failed == 0

    def test_update_posts_collected(self):
        """
        Scenario: Posts collected from account

        When saya memanggil update_posts_collected(10)

        Then posts_collected += 10
        """
        monitor = ScrapingMonitor()
        monitor.start()
        monitor.update_posts_collected(10)

        assert monitor.metrics.posts_collected == 10

    def test_update_post_extracted_full_success(self):
        """
        Scenario: Post extracted with full success

        When saya memanggil update_post_extracted("FULL_SUCCESS")

        Then full_success += 1
        """
        monitor = ScrapingMonitor()
        monitor.start()
        monitor.update_post_extracted("FULL_SUCCESS")

        assert monitor.metrics.full_success == 1
        assert monitor.metrics.partial_success == 0

    def test_update_post_extracted_partial_success(self):
        """
        Scenario: Post extracted with partial success

        When saya memanggil update_post_extracted("PARTIAL_SUCCESS")

        Then partial_success += 1
        """
        monitor = ScrapingMonitor()
        monitor.start()
        monitor.update_post_extracted("PARTIAL_SUCCESS")

        assert monitor.metrics.partial_success == 1

    def test_update_post_extracted_null(self):
        """
        Scenario: Post extraction resulted in null fields

        When saya memanggil update_post_extracted("FIELD_PARTIAL_NULL")

        Then partial_success += 1 (FIELD_PARTIAL_NULL is treated as partial success)
        """
        monitor = ScrapingMonitor()
        monitor.start()
        monitor.update_post_extracted("FIELD_PARTIAL_NULL")

        assert monitor.metrics.partial_success == 1

    def test_update_engagement(self):
        """
        Scenario: Engagement metrics updated

        When saya memanggil update_engagement(likes=100, comments=10)

        Then:
          - total_likes = 100
          - total_comments = 10
          - total_engagement = 110
        """
        monitor = ScrapingMonitor()
        monitor.start()
        monitor.update_engagement(likes=100, comments=10)

        assert monitor.metrics.total_likes == 100
        assert monitor.metrics.total_comments == 10
        assert monitor.metrics.total_engagement == 110

    def test_monitor_end(self):
        """
        Scenario: Monitor ends and calculates final stats

        When saya memanggil monitor.end()

        Then:
          - end_time di-set
          - _running = False
          - rates calculated
        """
        monitor = ScrapingMonitor()
        monitor.start(total_accounts=5)
        monitor.update_posts_collected(10)
        monitor.update_post_extracted("FULL_SUCCESS")
        import time
        time.sleep(0.01)  # Small delay to ensure duration > 0
        monitor.end()

        assert monitor.metrics.end_time is not None
        assert monitor._running is False
        assert monitor.metrics.duration_seconds() >= 0

    def test_full_workflow(self):
        """
        Scenario: Complete scraping workflow tracking

        When saya memanggil:
          - monitor.start(total_accounts=5)
          - monitor.update_account_processed(success=True)
          - monitor.update_posts_collected(10)
          - monitor.update_post_extracted("FULL_SUCCESS")  # 10x untuk posts_collected=10
          - monitor.end()

        Then metrics:
          - accounts_processed = 1
          - posts_collected = 10
          - full_success = 10 (one per post collected)
          - success_rate = 100.0
        """
        monitor = ScrapingMonitor()
        monitor.start(total_accounts=5)
        monitor.update_account_processed(success=True)
        monitor.update_posts_collected(10)
        # Simulate extracting all 10 posts successfully
        for _ in range(10):
            monitor.update_post_extracted("FULL_SUCCESS")
        monitor.end()

        assert monitor.metrics.accounts_processed == 1
        assert monitor.metrics.posts_collected == 10
        assert monitor.metrics.full_success == 10
        assert monitor.metrics.success_rate() == 100.0


# ============================================================
# Test Case: ME-002 - Alert Rules
# ============================================================

class TestAlertRules:
    """ME-002: System triggers alerts based on conditions"""

    def test_low_caption_recovery_alert(self):
        """
        Scenario: Alert triggered when caption recovery < 50%

        Given metrics dengan caption_recovery_rate = 40 (< 50%)

        When saya memanggil monitor.check_alerts()

        Then alert terpicu:
          - rule: "low_caption_recovery"
          - severity: "error"
          - message: "Caption recovery rate di bawah 50%"
        """
        monitor = ScrapingMonitor()
        monitor.start()
        monitor.metrics.caption_recovery_rate = 40
        monitor.end()

        alerts = monitor.check_alerts()

        assert len(alerts) > 0
        low_caption_alert = next((a for a in alerts if a["rule"] == "low_caption_recovery"), None)
        assert low_caption_alert is not None
        assert low_caption_alert["severity"] == "error"

    def test_high_account_failure_alert(self):
        """
        Scenario: Alert when >30% accounts failed

        Given:
          - total_accounts = 10
          - accounts_failed = 4 (> 30%)

        When saya memanggil check_alerts

        Then alert "high_account_failure" terpicu
        """
        monitor = ScrapingMonitor()
        monitor.start(total_accounts=10)
        for _ in range(4):
            monitor.update_account_processed(success=False)
        monitor.end()

        alerts = monitor.check_alerts()
        high_failure_alert = next((a for a in alerts if a["rule"] == "high_account_failure"), None)
        assert high_failure_alert is not None

    def test_login_wall_alert(self):
        """
        Scenario: Warning when login wall detected

        Given metrics.accounts_login_wall > 0

        When saya memanggil check_alerts

        Then alert dengan severity "warning" terpicu
        """
        monitor = ScrapingMonitor()
        monitor.start()
        monitor.update_account_processed(login_wall=True)
        monitor.end()

        alerts = monitor.check_alerts()
        login_wall_alert = next((a for a in alerts if a["rule"] == "login_wall_detected"), None)
        assert login_wall_alert is not None
        assert login_wall_alert["severity"] == "warning"

    def test_no_alerts_when_good_metrics(self):
        """
        Scenario: No alerts when metrics are good

        Given:
          - caption_recovery_rate = 80%
          - accounts_failed = 0
          - accounts_login_wall = 0

        When saya memanggil check_alerts

        Then tidak ada alert
        """
        monitor = ScrapingMonitor()
        monitor.start()
        monitor.metrics.caption_recovery_rate = 80
        monitor.update_account_processed(success=True)
        monitor.end()

        alerts = monitor.check_alerts()
        assert len(alerts) == 0

    def test_multiple_alerts_triggered(self):
        """
        Scenario: Multiple alerts can be triggered

        Given:
          - caption_recovery_rate = 30%
          - accounts_login_wall = 2

        When saya memanggil check_alerts

        Then 2+ alerts returned
        """
        monitor = ScrapingMonitor()
        monitor.start()
        monitor.metrics.caption_recovery_rate = 30
        monitor.update_account_processed(login_wall=True)
        monitor.update_account_processed(login_wall=True)
        monitor.end()

        alerts = monitor.check_alerts()
        assert len(alerts) >= 2


# ============================================================
# Test Case: ME-003 - Success Rate Calculation
# ============================================================

class TestSuccessRateCalculation:
    """ME-003: System calculates success rate correctly"""

    def test_success_rate_calculation(self):
        """
        Scenario: Success rate = (full_success + partial_success) / posts_collected * 100

        Given:
          - full_success = 8
          - partial_success = 2
          - posts_collected = 12

        When saya memanggil metrics.success_rate()

        Then hasil = 83.33 (%)
        """
        metrics = ScrapeMetrics()
        metrics.full_success = 8
        metrics.partial_success = 2
        metrics.posts_collected = 12

        success_rate = metrics.success_rate()

        assert success_rate == pytest.approx(83.33, rel=0.01)

    def test_success_rate_zero_posts(self):
        """
        Scenario: Zero posts returns 0% success rate

        Given posts_collected = 0

        When saya memanggil success_rate

        Then 0.0
        """
        metrics = ScrapeMetrics()
        assert metrics.success_rate() == 0.0

    def test_success_rate_all_full_success(self):
        """
        Scenario: All posts full success = 100%

        Given:
          - full_success = 10
          - posts_collected = 10

        When saya memanggil success_rate

        Then 100.0
        """
        metrics = ScrapeMetrics()
        metrics.full_success = 10
        metrics.posts_collected = 10

        assert metrics.success_rate() == 100.0


# ============================================================
# Additional Monitoring Tests
# ============================================================

class TestScrapeMetrics:
    """Tests for ScrapeMetrics dataclass"""

    def test_duration_seconds_while_running(self):
        """
        Scenario: Duration calculated from start_time to now

        Given monitor started 5 seconds ago

        When saya memanggil duration_seconds

        Then hasil ~5 detik
        """
        metrics = ScrapeMetrics()
        # Manually set start_time to 5 seconds ago
        metrics.start_time = datetime.now() - timedelta(seconds=5)

        duration = metrics.duration_seconds()

        assert 4 < duration < 6

    def test_duration_seconds_after_end(self):
        """
        Scenario: Duration calculated to end_time

        Given:
          - start_time = T0
          - end_time = T0 + 10 detik

        When saya memanggil duration_seconds

        Then hasil ~10 detik
        """
        metrics = ScrapeMetrics()
        metrics.start_time = datetime.now() - timedelta(seconds=10)
        metrics.end_time = datetime.now()

        duration = metrics.duration_seconds()

        assert 9 < duration < 11

    def test_to_dict(self):
        """
        Scenario: Metrics converted to dict for serialization

        When saya memanggil metrics.to_dict()

        Then dict dengan semua field metrics
        """
        metrics = ScrapeMetrics()
        metrics.total_accounts = 5
        metrics.posts_collected = 20
        metrics.full_success = 15

        result = metrics.to_dict()

        assert result["total_accounts"] == 5
        assert result["posts_collected"] == 20
        assert result["full_success"] == 15
        assert "start_time" in result
        assert "duration_seconds" in result


class TestNullReasonTracker:
    """Tests for NullReasonTracker"""

    def test_record_null_reason(self):
        """
        Scenario: Track null reasons

        When saya memanggil tracker.record("caption", "NOT_FOUND")

        Then reasons["caption:NOT_FOUND"] = 1
        """
        tracker = NullReasonTracker()
        tracker.record("caption", "NOT_FOUND")

        assert tracker.reasons["caption:NOT_FOUND"] == 1

    def test_record_increments_count(self):
        """
        Scenario: Same reason increments counter

        When saya memanggil:
          - record("caption", "NOT_FOUND")
          - record("caption", "NOT_FOUND")

        Then count = 2
        """
        tracker = NullReasonTracker()
        tracker.record("caption", "NOT_FOUND")
        tracker.record("caption", "NOT_FOUND")

        assert tracker.reasons["caption:NOT_FOUND"] == 2

    def test_get_top_reasons(self):
        """
        Scenario: Get top N null reasons

        Given multiple reasons with different counts

        When saya memanggil get_top_reasons(limit=2)

        Then top 2 reasons returned
        """
        tracker = NullReasonTracker()
        tracker.record("caption", "NOT_FOUND")
        tracker.record("caption", "NOT_FOUND")
        tracker.record("caption", "ELEMENT_MISSING")
        tracker.record("timestamp", "NOT_FOUND")

        top = tracker.get_top_reasons(limit=2)

        assert len(top) == 2
        assert top[0][0] == "caption:NOT_FOUND"  # Count 2
        assert top[0][1] == 2

    def test_get_field_reasons(self):
        """
        Scenario: Get reasons for specific field

        When saya memanggil get_field_reasons("caption")

        Then hanya reason untuk field "caption"
        """
        tracker = NullReasonTracker()
        tracker.record("caption", "NOT_FOUND")
        tracker.record("caption", "EMPTY")
        tracker.record("timestamp", "NOT_FOUND")

        caption_reasons = tracker.get_field_reasons("caption")

        # Returns dict like {'NOT_FOUND': 1, 'EMPTY': 1} without field prefix
        assert "NOT_FOUND" in caption_reasons
        assert "EMPTY" in caption_reasons
        assert caption_reasons["NOT_FOUND"] == 1
        assert caption_reasons["EMPTY"] == 1
        assert "timestamp:NOT_FOUND" not in caption_reasons

    def test_to_dict(self):
        """
        Scenario: Tracker serialized to dict

        When saya memanggil tracker.to_dict()

        Then dict dengan summary
        """
        tracker = NullReasonTracker()
        tracker.record("caption", "NOT_FOUND")

        result = tracker.to_dict()

        assert result["total_records"] == 1
        assert result["unique_reasons"] == 1
        assert "top_reasons" in result


class TestProgressCallback:
    """Tests for progress callback factory"""

    def test_create_progress_callback(self):
        """
        Scenario: Progress callback created successfully

        Given monitor

        When saya memanggil create_progress_callback(monitor)

        Then callback function returned
        """
        monitor = ScrapingMonitor()
        callback = create_progress_callback(monitor)

        assert callable(callback)

    def test_progress_callback_handles_stop_event(self):
        """
        Scenario: Callback handles stop event

        Given callback dengan event type "stop"

        When dipanggil dengan message "Rate limited"

        Then error added ke metrics
        """
        monitor = ScrapingMonitor()
        callback = create_progress_callback(monitor)

        callback({"stage": "stop", "message": "Rate limited"})

        assert "Stopped: Rate limited" in monitor.metrics.errors


class TestAlertRulesRegistry:
    """Tests for ALERT_RULES registry"""

    def test_alert_rules_exist(self):
        """
        Scenario: Alert rules are defined

        Then ALERT_RULES list tidak kosong
        """
        assert len(ALERT_RULES) > 0

    def test_alert_rules_have_required_fields(self):
        """
        Scenario: All alert rules have required fields

        Then setiap rule memiliki: name, condition, message, severity
        """
        for rule in ALERT_RULES:
            assert hasattr(rule, "name")
            assert hasattr(rule, "condition")
            assert hasattr(rule, "message")
            assert hasattr(rule, "severity")

    def test_alert_severity_values(self):
        """
        Scenario: Alert severities are valid

        Then severity adalah: info, warning, atau error
        """
        valid_severities = ["info", "warning", "error"]
        for rule in ALERT_RULES:
            assert rule.severity in valid_severities


class TestGetSummary:
    """Tests for get_summary method"""

    def test_get_summary_structure(self):
        """
        Scenario: Summary contains metrics and alerts

        When saya memanggil get_summary()

        Then hasil memiliki keys: metrics, alerts, status
        """
        monitor = ScrapingMonitor()
        monitor.start()
        monitor.metrics.caption_recovery_rate = 30
        monitor.update_account_processed(login_wall=True)
        monitor.end()

        summary = monitor.get_summary()

        assert "metrics" in summary
        assert "alerts" in summary
        assert "status" in summary

    def test_save_report(self, tmp_path):
        """
        Scenario: Monitoring report saved to JSON

        When saya memanggil save_report(output_dir)

        Then file JSON dibuat di output_dir
        """
        monitor = ScrapingMonitor()
        monitor.start(total_accounts=3)
        monitor.update_account_processed(success=True)
        monitor.end()

        report_path = monitor.save_report(tmp_path)

        assert report_path.exists()
        assert report_path.suffix == ".json"
        assert "monitoring_report_" in report_path.name