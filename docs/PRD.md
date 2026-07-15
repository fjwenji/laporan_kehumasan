# PRD - Mayz Monitoring System

## 1. Ringkasan
Mayz Monitoring System adalah aplikasi internal DJPb untuk monitoring publikasi Instagram akun DJPb/Kanwil/KPPN/Kanver. Sistem ini terdiri dari dashboard React, backend FastAPI, database MySQL, worker scraping Playwright, Telegram alert, dan export Excel berdasarkan periode.

Status project sudah masuk tahap **siap scraping operasional**, bukan sekadar testing UI. Fokus maintenance ke depan adalah menjaga scraping stabil, tidak duplikatif, tidak membebani database, dan tetap aman dari rate limit/login wall Instagram.

## 2. Prinsip Utama
1. React dashboard tidak boleh menjalankan scraping berat.
2. Worker berjalan terpisah dari frontend/backend.
3. Export Excel mengambil data dari database, bukan scraping ulang.
4. JSONL staging adalah penampung sementara, bukan pengganti database utama.
5. Database tetap menjadi source of truth untuk dashboard, export, job monitoring, dan audit.
6. Scraping historis harus dicicil dengan batch, checkpoint, dan retry.
7. Telegram tidak boleh spam per postingan; default notifikasi adalah ringkasan per job/batch.
8. Parser Instagram, normalisasi media type, export yang sudah stabil, dan desain web yang sudah benar tidak boleh diubah tanpa alasan teknis jelas.

## 3. Role Pengguna
| Role | Kebutuhan |
|---|---|
| User/Senior | Lihat dashboard ringkas, pilih periode, export Excel, cek status data. |
| Admin | Kelola akun Instagram, Telegram, scheduler, job monitoring, batch/customize data. |
| Worker | Memproses scraping background, menulis staging, ingest database, update heartbeat, kirim alert. |

## 4. Arsitektur Sistem
```text
React Frontend
    ↓
FastAPI Backend
    ↓
MySQL Database
    ↑
Worker Scraper + Scheduler
    ↓
JSONL Staging
    ↓
Validator + Deduplicator + Batch Upsert
    ↓
Telegram Summary Alert
```

Folder utama:
```text
backend/    FastAPI API
frontend/   React + TypeScript + Vite
src/        Core scraper, parser, export, repository, notification
worker/     Worker loop terpisah
data/       Master data, staging, checkpoints
docs/       Dokumentasi operasional dan maintenance
```

## 5. Pipeline Scraping Hot/Warm/Cold
Pipeline baru harus memisahkan data berdasarkan kebutuhan bisnis dan risiko scraping.

| Tipe | Fungsi | Rentang | Frekuensi | Telegram | Output Awal |
|---|---|---:|---|---|---|
| Hot | Deteksi postingan baru dan update dashboard cepat | 1-3 hari terakhir | beberapa kali sehari | ringkasan batch | JSONL staging + DB upsert cepat |
| Warm | Update engagement postingan terbaru | 7-14 hari terakhir | harian/malam | hanya ringkasan jika perlu | JSONL staging + DB upsert |
| Cold | Backfill historis untuk laporan bulanan/triwulan | per bulan/per akun | dicicil background | off default | JSONL staging, preview, ingest batch |

Catatan penting: jangan menerjemahkan kebutuhan mentor menjadi scrape 1 bulan penuh untuk 34 akun setiap hari. Itu boros, memperbesar risiko login wall, dan mengulang data yang sudah ada. Gunakan hot untuk data terbaru, warm untuk update metrik, dan cold untuk histori.

## 6. Customize Data / Bulk Scraping
Fitur baru yang direkomendasikan adalah halaman **Customize Data** atau **Bulk Scraping**. Fitur ini tidak mengganti dashboard/export lama, tetapi menjadi workflow khusus untuk permintaan data historis.

Workflow:
```text
Pilih scope akun
↓
Pilih periode
↓
Cek coverage data
↓
Buat batch scraping jika data belum lengkap
↓
Scrape ke JSONL staging
↓
Preview tabel sementara dari JSONL
↓
Validasi dan deduplicate
↓
Ingest/upsert ke database
↓
Export Excel
```

Scope akun:
- Semua akun
- Kanwil
- KPPN
- Pusat
- Kanver
- Custom akun, contoh hanya `djpbaceh`

Preset periode:
- Harian
- Mingguan
- Bulanan
- Triwulan I, II, III, IV
- Semester
- Custom date range

Untuk kebutuhan laporan triwulan, admin memilih akun/scope dan periode triwulan. Sistem mengecek data yang sudah ada. Jika belum lengkap, sistem membuat cold batch per bulan/per akun, bukan scraping besar tanpa kontrol.

## 7. Urutan Zona Waktu Scraping
Mentor meminta urutan scraping berdasarkan zona waktu untuk mengurangi miskomunikasi laporan postingan. Batch planner harus mendukung prioritas berikut:

```text
1. WIT
2. WITA
3. WIB
```

Alasan operasional: akun wilayah timur diproses lebih dulu, dilanjutkan wilayah tengah, lalu wilayah barat. Ini membantu laporan harian mengikuti konteks waktu lokal masing-masing wilayah.

Setiap akun sebaiknya memiliki metadata `timezone_region`:
```text
WIT  = UTC+9
WITA = UTC+8
WIB  = UTC+7
```

Urutan scraping membantu operasional, tetapi laporan tetap harus menyimpan waktu posting dengan jelas:
- `posted_at_utc`
- `posted_at_local`
- `timezone_region`

Jika schema belum mendukung tiga kolom tersebut, minimal simpan `posted_at` konsisten dan tampilkan catatan zona waktu pada report.

## 8. JSONL Staging
JSONL staging dipakai agar scraping aman dicicil, tahan gagal, bisa retry, dan tidak langsung membebani database.

Struktur folder:
```text
data/staging/
├── hot/
│   └── YYYY-MM-DD/
├── warm/
│   └── YYYY-MM/
└── cold/
    └── YYYY-MM/
```

Format nama file:
```text
username_YYYYMMDD_YYYYMMDD.jsonl
```

Contoh:
```text
data/staging/cold/2026-01/djpbaceh_20260101_20260131.jsonl
data/staging/hot/2026-07-08/djpbntb_20260708_20260708.jsonl
```

Format minimal per baris:
```json
{"batch_id":"cold_202601_djpbaceh","batch_type":"COLD","username":"djpbaceh","unit_name":"Kanwil DJPb Provinsi Aceh","post_url":"https://www.instagram.com/p/xxxx/","shortcode":"xxxx","caption":"...","posted_at":"2026-01-10 09:00","media_type_normalized":"image","like_count":10,"comment_count":1,"view_count":null,"scraped_at":"2026-07-08T10:00:00","source":"instagram_web"}
```

Aturan:
1. Satu baris adalah satu post.
2. Jangan gunakan satu file JSON array besar untuk proses panjang.
3. Jika proses gagal di tengah, baris yang sudah tertulis tetap aman.
4. File staging harus bisa dibaca ulang untuk preview dan ingest.
5. File staging harus punya batch_id agar audit jelas.

## 9. Deduplicate dan Upsert
Identitas utama post adalah `shortcode` atau `post_url`.

Aturan:
- Jika post belum ada di database, insert.
- Jika post sudah ada, update metrik seperti like, comment, view, caption, media type jika ada data lebih baru.
- Jangan duplicate hanya karena post muncul dari akun collab.
- Untuk collab post, idealnya satu post utama bisa terkait ke banyak akun melalui tabel relasi.

Rekomendasi schema lanjutan:
```text
posts
- id
- shortcode unique
- post_url
- caption
- posted_at
- media_type_normalized
- like_count
- comment_count
- view_count
- last_scraped_at

post_accounts
- id
- post_id
- username
- relation_type owner/collaborator/observed
```

Jika schema saat ini belum dipisah seperti itu, jangan ubah langsung. Tambahkan migration hanya setelah ada approval.

## 10. Checkpoint dan Batch Status
Agar backfill Januari 2026 sampai sekarang bisa selesai tanpa mengulang dari nol, sistem wajib punya checkpoint.

Minimal status batch:
```text
QUEUED
RUNNING
STAGED
VALIDATED
INGESTED
PARTIAL_FAILED
FAILED
SKIPPED_DUPLICATE
```

Rekomendasi file checkpoint:
```text
data/checkpoints/backfill_state.json
```

Rekomendasi tabel lanjutan:
```text
scrape_batches
- id
- batch_id
- batch_type HOT/WARM/COLD
- username
- start_date
- end_date
- timezone_region
- status
- jsonl_path
- total_found
- total_valid
- total_duplicate
- total_inserted
- total_updated
- failed_count
- attempt
- started_at
- finished_at
- error_message
```

## 11. Telegram Alert Policy
Telegram tidak boleh mengirim satu pesan untuk setiap postingan baru secara default, karena akan membuat grup overload.

Default yang disarankan:
| Event | Default | Keterangan |
|---|---|---|
| Hot batch selesai | ON | Kirim ringkasan jumlah akun, post baru, updated, failed. |
| Postingan baru per post | OFF | Bisa diaktifkan hanya untuk scope kecil/debug. |
| Job gagal | ON | Kirim jika job failed atau failed_count melewati threshold. |
| Worker stuck/offline | ON | Kirim jika heartbeat tidak update dalam batas waktu. |
| Cold backfill selesai | ON ringkas | Kirim summary, bukan daftar semua postingan. |
| Cold per post | OFF | Tidak boleh spam historis. |

Contoh format ringkasan:
```text
Mayz Monitoring Summary

Periode Proses : 08/07/2026 08:00 - 11:00
Tipe Job       : HOT
Akun diproses  : 34
Postingan baru : 18
Postingan update: 42
Gagal diproses : 2

Catatan:
2 akun perlu retry karena timeout/login wall.

Cek dashboard Mayz untuk detail.
```

Format detail per post tetap boleh tersedia untuk mode khusus, tetapi tidak menjadi default.

## 12. Scheduler dan Worker Operasional
Worker harus hidup terus. Scheduler UI mengatur kapan worker boleh menjalankan batch, bukan menggantikan worker.

Mode yang disarankan:
```text
Windows Task Scheduler / service manager
    ↓ memastikan worker hidup saat startup
Worker loop
    ↓ membaca setting scheduler dari DB
Batch planner
    ↓ membuat/mengambil job
Scraper
    ↓ menulis staging dan ingest
```

Jangan membuat banyak OS task untuk setiap rentang jam jika belum stabil. Untuk sementara, cukup satu task yang menjalankan worker saat startup. Worker membaca jadwal aktif dari database.

## 13. Setup Dua Device: Laptop Server Rumah dan Laptop Kerja
Untuk tahap awal, gunakan dua device dengan peran yang jelas.

```text
Device 1: Laptop Server Rumah
├── MySQL
├── Backend FastAPI
├── Frontend dev/preview atau static build
├── Worker scraping
├── Scheduler/Windows Task Scheduler
├── JSONL staging
├── checkpoints
└── logs

Device 2: Laptop Kerja/Kantor
└── Browser untuk akses dashboard / remote ke laptop server
```

Laptop server rumah adalah mesin yang harus tetap menyala. Laptop kerja tidak perlu menjalankan worker, scraper, backend, database, atau menyimpan staging utama. Laptop kerja cukup dipakai untuk membuka dashboard, monitoring status, dan pekerjaan harian.

Syarat laptop server rumah:
1. Sleep dimatikan.
2. Charger selalu terhubung.
3. IP lokal dibuat tetap untuk akses satu jaringan.
4. Windows Update restart otomatis dikendalikan.
5. MySQL, backend, dan worker mudah dinyalakan ulang atau otomatis saat startup.
6. Worker dipasang di Task Scheduler `At startup`.
7. Folder `data/staging`, `data/checkpoints`, dan `logs` dipantau harian.

Contoh akses dari laptop kerja ketika masih satu jaringan dengan laptop server:
```text
http://IP-LAPTOP-SERVER:5173
http://IP-LAPTOP-SERVER:8000/docs
```

Jika laptop kerja berada di kantor dan laptop server berada di rumah, IP lokal `192.168.x.x` tidak bisa diakses langsung. Opsi sementara:
- remote desktop ke laptop server
- VPN pribadi
- tunnel aman seperti Cloudflare Tunnel/Tailscale sesuai kebijakan instansi

Batasan: jika laptop server rumah mati, worker berhenti. Untuk production sebenarnya, pindahkan ke VPS/server dengan service manager seperti systemd atau Windows Service.

## 14. Entry Point dan Cara Run
Frontend development:
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Frontend build:
```bash
cd frontend
npm run build
npm run preview -- --host 0.0.0.0
```

Backend:
```bash
cd backend
pip install -r requirements.txt
python run.py
```

Worker manual:
```bash
python worker/main.py
```

Worker sekali jalan untuk Task Scheduler:
```bash
python worker/main.py --once
```

Windows helper:
```text
run_all.bat        development lokal
run_worker.bat     worker loop
run_scheduler.bat  sync/check scheduler
```

## 15. Struktur Asset Frontend
Asset frontend dipusatkan di:
```text
frontend/public/assets/images/
├── logo/
│   ├── djpb_logo.png
│   └── favicon.ico
└── login/
    ├── login_page.jpg
    └── login_illustration.png
```

Aturan:
- Jangan edit `frontend/dist`.
- Jangan pakai asset dari root `assets/` untuk UI frontend.
- Asset Vite harus berada di `frontend/public`.

## 16. Batasan Maintenance untuk Agent
Jangan lakukan tanpa instruksi eksplisit:
1. Rewrite project dari nol.
2. Mengubah desain login/dashboard/settings/export yang sudah benar.
3. Mengubah parser Instagram yang sudah stabil.
4. Mengubah media type normalized tanpa bukti baru.
5. Mengubah export Excel yang sudah benar secara besar-besaran.
6. Menjalankan scraping besar untuk validasi UI.
7. Menyimpan token Telegram di frontend/localStorage.
8. Mengubah NULL menjadi 0 untuk view_count.
9. Menghapus file/folder tanpa daftar dan alasan.
10. Membuat dummy production data.

## 17. Acceptance Operasional
Sistem dianggap siap scraping jika:
1. Worker bisa hidup terus dan update heartbeat.
2. Scheduler UI jelas membedakan worker online, scheduler aktif, dan sinkronisasi OS/server.
3. Hot job bisa memproses data terbaru tanpa spam Telegram.
4. Cold job bisa backfill per bulan/per akun ke JSONL staging.
5. Data staging bisa dipreview sebelum masuk database.
6. Deduplicate memakai shortcode/post_url.
7. Ingest memakai batch upsert.
8. Job gagal bisa retry dari checkpoint.
9. Telegram default mengirim ringkasan batch, bukan per post.
10. Export triwulan bisa mengambil data dari database setelah coverage lengkap.
11. Dashboard dan export tidak scraping ulang.
12. `/login`, `/dashboard`, `/admin`, `/accounts`, `/export`, `/settings`, `/jobs` tidak blank.
