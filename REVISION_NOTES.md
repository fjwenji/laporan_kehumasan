# Mayz DJPb Production - Revision Notes

## Fokus revisi
- Perbaikan bug worker yang bisa membuat job menggantung.
- Trigger job lebih aman agar tidak tidak sengaja memproses semua akun aktif.
- Worker `--once` sekarang menghormati account selection per job.
- UI polish ringan untuk login illustration, Export Excel, dan copy halaman Pengaturan.
- Pembersihan struktur paket dari generated files sebelum zip.

## Perubahan penting

### Worker
- `worker/main.py` dirapikan dan dipadatkan.
- Query `complete_job()` diperbaiki. Sebelumnya field `total_accounts` dan `total_posts_found` dobel di SQL sehingga update statistik job berisiko gagal.
- Logic pemilihan akun dibuat konsisten untuk loop mode dan `--once` mode.
- Job-specific usernames dari `settings.job_accounts_{job_id}` dipakai di semua mode yang relevan.
- JSONL staging tetap ditulis sebelum upsert DB.
- Notifikasi Telegram tetap mengikuti setting lama dan tidak diaktifkan otomatis.

### Trigger job
- `backend/app/api/endpoints/jobs.py` mendukung explicit `account_ids`, `usernames`, `account_limit`, dan `dry_run`.
- Default trigger diblokir kalau akun aktif lebih dari 34 kecuali request menyertakan `allow_all_active=true`.
- Response trigger punya informasi `selected_accounts`, `blocked`, `reason`, dan `job_created`.

### Frontend
- Header Pengaturan diubah menjadi bahasa Indonesia:
  - Title: `Pengaturan`
  - Subtitle: `Kelola konfigurasi sistem dan preferensi aplikasi.`
- Login illustration diperbesar sedikit, dibuat lebih center secara visual, dan diberi hover interaction halus.
- Export Excel memakai layout dua kolom agar sisi kanan tidak kosong di desktop.

## Validasi yang dilakukan
- `python -m compileall -q backend src worker` berhasil.
- `npx tsc --noEmit` berhasil.
- `npm run build` belum bisa divalidasi di sandbox karena `node_modules` dari zip tidak membawa optional dependency Rollup Linux (`@rollup/rollup-linux-x64-gnu`). Jalankan `npm ci` atau Docker build di local untuk validasi build penuh.

## Catatan operasional
- Jangan pakai default trigger saat active accounts masih 217.
- Gunakan explicit `usernames` atau `account_ids` untuk job scraping.
- Scheduler auto-scraping tetap jangan diaktifkan sebelum scope job aman.
- Folder `node_modules`, `__pycache__`, logs, dan debug output tidak disertakan di paket revisi.
