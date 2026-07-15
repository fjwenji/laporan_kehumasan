# Telegram Notification Policy

## Prinsip
Telegram dipakai untuk memberi sinyal operasional, bukan membanjiri grup dengan semua detail scraping.

## Default Notifikasi
| Event | Default | Format |
|---|---|---|
| Hot batch selesai | ON | Ringkasan batch |
| Warm batch selesai | OFF/harian | Ringkasan harian |
| Cold batch selesai | ON | Ringkasan backfill |
| Post baru per post | OFF | Detail hanya jika scope kecil |
| Job failed | ON | Alert error |
| Worker stuck/offline | ON | Alert kritis |

## Format Ringkasan Batch
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

## Format Detail Post Opsional
```text
Mayz Monitoring Alert

Username Instagram : @djpbntb
Unit               : Kanwil DJPb Provinsi Nusa Tenggara Barat
Status             : Postingan baru terdeteksi
Tanggal Posting    : 18/06/2026 05:23
Media Type         : image
Engagement         : Like: 22 | Komentar: 0

Caption Ringkas:
Caption dipotong maksimal 180-220 karakter...

Link: https://www.instagram.com/p/xxxx/

Segera cek dashboard Mayz untuk validasi data terbaru.
```

## Anti-Spam Rule
1. Jangan kirim cold backfill per postingan.
2. Jangan kirim ulang notifikasi untuk shortcode yang sama.
3. Gunakan `notification_logs` untuk deduplicate pesan.
4. Batasi summary maksimal per batch/window.
5. Kirim error kritis segera, tapi gunakan cooldown untuk error berulang.
