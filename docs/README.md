# Mayz Monitoring - Sistem Baru

Sistem monitoring publikasi Instagram DJPb dengan arsitektur modern: **React Frontend** + **FastAPI Backend** + **Standalone Worker**.

## Arsitektur

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React UI      │────▶│   FastAPI       │────▶│   MySQL DB      │
│   (Vite)        │     │   (Backend)     │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              ▲
                              │ API
                        ┌─────┴─────┐
                        │  Worker   │
                        │ (Scraper) │
                        └───────────┘
```

## Struktur Project

```
mayz_djpb/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── main.py           # FastAPI app entry
│   │   ├── config.py         # Configuration
│   │   ├── database.py      # Database connection
│   │   ├── schemas/         # Pydantic models
│   │   └── api/endpoints/   # API routes
│   ├── requirements.txt
│   ├── run.py
│   └── migrate.py
│
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/      # Reusable components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   ├── types/          # TypeScript types
│   │   └── styles/         # CSS styles
│   ├── package.json
│   └── vite.config.ts
│
├── worker/                     # Scraper Worker
│   └── main.py
│
├── src/                       # Core scraping (REUSE)
│   ├── database.py         # Database connection
│   ├── db_repository.py    # CRUD operations
│   ├── scraper.py         # Instagram scraper
│   ├── parser.py          # Data parsing
│   ├── excel_builder.py   # Excel building
│   └── notification_service.py  # Telegram notifications
│
├── legacy_backup/             # Old Streamlit files (backup)
└── MIGRATION_PLAN.md         # Migration documentation
```

## Cara Menjalankan

### 1. Backend API

```powershell
cd backend
pip install -r requirements.txt
python migrate.py   # Jalankan sekali untuk setup database
python run.py      # Start server di http://localhost:8000
```

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev       # Start dev server di http://localhost:5173
```

### 3. Worker (Scraper)

```powershell
REM Cara 1: Gunakan batch file
run_worker.bat

REM Cara 2: Langsung dari command line
cd worker
python main.py           # Worker loop (continuous)
python main.py --once    # Single job

REM Atau dari root directory
python worker/main.py
```

### 4. Scheduler Sync

```powershell
REM Sync scheduler settings ke Windows Task Scheduler
run_scheduler.bat
```

## Login Default

```
Username: admin
Password: admin123
```

⚠️ **PENTING: Ganti password admin segera setelah login!**

## Fitur

### User Dashboard
- Filter periode dan akun
- Metric cards (Akun Aktif, Total Postingan, Like, Komentar, Engagement, Views)
- Bar chart engagement per akun
- Pie chart media type
- Export Excel

### Admin Dashboard
- Node flow visualization (n8n-style)
- Job status table
- Failed items table
- Alert panel
- Worker status
- Manual job trigger

### Admin Settings (Pengaturan)
- **Telegram Settings**: Bot token, recipients, test notification
- **Scheduler Settings**: Enable/disable, interval, daily times, account limits

### Instagram Accounts Management
- Tambah/edit/hapus akun Instagram
- Import dari Excel dengan preview
- Deteksi duplicate username
- Filter berdasarkan jenis akun (Kanwil, KPPN, Pusat, Kanver Lainnya)

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/login/json` - Login (JSON)
- `GET /api/auth/me` - Get current user

### Dashboard
- `GET /api/dashboard/summary` - Dashboard summary
- `GET /api/dashboard/posts` - Posts list
- `GET /api/dashboard/charts` - Chart data
- `GET /api/dashboard/accounts` - Account filter options

### Jobs (Admin)
- `GET /api/jobs/` - List jobs
- `GET /api/jobs/node-flow` - Node workflow status
- `GET /api/jobs/failed` - Failed items
- `GET /api/jobs/worker-status` - Worker status
- `POST /api/jobs/trigger` - Trigger manual job

### Export
- `GET /api/export/excel` - Download Excel report

### Admin Settings (Telegram)
- `GET /api/admin/settings/telegram` - Get Telegram settings
- `PUT /api/admin/settings/telegram` - Update Telegram settings
- `POST /api/admin/settings/telegram/token` - Update bot token
- `GET /api/admin/settings/telegram/recipients` - List recipients
- `POST /api/admin/settings/telegram/recipients` - Add recipient
- `PUT /api/admin/settings/telegram/recipients/:id` - Update recipient
- `DELETE /api/admin/settings/telegram/recipients/:id` - Delete recipient
- `POST /api/admin/settings/telegram/recipients/:id/toggle` - Toggle recipient
- `POST /api/admin/settings/telegram/test` - Test Telegram notification

### Admin Settings (Scheduler)
- `GET /api/admin/settings/scheduler` - Get scheduler settings
- `PUT /api/admin/settings/scheduler` - Update scheduler settings
- `GET /api/admin/settings/scheduler/status` - Get scheduler status
- `POST /api/admin/settings/scheduler/sync` - Sync to Windows Task Scheduler

### Instagram Accounts
- `GET /api/admin/instagram-accounts` - List accounts
- `POST /api/admin/instagram-accounts` - Create account
- `PUT /api/admin/instagram-accounts/:id` - Update account
- `DELETE /api/admin/instagram-accounts/:id` - Delete account
- `POST /api/admin/instagram-accounts/:id/toggle` - Toggle status
- `POST /api/admin/instagram-accounts/validate-username` - Validate username
- `POST /api/admin/instagram-accounts/import-preview` - Preview Excel import
- `POST /api/admin/instagram-accounts/import-confirm` - Confirm Excel import

## Konfigurasi

### Database (.env)

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=mayz_monitoring
```

### Telegram (.env)

```env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
```

## Troubleshooting

### Database connection failed
1. Pastikan MySQL/XAMPP berjalan
2. Cek credentials di file `.env`
3. Pastikan database `mayz_monitoring` ada

### Frontend can't connect to backend
1. Pastikan backend berjalan di port 8000
2. Cek CORS settings di `backend/app/config.py`

### Worker tidak mengambil job
1. Cek tabel `scrape_jobs` di database
2. Pastikan ada job dengan status `QUEUED`

## Windows Task Scheduler Setup

Worker dapat dijadwalkan menggunakan Windows Task Scheduler untuk berjalan otomatis.

### Cara Setup

1. **Buka Task Scheduler**
   - Tekan `Win + R`, ketik `taskschd.msc`, Enter

2. **Create Basic Task**
   - Klik "Create Basic Task..."
   - Name: `Mayz_Worker_Sync_2200`
   - Description: `Mayz Worker sync at 22:00`
   - Trigger: Daily, Time: 22:00

3. **Action: Start a program**
   - Program: `C:\Users\[username]\magang\Project Kemenkeu\mayz_djpb\.venv\Scripts\python.exe`
   - Arguments: `worker\main.py`
   - Start in: `C:\Users\[username]\magang\Project Kemenkeu\mayz_djpb`

4. **Atau gunakan Sync dari Dashboard**
   - Buka Admin Dashboard > Pengaturan > Scheduler
   - Klik "Sync ke Windows Task Scheduler"
   - Task akan dibuat otomatis

### File Log Worker

Worker tidak memiliki file log default. Untuk melihat output:
- Jalankan worker di terminal untuk melihat output real-time
- Atau modifikasi worker untuk menulis ke file log

## Catatan Penting

1. **Jangan hapus folder `src/`** - berisi scraper, parser, dan notification service yang sudah berjalan dengan baik.

2. **Media type** tidak pernah tampil sebagai "Unknown" - menggunakan fallback:
   - IMAGE
   - CAROUSEL
   - REELS
   - VIDEO
   - UNCLASSIFIED_REVIEW

3. **Optional metrics** (view_count, play_count, share_count, save_count) tampil sebagai "-" jika null, bukan 0.

4. **Scraper worker** berjalan terpisah dari dashboard - dashboard hanya membaca data dari database.

## License

© 2026 DJPb - Internal Use Only
