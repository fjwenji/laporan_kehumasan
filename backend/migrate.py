"""
Database migrations for Mayz Monitoring Backend

This script creates additional tables needed for the new React dashboard:
1. users - User authentication
2. job_failed_items - Failed scraping items tracking
3. export_logs - Export history tracking
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db_cursor, test_connection
from app.api.deps import hash_password


def run_migrations():
    """Run all database migrations."""
    print("=" * 60)
    print("MAYZ MONITORING - DATABASE MIGRATIONS")
    print("=" * 60)

    # Test connection
    print("\n[1/5] Testing database connection...")
    success, msg = test_connection()
    if not success:
        print(f"  [ERROR] {msg}")
        print("  Please ensure MySQL is running and credentials are correct.")
        return False
    print(f"  [OK] {msg}")

    print("\n[2/5] Creating tables...")

    # Table: users
    print("  - Creating users table...")
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    role ENUM('admin', 'user') DEFAULT 'user',
                    nama_lengkap VARCHAR(255) DEFAULT '',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_username (username),
                    INDEX idx_role (role)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("    [OK] users table created/verified")
    except Exception as e:
        print(f"    [ERROR] {e}")

    # Table: job_failed_items
    print("  - Creating job_failed_items table...")
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_failed_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    job_id VARCHAR(100) NOT NULL,
                    username VARCHAR(100) DEFAULT '',
                    post_url VARCHAR(500) DEFAULT NULL,
                    shortcode VARCHAR(50) DEFAULT '',
                    reason TEXT,
                    error_type VARCHAR(50) DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_job_id (job_id),
                    INDEX idx_username (username),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("    [OK] job_failed_items table created/verified")
    except Exception as e:
        print(f"    [ERROR] {e}")

    # Table: export_logs
    print("  - Creating export_logs table...")
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS export_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    exported_by VARCHAR(100) NOT NULL,
                    period_start DATE NOT NULL,
                    period_end DATE NOT NULL,
                    record_count INT DEFAULT 0,
                    file_size INT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_exported_by (exported_by),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("    [OK] export_logs table created/verified")
    except Exception as e:
        print(f"    [ERROR] {e}")

    # Table: alerts
    print("  - Creating alerts table...")
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    alert_type VARCHAR(50) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT,
                    severity ENUM('info', 'warning', 'danger') DEFAULT 'info',
                    is_read BOOLEAN DEFAULT FALSE,
                    metadata JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_is_read (is_read),
                    INDEX idx_created_at (created_at),
                    INDEX idx_alert_type (alert_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("    [OK] alerts table created/verified")
    except Exception as e:
        print(f"    [ERROR] {e}")

    print("\n[3/5] Verifying existing tables...")
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SHOW TABLES")
            tables = [row[list(row.keys())[0]] for row in cursor.fetchall()]
            print(f"  [OK] Found {len(tables)} tables:")
            for t in tables:
                print(f"      - {t}")
    except Exception as e:
        print(f"  [ERROR] {e}")

    print("\n[4/5] Creating default admin user...")
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if cursor.fetchone():
                print("  [SKIP] Admin user already exists")
            else:
                # Create default admin with secure hashed password
                password_hash = hash_password("admin123")
                with get_db_cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO users (username, password_hash, role, nama_lengkap, is_active)
                        VALUES ('admin', %s, 'admin', 'Administrator', TRUE)
                    """, (password_hash,))
                    print("  [OK] Admin user created (username: admin, password: admin123)")
                    print("  [WARN] Please change the password immediately in production!")
    except Exception as e:
        print(f"  [ERROR] {e}")

    print("\n[5/5] Checking for missing columns in existing tables...")
    try:
        with get_db_cursor(commit=False) as cursor:
            # Check scrape_jobs for worker columns
            cursor.execute("SHOW COLUMNS FROM scrape_jobs LIKE 'worker_id'")
            if not cursor.fetchone():
                print("  - Adding worker_id to scrape_jobs...")
                try:
                    with get_db_cursor() as cursor:
                        cursor.execute("ALTER TABLE scrape_jobs ADD COLUMN worker_id VARCHAR(100) NULL")
                        print("    [OK] Added worker_id")
                except:
                    pass

            cursor.execute("SHOW COLUMNS FROM scrape_jobs LIKE 'worker_pid'")
            if not cursor.fetchone():
                print("  - Adding worker_pid to scrape_jobs...")
                try:
                    with get_db_cursor() as cursor:
                        cursor.execute("ALTER TABLE scrape_jobs ADD COLUMN worker_pid INT NULL")
                        print("    [OK] Added worker_pid")
                except:
                    pass

            cursor.execute("SHOW COLUMNS FROM scrape_jobs LIKE 'worker_heartbeat_at'")
            if not cursor.fetchone():
                print("  - Adding worker_heartbeat_at to scrape_jobs...")
                try:
                    with get_db_cursor() as cursor:
                        cursor.execute("ALTER TABLE scrape_jobs ADD COLUMN worker_heartbeat_at DATETIME NULL")
                        print("    [OK] Added worker_heartbeat_at")
                except:
                    pass

    except Exception as e:
        print(f"  [ERROR] {e}")

    # Table: telegram_recipients
    print("  - Creating telegram_recipients table...")
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telegram_recipients (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    chat_id VARCHAR(100) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_chat_id (chat_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("    [OK] telegram_recipients table created/verified")
    except Exception as e:
        print(f"    [ERROR] {e}")

    # Add notes column to accounts table
    print("  - Checking accounts table for notes column...")
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SHOW COLUMNS FROM accounts LIKE 'notes'")
            if not cursor.fetchone():
                print("  - Adding notes column to accounts...")
                with get_db_cursor() as cursor:
                    cursor.execute("ALTER TABLE accounts ADD COLUMN notes TEXT NULL")
                    print("    [OK] Added notes column")
    except Exception as e:
        print(f"    [ERROR] {e}")

    # Add profile metrics columns to accounts table
    print("  - Checking accounts table for profile metrics columns...")
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SHOW COLUMNS FROM accounts LIKE 'followers_count'")
            if not cursor.fetchone():
                print("  - Adding followers_count to accounts...")
                with get_db_cursor() as cursor:
                    cursor.execute("ALTER TABLE accounts ADD COLUMN followers_count INT NULL")
                    print("    [OK] Added followers_count")
    except Exception as e:
        print(f"    [ERROR] {e}")

    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SHOW COLUMNS FROM accounts LIKE 'following_count'")
            if not cursor.fetchone():
                print("  - Adding following_count to accounts...")
                with get_db_cursor() as cursor:
                    cursor.execute("ALTER TABLE accounts ADD COLUMN following_count INT NULL")
                    print("    [OK] Added following_count")
    except Exception as e:
        print(f"    [ERROR] {e}")

    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SHOW COLUMNS FROM accounts LIKE 'profile_posts_count'")
            if not cursor.fetchone():
                print("  - Adding profile_posts_count to accounts...")
                with get_db_cursor() as cursor:
                    cursor.execute("ALTER TABLE accounts ADD COLUMN profile_posts_count INT NULL")
                    print("    [OK] Added profile_posts_count")
    except Exception as e:
        print(f"    [ERROR] {e}")

    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SHOW COLUMNS FROM accounts LIKE 'profile_last_scraped_at'")
            if not cursor.fetchone():
                print("  - Adding profile_last_scraped_at to accounts...")
                with get_db_cursor() as cursor:
                    cursor.execute("ALTER TABLE accounts ADD COLUMN profile_last_scraped_at DATETIME NULL")
                    print("    [OK] Added profile_last_scraped_at")
    except Exception as e:
        print(f"    [ERROR] {e}")

    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SHOW COLUMNS FROM accounts LIKE 'profile_metric_status'")
            if not cursor.fetchone():
                print("  - Adding profile_metric_status to accounts...")
                with get_db_cursor() as cursor:
                    cursor.execute("ALTER TABLE accounts ADD COLUMN profile_metric_status VARCHAR(50) NULL")
                    print("    [OK] Added profile_metric_status")
    except Exception as e:
        print(f"    [ERROR] {e}")

    # Add view_parse_status to posts table
    print("  - Checking posts table for view_parse_status column...")
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SHOW COLUMNS FROM posts LIKE 'view_parse_status'")
            if not cursor.fetchone():
                print("  - Adding view_parse_status to posts...")
                with get_db_cursor() as cursor:
                    cursor.execute("ALTER TABLE posts ADD COLUMN view_parse_status VARCHAR(50) NULL")
                    print("    [OK] Added view_parse_status")
    except Exception as e:
        print(f"    [ERROR] {e}")

    print("\n" + "=" * 60)
    print("MIGRATIONS COMPLETE")
    print("=" * 60)
    print("\nDefault login credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("\n[IMPORTANT] Change the password immediately!")
    print("\nNext steps:")
    print("  1. cd backend")
    print("  2. pip install -r requirements.txt")
    print("  3. python run.py")
    print("=" * 60)


if __name__ == "__main__":
    run_migrations()
