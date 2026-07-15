# Migrasi Mayz Monitoring - Dari Streamlit ke React + FastAPI

## Status: COMPLETED 

Semua komponen utama telah diimplementasi dan file Streamlit lama sudah dipindahkan ke `legacy_backup/`.

---

## Cara Run Sistem

### 1. Backend API (FastAPI)

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run migrations (create users table, etc)
python migrate.py

# Start server
python run.py
# Atau: uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Backend akan berjalan di: http://localhost:8000

### 2. Frontend (React + Vite)

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend akan berjalan di: http://localhost:5173

### 3. Scraper Worker (Standalone)

```bash
cd worker

# Run worker (continuous loop)
python main.py

# Run single job
python main.py --once
```

### 4. Database Migrations

```bash
cd backend
python migrate.py
```

Ini akan membuat tabel baru:
- `users` - User authentication
- `job_failed_items` - Failed scraping items
- `export_logs` - Export history
- `alerts` - Alerts/notifications

Dan menambahkan kolom worker ke tabel `scrape_jobs`.

---

## Default Login

```
Username: admin
Password: admin123
```

**PENTING: Ganti password admin segera setelah login!**

---

## Struktur Folder

```
mayz_djpb/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── main.py           # FastAPI app
│   │   ├── config.py         # Configuration
│   │   ├── database.py      # Database connection
│   │   ├── schemas/        # Pydantic models
│   │   └── api/endpoints/   # API routes
│   ├── requirements.txt
│   ├── run.py
│   └── migrate.py
│
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/      # Reusable components
│   │   ├── pages/          # Page components
│   │   ├── services/      # API services
│   │   ├── types/         # TypeScript types
│   │   └── styles/        # CSS styles
│   ├── package.json
│   └── vite.config.ts
│
├── worker/                    # Scraper Worker
│   └── main.py
│
├── src/                       # Existing code (REUSE)
│   ├── database.py         # Database connection
│   ├── db_repository.py    # CRUD operations
│   ├── scraper.py         # Core scraping
│   ├── parser.py          # Data parsing
│   ├── excel_builder.py   # Excel building
│   ├── config.py          # Configuration
│   └── notification_service.py  # Telegram notifications
│
├── legacy_backup/             # Old Streamlit files (backup)
└── backup_old_files.py       # Script to backup old files
```

---

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/login/json` - Login (JSON)
- `GET /api/auth/me` - Get current user
- `POST /api/auth/register` - Register user (admin)
- `GET /api/auth/users` - List users (admin)

### Dashboard
- `GET /api/dashboard/summary` - Dashboard summary
- `GET /api/dashboard/posts` - Posts list
- `GET /api/dashboard/charts` - Chart data
- `GET /api/dashboard/accounts` - Account filter options

### Jobs (Admin)
- `GET /api/jobs/` - List jobs
- `GET /api/jobs/current` - Current running job
- `GET /api/jobs/node-flow` - Node workflow status
- `GET /api/jobs/failed` - Failed items
- `GET /api/jobs/worker-status` - Worker status
- `GET /api/jobs/alerts` - Recent alerts
- `POST /api/jobs/trigger` - Trigger manual job

### Export
- `GET /api/export/excel` - Download Excel report

---

## Fitur Dashboard User

1. Login dengan autentikasi JWT
2. Filter periode (tanggal mulai - selesai)
3. Filter akun
4. Metric cards:
   - Akun Aktif
   - Total Postingan
   - Total Like
   - Total Komentar
   - Total Engagement
   - Total Views
5. Komposisi Media Type:
   - IMAGE
   - CAROUSEL
   - REELS
   - VIDEO
   - UNCLASSIFIED_REVIEW (bukan "Unknown")
6. Charts interaktif:
   - Bar chart engagement per akun
   - Donut chart media type
   - Bar chart postingan per akun
7. Export Excel dengan multiple sheets

---

## Fitur Admin Dashboard

1. Worker status (alive/dead)
2. Node workflow visualization (n8n-style)
3. Job list dengan status
4. Failed items dengan error reason
5. Alerts panel
6. Manual job trigger

---

## Checklist Testing

### Backend
- [ ] `POST /api/auth/login/json` - Login berhasil
- [ ] `GET /api/auth/me` - Ambil user info
- [ ] `GET /api/dashboard/summary` - Summary data
- [ ] `GET /api/dashboard/posts` - Posts data
- [ ] `GET /api/dashboard/charts` - Chart data
- [ ] `GET /api/export/excel` - Download Excel
- [ ] `GET /api/jobs/` - Job list
- [ ] `POST /api/jobs/trigger` - Trigger job

### Frontend
- [ ] Login page responsive di mobile
- [ ] Redirect ke dashboard setelah login
- [ ] Metric cards tampil dengan benar
- [ ] Charts berubah saat ganti periode
- [ ] Export Excel berfungsi
- [ ] Admin node flow visible
- [ ] Mobile hamburger menu works

### Integration
- [ ] Scraper worker terpisah dari dashboard
- [ ] Telegram notification still works
- [ ] Job heartbeat updates
- [ ] Failed items logged correctly

---

## File Lama untuk Di-backup

Jalankan script backup sebelum hapus file lama:

```bash
python backup_old_files.py
```

Atau backup manual folder berikut:
- `app.py`
- `pages/`
- `worker_scraper.py`
- `mayz.service`
- `setup_server.sh`
- `run_app.bat`
- `setup_cron.bat`

**JANGAN HAPUS folder `src/`** - berisi logic yang direuse.

---

## Troubleshooting

### Database connection failed
1. Pastikan MySQL berjalan
2. Cek `.env` dengan kredensial yang benar
3. Pastikan database `mayz_monitoring` ada

### Frontend tidak bisa connect ke backend
1. Pastikan backend berjalan di port 8000
2. Cek CORS settings di `backend/app/config.py`
3. Pastikan proxy Vite ke backend sudah benar

### Worker tidak mengambil job
1. Cek tabel `scrape_jobs` di database
2. Pastikan ada job dengan status `QUEUED`
3. Cek apakah ada job `RUNNING` sudah ada

---

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
