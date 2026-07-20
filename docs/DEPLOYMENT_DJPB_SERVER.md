# Panduan Deployment - Mayz Monitoring System
## DJPb Server Setup Guide

> Dibuat: 2026-07-15
> Untuk: Tim IT DJPb / Admin Server

---

## 📋 Daftar Isi

1. [Persiapan Awal](#1-persiapan-awal)
2. [Instalasi Python & Dependencies](#2-instalasi-python--dependencies)
3. [Setup Database MySQL](#3-setup-database-mysql)
4. [Setup Environment Variables](#4-setup-environment-variables)
5. [Migrasi Database](#5-migrasi-database)
6. [Setup Akun Instagram Dummy](#6-setup-akun-instagram-dummy)
7. [Test Manual](#7-test-manual)
8. [Setup Windows Task Scheduler](#8-setup-windows-task-scheduler)
9. [Setup Worker sebagai Service](#9-setup-worker-sebagai-service)
10. [Monitoring & Troubleshooting](#10-monitoring--troubleshooting)

---

## 1. Persiapan Awal

### Requirements
- Windows Server 2016+ atau Windows 10/11 Pro
- Python 3.10 atau 3.11
- MySQL 8.0+ atau MariaDB 10.5+
- Akses Administrator
- Internet connection

### Struktur Folder yang Direkomendasikan

```
D:\mayz_monitoring\
├── backend\           # FastAPI backend
├── frontend\          # React dashboard
├── src\               # Core scraper, parser, dll
├── worker\            # Worker scraping
├── data\              # Staging, checkpoints
│   ├── staging\
│   │   ├── hot\
│   │   ├── warm\
│   │   └── cold\
│   └── checkpoints\
├── logs\              # Worker logs
├── deployment\        # Docker configs (optional)
└── mayz_sync.bat     # Worker batch file
```

---

## 2. Instalasi Python & Dependencies

### 2.1 Install Python

1. Download Python 3.11 dari https://www.python.org/downloads/
2. Install dengan opsi:
   - ✅ Add Python to PATH
   - ✅ Install pip
   - ✅ Install for all users

3. Verifikasi installation:
```powershell
python --version
pip --version
```

### 2.2 Buat Virtual Environment

```powershell
cd D:\mayz_monitoring
python -m venv .venv
```

### 2.3 Install Dependencies

```powershell
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install -r backend\requirements.txt
```

### Dependencies yang diperlukan:

```
# requirements.txt (root)
playwright>=1.40.0
mysql-connector-python>=8.0.0
python-dotenv>=1.0.0
openpyxl>=3.1.0
pandas>=2.0.0

# backend/requirements.txt
fastapi>=0.100.0
uvicorn>=0.23.0
python-multipart>=0.0.6
python-jose>=3.3.0
passlib>=1.7.4
bcrypt>=4.0.0

# Install Playwright browser
.venv\Scripts\playwright install chromium
```

---

## 3. Setup Database MySQL

### 3.1 Install MySQL (jika belum ada)

Download dari: https://dev.mysql.com/downloads/mysql/

Atau gunakan XAMPP untuk development:
https://www.apachefriends.org/download.html

### 3.2 Buat Database dan User

```sql
-- Login sebagai root
mysql -u root -p

-- Buat database
CREATE DATABASE IF NOT EXISTS mayz_monitoring
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- Buat user untuk aplikasi
CREATE USER IF NOT EXISTS 'mayz_user'@'localhost' IDENTIFIED BY 'MayzPassword123!';
GRANT ALL PRIVILEGES ON mayz_monitoring.* TO 'mayz_user'@'localhost';
FLUSH PRIVILEGES;

-- Atau untuk remote access:
CREATE USER IF NOT EXISTS 'mayz_user'@'%' IDENTIFIED BY 'MayzPassword123!';
GRANT ALL PRIVILEGES ON mayz_monitoring.* TO 'mayz_user'@'%';
FLUSH PRIVILEGES;
```

### 3.3 Verifikasi Koneksi

```powershell
.venv\Scripts\python -c "import mysql.connector; c = mysql.connector.connect(host='localhost', user='mayz_user', password='MayzPassword123!', database='mayz_monitoring'); print('OK')"
```

---

## 4. Setup Environment Variables

### 4.1 Buat File `.env`

Buat file `.env` di root project:

```env
# ============================================
# MAYZ MONITORING - Environment Configuration
# ============================================

# --- MySQL Database ---
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=mayz_user
MYSQL_PASSWORD=MayzPassword123!
MYSQL_DATABASE=mayz_monitoring

# --- Application ---
APP_NAME=Mayz Monitoring
APP_VERSION=1.0.0
SECRET_KEY=your-secret-key-change-this-in-production

# --- Instagram Login (Wajib untuk scraping stabil) ---
IG_LOGIN_ENABLED=true
IG_USERNAME=dummy_akun_mayz
IG_PASSWORD=PasswordDummy123!
IG_AUTH_STATE_PATH=data/instagram/auth_state.json

# --- Telegram Notifications (Optional) ---
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# --- Scheduler Settings ---
SCHEDULER_ENABLED=true
SCHEDULER_MODE=daily
SCHEDULER_TIMES=06:00-07:00,22:00-23:00
SCHEDULER_SYNC_MODE=hot
LATEST_MAX_POSTS_PER_ACCOUNT=12
LATEST_SYNC_INTERVAL_MINUTES=0

# --- Rate Limiting Protection ---
SKIP_SUCCESS_HOURS=6
LOGIN_WALL_COOLDOWN_MINUTES=120
LOGIN_WALL_STREAK_LIMIT=3

# --- CORS ---
CORS_ORIGINS=http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:8080
```

### 4.2 Buat Folder yang Dibutuhkan

```powershell
# Buat folder struktur
mkdir -p data\staging\hot
mkdir -p data\staging\warm
mkdir -p data\staging\cold
mkdir -p data\checkpoints
mkdir -p data\instagram
mkdir -p logs
mkdir -p exports
```

---

## 5. Migrasi Database

### 5.1 Run Migration Script

```powershell
cd D:\mayz_monitoring
.venv\Scripts\python backend\migrate.py
```

### 5.2 Output yang Diharapkan

```
============================================================
MAYZ MONITORING - DATABASE MIGRATIONS
============================================================

[1/5] Testing database connection...
  [OK] Koneksi database berhasil

[2/5] Creating tables...
  - Creating users table... [OK]
  - Creating job_failed_items table... [OK]
  - Creating export_logs table... [OK]
  - Creating alerts table... [OK]
  [OK] Found X tables

[3/5] Verifying existing tables...
  [OK] Found X tables:
      - accounts
      - posts
      - scrape_jobs
      - settings
      - users
      - etc...

[4/5] Creating default admin user...
  [OK] Admin user created (username: admin, password: admin123)

[5/5] Checking for missing columns...
  [OK] Added followers_count
  [OK] Added following_count
  [OK] Added profile_posts_count
  ...

============================================================
MIGRATIONS COMPLETE
============================================================
```

### 5.3 Default Login

```
Username: admin
Password: admin123

⚠️ GANTI PASSWORD SEGERA SETELAH LOGIN PERTAMA KALI!
```

---

## 6. Setup Akun Instagram Dummy

### 6.1 Persiapan Akun Dummy

1. Buat akun Instagram baru atau gunakan akun yang sudah ada
2. Pastikan akun sudah:
   - ✅ Email verified
   - ✅ Phone number verified
   - ✅ Tidak ada 2FA aktif (atau siapkan bypass)
   - ✅ Tidak dalam keadaan banned/restricted

### 6.2 Setup di Environment

```env
IG_LOGIN_ENABLED=true
IG_USERNAME=your_dummy_account
IG_PASSWORD=your_password
```

### 6.3 First Login (Otentik)

 Jalankan script test login SEKALI:

```powershell
.venv\Scripts\python -c "
import sys
sys.path.insert(0, '.')
from src.scraper import ensure_instagram_login, create_context, sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = create_context(browser)
    try:
        # Ini akan buka browser dan minta login
        # Ikuti instruksi di browser
        ensure_instagram_login(context)
        print('Login berhasil! Session disimpan.')
    except Exception as e:
        print(f'Login gagal: {e}')
    finally:
        browser.close()
"
```

### 6.4 Verifikasi Session

Setelah login berhasil, file `data/instagram/auth_state.json` akan dibuat.
File ini menyimpan session sehingga tidak perlu login ulang.

---

## 7. Test Manual

### 7.1 Test Worker Sekali Jalan

```powershell
.venv\Scripts\python worker\main.py --once
```

Expected output:
```
[INFO] Database connected: Koneksi database berhasil
[INFO] No queued job. Worker exiting (--once mode).
```

### 7.2 Test Scraping 1 Akun

```powershell
# Buat job test melalui backend API
.venv\Scripts\python -c "
import sys
sys.path.insert(0, '.')
from src.database import get_db_cursor
from src.db_repository import create_scrape_job

# Buat job test
success, job_id = create_scrape_job(
    job_id='TEST_20260715',
    job_type='LATEST_SYNC',
    trigger_type='MANUAL'
)
print(f'Job created: {job_id}')
"
```

### 7.3 Jalankan Worker

```powershell
.venv\Scripts\python worker\main.py
```

Worker akan memproses job dan update database.

---

## 8. Setup Windows Task Scheduler

### 8.1 Opsi A: Worker Loop (Recommended)

Worker loop berjalan terus dan scheduler internally controlled.

```powershell
# Buat scheduled task untuk start worker saat startup
schtasks /create /tn "Mayz_Worker_Startup" /tr "D:\mayz_monitoring\.venv\Scripts\python.exe D:\mayz_monitoring\worker\main.py" /sc ONSTART /ru SYSTEM /f
```

### 8.2 Opsi B: Scheduled Jobs (Lebih Kontrol)

```powershell
# Hot sync - 2x sehari
schtasks /create /tn "Mayz_HOT_AM" /tr "D:\mayz_monitoring\mayz_sync.bat" /sc DAILY /st 06:00 /f
schtasks /create /tn "Mayz_HOT_PM" /tr "D:\mayz_monitoring\mayz_sync.bat" /sc DAILY /st 22:00 /f
```

### 8.3 Auto-sync Scheduler (Recommended)

Setup sync otomatis dari database ke Task Scheduler:

```powershell
# Jalankan sync saat startup
schtasks /create /tn "Mayz_Scheduler_Sync" /tr "D:\mayz_monitoring\run_scheduler.bat" /sc ONSTART /ru SYSTEM /f

# Atau harian untuk verify sync
schtasks /create /tn "Mayz_Scheduler_Sync_Daily" /tr "D:\mayz_monitoring\run_scheduler.bat" /sc DAILY /st 05:55 /f
```

---

## 9. Setup Worker sebagai Service

### 9.1 Windows Service (NSSM)

Download NSSM: https://nssm.cc/download

```powershell
# Install service
nssm install MayzWorker "D:\mayz_monitoring\.venv\Scripts\python.exe" "D:\mayz_monitoring\worker\main.py"

# Set startup type
nssm set MayzWorker Start SERVICE_AUTO_START

# Set working directory
nssm set MayzWorker AppDirectory "D:\mayz_monitoring"

# Set environment
nssm set MayzWorker AppEnvironmentExtra "PYTHONPATH=D:\mayz_monitoring"

# Start service
nssm start MayzWorker
```

### 9.2 Verifikasi Service

```powershell
nssm status MayzWorker
# atau
sc query MayzWorker
```

---

## 10. Monitoring & Troubleshooting

### 10.1 Log Files

```
D:\mayz_monitoring\logs\
├── worker.log          # Worker activity
├── worker_startup.log # Startup records
└── worker_loop.log    # Loop output
```

### 10.2 Health Check

```powershell
# Check database
.venv\Scripts\python -c "from src.database import test_connection; print(test_connection())"

# Check scheduler
.venv\Scripts\python -c "from src.scheduler_service import check_sync_status; import json; print(json.dumps(check_sync_status(), indent=2, default=str))"

# Check recent jobs
.venv\Scripts\python -c "from src.db_repository import get_recent_jobs; jobs = get_recent_jobs(5); [print(f\"{j['job_id']}: {j['status']}\") for j in jobs]"
```

### 10.3 Common Issues

#### Issue: Login Wall Beruntun
```
[SCRAPER] Login wall streak limit reached (3). Stopping batch.
```
**Solusi:** Tunggu 2 jam, kemudian coba lagi. Instagram rate limit self-healing.

#### Issue: Database Connection Failed
```
Error: Could not connect to MySQL
```
**Solusi:** 
1. Cek MySQL service running: `services.msc`
2. Cek credentials di `.env`
3. Cek firewall

#### Issue: Task Scheduler Access Denied
```
Error: Access is denied
```
**Solusi:** Jalankan Command Prompt sebagai Administrator

#### Issue: Playwright Browser Error
```
Error: Executable doesn't exist
```
**Solusi:** Install browser: `.\.venv\Scripts\playwright install chromium`

### 10.4 Dashboard Monitoring

Akses dashboard untuk monitoring:
```
http://SERVER_IP:8080
```

Pages penting:
- `/admin` - System status, scheduler config
- `/jobs` - Job history, running jobs
- `/dashboard` - Data overview
- `/settings` - Telegram, scheduler settings

---

## 📞 Kontak & Support

Jika ada masalah teknis:
1. Cek log files di `logs/`
2. Cek status di dashboard `/admin`
3. Dokumentasi lengkap di `docs/`

---

## ✅ Checklist Deployment

```markdown
## Pre-Deployment
- [ ] Python 3.10+ installed
- [ ] MySQL 8.0+ installed & configured
- [ ] Project files copied to server
- [ ] Virtual environment created
- [ ] Dependencies installed

## Configuration
- [ ] .env file created with correct credentials
- [ ] MySQL database and user created
- [ ] Database migration run successfully
- [ ] Default admin password changed
- [ ] Instagram dummy account configured

## Testing
- [ ] Database connection test passed
- [ ] Worker --once test passed
- [ ] Test scraping 1-3 accounts passed
- [ ] Telegram notification tested (if enabled)

## Production
- [ ] Windows Task Scheduler configured
- [ ] Worker auto-start configured
- [ ] Backup strategy in place
- [ ] Monitoring dashboard accessible
- [ ] Log rotation configured
```

---

**Document Version:** 1.0.0
**Last Updated:** 2026-07-15
**Author:** Claude Code (AI Assistant)
