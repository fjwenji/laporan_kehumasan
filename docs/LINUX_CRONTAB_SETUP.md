# ===========================================
# Mayz Monitoring - Linux Crontab Setup
# ===========================================
#
# Panduan setup cron job di Linux server DJPb
# Jalankan script ini sebagai user yang punya akses project
#
# ===========================================

# ===========================================
# 1. PERSIAPAN
# ===========================================

# Buka terminal dan cd ke project directory
cd /opt/mayz_monitoring

# Buat virtual environment
python3 -m venv .venv

# Install dependencies
source .venv/bin/activate
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Install Playwright browser
.venv/bin/playwright install chromium


# ===========================================
# 2. KONFIGURASI ENVIRONMENT
# ===========================================

# Buat file .env
cat > .env << 'EOF'
# MySQL Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=mayz_user
MYSQL_PASSWORD=YourSecurePassword123!
MYSQL_DATABASE=mayz_monitoring

# Application
APP_NAME=Mayz Monitoring
SECRET_KEY=change-this-secret-key-in-production

# Instagram Login (Wajib)
IG_LOGIN_ENABLED=true
IG_USERNAME=dummy_akun_mayz
IG_PASSWORD=PasswordDummy123!
IG_AUTH_STATE_PATH=/opt/mayz_monitoring/data/instagram/auth_state.json

# Telegram (Optional)
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Scheduler
SCHEDULER_ENABLED=true
SCHEDULER_MODE=daily
SCHEDULER_TIMES=06:00-07:00,22:00-23:00
SCHEDULER_SYNC_MODE=hot
EOF


# ===========================================
# 3. BUAT SERVICE FILE (Systemd)
# ===========================================

# Buat service file
sudo tee /etc/systemd/system/mayz-worker.service << 'EOF'
[Unit]
Description=Mayz Monitoring Worker Service
After=network.target mysql.service

[Service]
Type=simple
User=mayz
Group=mayz
WorkingDirectory=/opt/mayz_monitoring
Environment="PATH=/opt/mayz_monitoring/.venv/bin"
Environment="PYTHONPATH=/opt/mayz_monitoring"
ExecStart=/opt/mayz_monitoring/.venv/bin/python /opt/mayz_monitoring/worker/main.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/mayz/worker.log
StandardError=append:/var/log/mayz/worker_error.log

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Buat user mayz (jika belum ada)
sudo useradd -r -s /usr/sbin/nologin mayz 2>/dev/null || true

# Buat log directory
sudo mkdir -p /var/log/mayz
sudo chown mayz:mayz /var/log/mayz

# Reload systemd dan enable service
sudo systemctl daemon-reload
sudo systemctl enable mayz-worker
sudo systemctl start mayz-worker


# ===========================================
# 4. CRON JOB UNTUK SCHEDULED SCRAPING
# ===========================================

# Edit crontab
crontab -e

# Tambahkan baris berikut:

# ===========================================
# CRON SCHEDULE - Mayz Monitoring
# ===========================================

# HOT Sync - 2x sehari (06:00 dan 22:00)
# Worker loop running 24/7, tapi bisa juga pakai cron untuk spesifik scraping
0 6 * * * /opt/mayz_monitoring/.venv/bin/python /opt/mayz_monitoring/worker/main.py --once >> /var/log/mayz/cron_hot_am.log 2>&1
0 22 * * * /opt/mayz_monitoring/.venv/bin/python /opt/mayz_monitoring/worker/main.py --once >> /var/log/mayz/cron_hot_pm.log 2>&1

# Scheduler sync check setiap jam
0 * * * * cd /opt/mayz_monitoring && /opt/mayz_monitoring/.venv/bin/python -c "from src.scheduler_service import check_sync_status; print('Sync OK')" >> /var/log/mayz/scheduler_check.log 2>&1

# Log rotation check setiap hari jam 00:30
30 0 * * * find /var/log/mayz/ -name "*.log" -mtime +7 -delete


# ===========================================
# 5. SHELL SCRIPT UNTUK SCRAPING
# ===========================================

# Buat script helper
sudo tee /usr/local/bin/mayz-sync << 'SCRIPT'
#!/bin/bash
# Mayz Sync Script - Jalankan scraping manual

PROJECT_DIR="/opt/mayz_monitoring"
LOG_FILE="/var/log/mayz/mayz-sync.log"

echo "[$(date)] Mayz Sync Started" >> $LOG_FILE

cd $PROJECT_DIR
source .venv/bin/activate

# Run worker
python worker/main.py --once >> $LOG_FILE 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date)] Mayz Sync Completed Successfully" >> $LOG_FILE
else
    echo "[$(date)] Mayz Sync Failed with exit code: $EXIT_CODE" >> $LOG_FILE
fi

exit $EXIT_CODE
SCRIPT

sudo chmod +x /usr/local/bin/mayz-sync


# ===========================================
# 6. MONITORING
# ===========================================

# Check service status
sudo systemctl status mayz-worker

# Check logs
sudo tail -f /var/log/mayz/worker.log

# Manual run
sudo -u mayz /opt/mayz_monitoring/.venv/bin/python /opt/mayz_monitoring/worker/main.py


# ===========================================
# 7. LOG ROTATION
# ===========================================

# Buat logrotate config
sudo tee /etc/logrotate.d/mayz << 'EOF'
/var/log/mayz/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 mayz mayz
    sharedscripts
    postrotate
        systemctl reload mayz-worker > /dev/null 2>&1 || true
    endscript
}
EOF


# ===========================================
# 8. UPDATE DATABASE SETTINGS
# ===========================================

# Set scheduler via API atau langsung di database

# Login ke MySQL
mysql -u mayz_user -p mayz_monitoring

# Update settings
UPDATE settings SET setting_value = 'true' WHERE setting_key = 'scheduler_enabled';
UPDATE settings SET setting_value = '06:00-07:00, 22:00-23:00' WHERE setting_key = 'scheduler_times';
UPDATE settings SET setting_value = 'hot' WHERE setting_key = 'scheduler_sync_mode';
UPDATE settings SET setting_value = '12' WHERE setting_key = 'latest_max_posts_per_account';


# ===========================================
# 9. VERIFIKASI
# ===========================================

# Test worker
/opt/mayz_monitoring/.venv/bin/python /opt/mayz_monitoring/worker/main.py --once

# Test service
sudo systemctl restart mayz-worker
sudo systemctl status mayz-worker

# Check logs
tail -100 /var/log/mayz/worker.log


# ===========================================
# 10. DASHBOARD ACCESS
# ===========================================

# Backend API
sudo systemctl enable mayz-backend
sudo systemctl start mayz-backend

# Frontend (nginx config)
sudo tee /etc/nginx/sites-available/mayz << 'EOF'
server {
    listen 80;
    server_name mayz.djpb.go.id;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/mayz /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
