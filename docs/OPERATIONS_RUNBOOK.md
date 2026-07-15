# Operations Runbook - Mayz Monitoring

## Mode Operasional
Mayz harus dijalankan sebagai beberapa proses terpisah:

```text
MySQL
Backend FastAPI
Frontend React/Static Preview
Worker Scraper
Scheduler/Task Scheduler
```

## Dua Device: Laptop Server Rumah dan Laptop Kerja
Gunakan satu device sebagai server sementara di rumah, lalu gunakan laptop kerja/kantor hanya sebagai client untuk membuka dashboard atau remote ke server.

Pembagian peran:
```text
Device 1 - Laptop Server Rumah
- MySQL
- Backend FastAPI
- Frontend dev/preview atau static build
- Worker scraper
- Windows Task Scheduler
- data/staging
- data/checkpoints
- logs

Device 2 - Laptop Kerja/Kantor
- Browser untuk akses dashboard
- Remote desktop/VPN/tunnel jika beda jaringan
- Tidak menjalankan worker
- Tidak menjalankan database
- Tidak menyimpan token atau staging utama
```

Checklist laptop server rumah:
1. Sleep = Never.
2. Charger terhubung.
3. IP lokal tetap jika akses masih satu jaringan.
4. MySQL menyala otomatis.
5. Backend menyala otomatis atau mudah dijalankan ulang.
6. Worker terpasang di Windows Task Scheduler.
7. Folder `data/staging`, `data/checkpoints`, dan `logs` dipantau.

## Jalankan Backend
```bash
cd backend
pip install -r requirements.txt
python run.py
```

Backend berjalan di:
```text
http://localhost:8000
```

Untuk akses dari laptop lain, backend harus bind ke `0.0.0.0` dan firewall mengizinkan port 8000.

Catatan akses dari kantor:
- Jika laptop kerja tidak satu jaringan dengan laptop server rumah, IP lokal seperti `192.168.x.x` tidak bisa diakses langsung.
- Gunakan remote desktop, VPN pribadi, atau tunnel aman sesuai kebijakan instansi.
- Untuk operasional sementara, paling aman adalah remote ke laptop server lalu buka dashboard dari mesin server.

## Jalankan Frontend
Development:
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Build/preview:
```bash
cd frontend
npm run build
npm run preview -- --host 0.0.0.0
```

Frontend berjalan di:
```text
http://localhost:5173
```

## Jalankan Worker Manual
```bash
python worker/main.py
```

Sekali jalan:
```bash
python worker/main.py --once
```

## Windows Task Scheduler untuk Worker
Tujuan Task Scheduler adalah memastikan worker hidup saat laptop/server menyala.

Rekomendasi trigger:
```text
At startup
```

Action:
```text
Program/script: C:\path\to\mayz_djpb\run_worker.bat
Start in:      C:\path\to\mayz_djpb
```

Pengaturan tambahan:
- Run whether user is logged on or not jika memungkinkan.
- Restart on failure.
- Stop task if runs longer: disabled untuk worker loop.

## Scheduler UI vs OS Scheduler
Scheduler UI mengatur jam aktif scraping. OS Scheduler menjaga worker tetap hidup.

Jangan buat banyak OS task untuk setiap jam scraping jika belum stabil. Lebih aman:
```text
Task Scheduler menjalankan worker saat startup.
Worker membaca jadwal aktif dari database.
```

## Telegram Operasional
Default Telegram:
- ON untuk ringkasan batch.
- ON untuk job failed/worker stuck.
- OFF untuk per-post alert massal.

Per-post alert hanya dipakai untuk scope kecil atau debugging.

## Monitoring Harian
Cek setiap hari:
1. Worker heartbeat masih update.
2. Job tidak stuck di RUNNING terlalu lama.
3. Tidak ada login wall streak.
4. Folder staging tidak menumpuk tanpa ingest.
5. Export triwulan memakai data yang sudah lengkap.

## Recovery
Jika laptop/server mati:
1. Nyalakan MySQL.
2. Jalankan backend.
3. Jalankan worker atau tunggu Task Scheduler.
4. Cek job RUNNING lama; ubah ke FAILED/PARTIAL jika perlu.
5. Lanjutkan batch dari checkpoint/staging.

## Batasan Laptop Server
Laptop server hanya solusi sementara. Untuk operasional jangka panjang, pindahkan ke VPS/server dengan service manager dan backup rutin.