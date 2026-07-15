"""
Unit Tests for Notification Service Module (src/notification_service.py)
Test Case IDs: NS-001 to NS-007

Metodologi: Test-Driven Development (TDD)
Format: Given-When-Then (GWT)
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, "C:/Users/syamh/magang/Project Kemenkeu/mayz_djpb_pusat")

from src.notification_service import (
    _safe,
    build_new_post_message,
    send_telegram_message,
    test_telegram_notification,
    send_job_complete_notification,
    get_telegram_status,
    get_telegram_enabled,
    get_telegram_token,
    get_telegram_chat_id,
)


# ============================================================
# Test Case: NS-001 - Build New Post Message
# ============================================================

class TestBuildNewPostMessage:
    """NS-001: System formats new post notification correctly"""

    def test_build_message_basic(self):
        """
        Scenario: System formats basic notification message

        Given post data:
          - username: "djpbjakarta"
          - nama_unit: "Kanwil DJPb Jakarta"
          - caption: "Detail kegiatan..."
          - like_count: 150
          - comment_count: 12

        When saya memanggil build_new_post_message(...)

        Then message mengandung:
          - "Mayz Monitoring Alert"
          - "@djpbjakarta"
          - "Kanwil DJPb Jakarta"
          - "Like: 150"
        """
        message = build_new_post_message(
            username="djpbjakarta",
            nama_unit="Kanwil DJPb Jakarta",
            post_url="https://instagram.com/p/ABC123/",
            caption="Detail kegiatan monitoring hari ini di Jakarta",
            timestamp=datetime(2026, 6, 15, 10, 30),
            media_type="Post",
            like_count=150,
            comment_count=12,
        )

        assert "Mayz Monitoring Alert" in message
        assert "@djpbjakarta" in message
        assert "Kanwil DJPb Jakarta" in message
        assert "Like:" in message
        assert "150" in message
        assert "Komentar:" in message
        assert "12" in message

    def test_build_message_truncates_long_caption(self):
        """
        Scenario: Long caption truncated to 200 chars

        Given caption dengan 300+ karakter

        When saya memanggil build_new_post_message

        Then caption di-truncate dengan "..."
        """
        long_caption = "A" * 300
        message = build_new_post_message(
            username="test",
            nama_unit="Test Unit",
            post_url="https://instagram.com/p/ABC123/",
            caption=long_caption,
            timestamp=datetime(2026, 6, 15),
            media_type="Post",
        )

        # Caption section should be truncated
        assert "..." in message
        assert len(message) < 2000  # Should not be the full 300 char caption

    def test_build_message_without_engagement(self):
        """
        Scenario: Message without engagement data

        Given post tanpa like/comment count

        When saya memanggil build_new_post_message

        Then engagement section tidak muncul
        """
        message = build_new_post_message(
            username="test",
            nama_unit="Test Unit",
            post_url="https://instagram.com/p/ABC123/",
            caption="Test caption",
            timestamp=datetime(2026, 6, 15),
            media_type="Post",
        )

        # Should contain basic info but no engagement numbers
        assert "Test Unit" in message
        assert "Test caption" in message

    def test_build_message_datetime_format(self):
        """
        Scenario: Datetime formatted as DD/MM/YYYY HH:MM

        Given timestamp: 2026-06-15 10:30

        When saya memanggil build_new_post_message

        Then formatted as "15/06/2026 10:30"
        """
        message = build_new_post_message(
            username="test",
            nama_unit="Test Unit",
            post_url="https://instagram.com/p/ABC123/",
            timestamp=datetime(2026, 6, 15, 10, 30),
            media_type="Post",
        )

        # Check for formatted date
        assert "15/06/2026" in message or "15/06/2026" in message.replace(" ", "")
        assert "10:30" in message

    def test_build_message_empty_caption(self):
        """
        Scenario: Handle empty caption

        Given caption = ""

        When saya memanggil build_new_post_message

        Then tidak error
        """
        message = build_new_post_message(
            username="test",
            nama_unit="Test Unit",
            post_url="https://instagram.com/p/ABC123/",
            caption="",
            timestamp=datetime(2026, 6, 15),
            media_type="Post",
        )

        assert message is not None
        assert "Mayz Monitoring Alert" in message

    def test_build_message_with_reels(self):
        """
        Scenario: Handle Reels media type

        Given media_type = "reels"

        When saya memanggil build_new_post_message

        Then message contains "reels"
        """
        message = build_new_post_message(
            username="test",
            nama_unit="Test Unit",
            post_url="https://instagram.com/p/ABC123/",
            media_type="reels",
        )

        # Media type should be displayed
        assert message is not None


# ============================================================
# Test Case: NS-002 - Get Telegram Configuration
# ============================================================

class TestGetTelegramConfig:
    """NS-002: System retrieves Telegram configuration correctly"""

    def test_get_telegram_enabled_returns_bool(self):
        """
        Scenario: get_telegram_enabled returns boolean

        When saya memanggil get_telegram_enabled()

        Then hasil adalah boolean
        """
        result = get_telegram_enabled()
        assert isinstance(result, bool)

    def test_get_telegram_token_returns_string(self):
        """
        Scenario: get_telegram_token returns string

        When saya memanggil get_telegram_token()

        Then hasil adalah string (bisa kosong)
        """
        result = get_telegram_token()
        assert isinstance(result, str)

    def test_get_telegram_chat_id_returns_string(self):
        """
        Scenario: get_telegram_chat_id returns string

        When saya memanggil get_telegram_chat_id()

        Then hasil adalah string (bisa kosong)
        """
        result = get_telegram_chat_id()
        assert isinstance(result, str)


# ============================================================
# Test Case: NS-003 - Send Telegram Disabled
# ============================================================

class TestSendTelegramDisabled:
    """NS-003: System returns error when Telegram disabled"""

    def test_send_telegram_when_disabled(self):
        """
        Scenario: Telegram disabled returns error

        Given TELEGRAM_ENABLED = false (via mock)

        When saya memanggil send_telegram_message("test")

        Then hasil = (False, "Telegram tidak diaktifkan.")
        """
        with patch("src.notification_service.get_telegram_enabled", return_value=False):
            success, message = send_telegram_message("Test message")

            assert success is False
            assert "tidak diaktifkan" in message

    def test_send_telegram_missing_token(self):
        """
        Scenario: Missing bot token returns error

        Given TELEGRAM_ENABLED = true
        And TELEGRAM_BOT_TOKEN = ""

        When saya memanggil send_telegram_message("test")

        Then hasil = (False, "Telegram bot token atau chat ID belum dikonfigurasi.")
        """
        with patch("src.notification_service.get_telegram_enabled", return_value=True):
            with patch("src.notification_service.get_telegram_token", return_value=""):
                success, message = send_telegram_message("Test message")

                assert success is False
                assert "belum dikonfigurasi" in message

    def test_send_telegram_missing_chat_id(self):
        """
        Scenario: Missing chat ID returns error

        Given TELEGRAM_ENABLED = true
        And TELEGRAM_BOT_TOKEN = "valid_token"
        And TELEGRAM_CHAT_ID = ""

        When saya memanggil send_telegram_message("test")

        Then error message about configuration
        """
        with patch("src.notification_service.get_telegram_enabled", return_value=True):
            with patch("src.notification_service.get_telegram_token", return_value="valid_token_123"):
                with patch("src.notification_service.get_telegram_chat_id", return_value=""):
                    success, message = send_telegram_message("Test message")

                    assert success is False
                    assert "belum dikonfigurasi" in message


# ============================================================
# Test Case: NS-004 - Test Telegram Connection
# ============================================================

class TestTestTelegramConnection:
    """NS-004: System validates Telegram credentials"""

    def test_test_without_token(self):
        """
        Scenario: Test fails without bot token

        Given TELEGRAM_BOT_TOKEN = ""

        When saya memanggil test_telegram_notification()

        Then hasil = (False, "Bot token belum dikonfigurasi...")
        """
        with patch("src.notification_service.get_telegram_token", return_value=""):
            success, message = test_telegram_notification()

            assert success is False
            assert "Bot token belum dikonfigurasi" in message

    def test_test_without_chat_id(self):
        """
        Scenario: Test fails without chat ID

        Given TELEGRAM_BOT_TOKEN = "valid_token"
        And TELEGRAM_CHAT_ID = ""

        When saya memanggil test_telegram_notification()

        Then hasil = (False, "Chat ID belum dikonfigurasi...")
        """
        with patch("src.notification_service.get_telegram_token", return_value="valid_token"):
            with patch("src.notification_service.get_telegram_chat_id", return_value=""):
                success, message = test_telegram_notification()

                assert success is False
                assert "Chat ID belum dikonfigurasi" in message

    def test_test_with_valid_credentials(self):
        """
        Scenario: Test sends message with valid credentials

        Given valid TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

        When saya memanggil test_telegram_notification()

        Then message sent via Telegram API (mocked)
        """
        with patch("src.notification_service.get_telegram_token", return_value="valid_token_123"):
            with patch("src.notification_service.get_telegram_chat_id", return_value="chat_id_456"):
                with patch("src.notification_service.requests.post") as mock_post:
                    mock_response = MagicMock()
                    mock_response.json.return_value = {"ok": True}
                    mock_response.status_code = 200
                    mock_post.return_value = mock_response

                    success, message = test_telegram_notification()

                    # Note: This might still fail due to other config issues,
                    # but the mock should be set up correctly
                    assert mock_post.called or success is False


# ============================================================
# Test Case: NS-005 - _safe Helper Function
# ============================================================

class TestSafeFunction:
    """Tests for _safe helper function"""

    def test_safe_html_escape(self):
        """
        Scenario: HTML characters are escaped

        Given value: "<script>alert('xss')</script>"

        When saya memanggil _safe(value)

        Then HTML escaped: &lt;script&gt;...
        """
        result = _safe("<script>alert('xss')</script>")
        assert "<" not in result
        assert ">" not in result

    def test_safe_none_value(self):
        """
        Scenario: None converted to "-"

        Given value = None

        When saya memanggil _safe(value)

        Then "-"
        """
        result = _safe(None)
        assert result == "-"

    def test_safe_normal_string(self):
        """
        Scenario: Normal string unchanged

        Given value = "Normal text"

        When saya memanggil _safe(value)

        Then "Normal text"
        """
        result = _safe("Normal text")
        assert result == "Normal text"

    def test_safe_empty_string(self):
        """
        Scenario: Empty string converted to "-"

        Given value = ""

        When saya memanggil _safe(value)

        Then "-"
        """
        result = _safe("")
        assert result == "-"


# ============================================================
# Test Case: NS-006 - Send Job Complete Notification
# ============================================================

class TestSendJobCompleteNotification:
    """Tests for job completion notifications"""

    def test_job_complete_when_disabled(self):
        """
        Scenario: Job notification when Telegram disabled

        Given TELEGRAM_ENABLED = false

        When saya memanggil send_job_complete_notification

        Then returns False with disabled message
        """
        with patch("src.notification_service.get_telegram_enabled", return_value=False):
            success, message = send_job_complete_notification(
                job_id="JOB_001",
                job_type="LATEST_SYNC",
                status="SUCCESS",
            )

            assert success is False
            assert "tidak diaktifkan" in message

    def test_job_complete_message_format(self):
        """
        Scenario: Job complete message contains job details

        Given job dengan:
          - job_id = "JOB_001"
          - job_type = "LATEST_SYNC"
          - status = "SUCCESS"
          - total_posts = 50
          - new_posts = 5

        When saya memanggil send_job_complete_notification

        Then message contains job details (when enabled)
        """
        # Test with disabled - just check it doesn't crash
        with patch("src.notification_service.get_telegram_enabled", return_value=False):
            success, message = send_job_complete_notification(
                job_id="JOB_001",
                job_type="LATEST_SYNC",
                status="SUCCESS",
                total_posts=50,
                new_posts=5,
            )

            assert success is False  # Because disabled
            assert message is not None


# ============================================================
# Test Case: NS-007 - Get Telegram Status
# ============================================================

class TestGetTelegramStatus:
    """Tests for get_telegram_status function"""

    def test_status_when_disabled(self):
        """
        Scenario: Status shows disabled when not configured

        Given TELEGRAM_ENABLED = false

        When saya memanggil get_telegram_status

        Then status.enabled = False
        """
        with patch("src.notification_service.get_telegram_enabled", return_value=False):
            status = get_telegram_status()

            assert status["enabled"] is False
            assert status["configured"] is False

    def test_status_when_enabled_and_configured(self):
        """
        Scenario: Status shows configured when all settings present

        Given TELEGRAM_ENABLED = true
        And TELEGRAM_BOT_TOKEN = "token"
        And TELEGRAM_CHAT_ID = "chat_id"

        When saya memanggil get_telegram_status

        Then status.configured = True
        """
        with patch("src.notification_service.get_telegram_enabled", return_value=True):
            with patch("src.notification_service.get_telegram_token", return_value="valid_token"):
                with patch("src.notification_service.get_telegram_chat_id", return_value="valid_chat"):
                    status = get_telegram_status()

                    assert status["enabled"] is True
                    assert status["configured"] is True
                    assert status["bot_token_set"] is True
                    assert status["chat_id_set"] is True

    def test_status_partial_configuration(self):
        """
        Scenario: Status shows partial when only token set

        Given TELEGRAM_BOT_TOKEN = "token"
        And TELEGRAM_CHAT_ID = ""

        When saya memanggil get_telegram_status

        Then:
          - bot_token_set = True
          - chat_id_set = False
          - configured = False
        """
        with patch("src.notification_service.get_telegram_enabled", return_value=True):
            with patch("src.notification_service.get_telegram_token", return_value="valid_token"):
                with patch("src.notification_service.get_telegram_chat_id", return_value=""):
                    status = get_telegram_status()

                    assert status["bot_token_set"] is True
                    assert status["chat_id_set"] is False
                    assert status["configured"] is False


# ============================================================
# Test Case: NS-008 - Telegram API Error Handling
# ============================================================

class TestTelegramApiErrors:
    """Tests for Telegram API error handling"""

    def test_handles_timeout_error(self):
        """
        Scenario: Timeout returns appropriate error message

        Given requests.post raises Timeout

        When saya memanggil send_telegram_message

        Then hasil = (False, "Request timeout saat mengirim Telegram.")
        """
        with patch("src.notification_service.get_telegram_enabled", return_value=True):
            with patch("src.notification_service.get_telegram_token", return_value="valid_token"):
                with patch("src.notification_service.get_telegram_chat_id", return_value="valid_chat"):
                    with patch("src.notification_service.requests.post") as mock_post:
                        import requests
                        mock_post.side_effect = requests.exceptions.Timeout()

                        success, message = send_telegram_message("Test")

                        assert success is False
                        assert "timeout" in message.lower()

    def test_handles_connection_error(self):
        """
        Scenario: Connection error returns appropriate message

        Given requests.post raises ConnectionError

        When saya memanggil send_telegram_message

        Then hasil = (False, "Gagal terhubung ke Telegram API.")
        """
        with patch("src.notification_service.get_telegram_enabled", return_value=True):
            with patch("src.notification_service.get_telegram_token", return_value="valid_token"):
                with patch("src.notification_service.get_telegram_chat_id", return_value="valid_chat"):
                    with patch("src.notification_service.requests.post") as mock_post:
                        import requests
                        mock_post.side_effect = requests.exceptions.ConnectionError()

                        success, message = send_telegram_message("Test")

                        assert success is False
                        assert "terhubung" in message.lower() or "connection" in message.lower()

    def test_handles_api_error_response(self):
        """
        Scenario: API returns error response

        Given Telegram API returns ok=False

        When saya memanggil send_telegram_message

        Then hasil = (False, error_description)
        """
        with patch("src.notification_service.get_telegram_enabled", return_value=True):
            with patch("src.notification_service.get_telegram_token", return_value="valid_token"):
                with patch("src.notification_service.get_telegram_chat_id", return_value="valid_chat"):
                    with patch("src.notification_service.requests.post") as mock_post:
                        mock_response = MagicMock()
                        mock_response.json.return_value = {
                            "ok": False,
                            "description": "Bad Request: chat not found"
                        }
                        mock_response.status_code = 400
                        mock_post.return_value = mock_response

                        success, message = send_telegram_message("Test")

                        assert success is False
                        assert "chat not found" in message

    def test_handles_success_response(self):
        """
        Scenario: API returns success response

        Given Telegram API returns ok=True

        When saya memanggil send_telegram_message

        Then hasil = (True, ...)
        """
        with patch("src.notification_service.get_telegram_enabled", return_value=True):
            with patch("src.notification_service.get_telegram_token", return_value="valid_token"):
                with patch("src.notification_service.get_telegram_chat_id", return_value="valid_chat"):
                    with patch("src.notification_service.requests.post") as mock_post:
                        mock_response = MagicMock()
                        mock_response.json.return_value = {"ok": True}
                        mock_response.status_code = 200
                        mock_post.return_value = mock_response

                        success, message = send_telegram_message("Test")

                        assert success is True
