# Revision System Notes

Perubahan sistem yang ditambahkan secara aman:

## 1. Worker Internal Scheduler
- Worker loop sekarang dapat membuat job otomatis saat `scheduler_enabled=true`.
- Untuk Docker Local Demo, backend tidak lagi memaksa Windows Task Scheduler.
- Endpoint sync scheduler di Docker akan memberi status sukses dengan mode internal worker.
- Scheduler tetap aman karena tidak aktif kalau `scheduler_enabled=false`.
- Job scheduler dibatasi maksimal 34 akun dan memakai daftar akun eksplisit per job.

Setting yang dipakai:
- `scheduler_enabled=true/false`
- `scheduler_mode=interval|daily`
- `latest_sync_interval_minutes`
- `scheduler_times` format `HH:mm-HH:mm`
- `scheduler_account_limit` atau fallback `latest_max_posts_per_account`
- `scheduler_sync_mode=hot|warm|cold`

## 2. Optional Instagram Dummy Login
- Scraper mendukung login opsional memakai akun dummy dari environment.
- Session disimpan ke `data/instagram/auth_state.json` dan dipakai ulang.
- Password tidak dicetak di log.
- Jika muncul challenge/checkpoint/verifikasi, scraping dihentikan dengan error jelas.

Environment variable:
- `IG_LOGIN_ENABLED=true|false`
- `IG_USERNAME=<dummy username>`
- `IG_PASSWORD=<dummy password>`
- `IG_AUTH_STATE_PATH=/app/data/instagram/auth_state.json`

Catatan:
- Jangan pakai akun pribadi.
- Sistem tidak bypass CAPTCHA/2FA/checkpoint.

## 3. Hot / Warm / Cold Mode
- Trigger job sekarang dapat menerima `sync_mode`.
- Mode menentukan rentang scraping, jumlah post, scroll, dan lokasi staging JSONL.

Mode:
- `hot`: data terbaru, sekitar 3 hari, staging `data/staging/hot/`
- `warm`: data 14 hari, staging `data/staging/warm/`
- `cold`: data historis/backfill, staging `data/staging/cold/`

Contoh request:
```json
{
  "job_type": "LATEST_SYNC",
  "usernames": ["djpbaceh"],
  "sync_mode": "hot",
  "dry_run": true
}
```

## Safety
- Jangan pakai default trigger saat active accounts masih 217.
- Pakai `usernames` atau `account_ids` eksplisit.
- Scheduler internal tidak akan membuat job jika masih ada job `QUEUED` atau `RUNNING`.
