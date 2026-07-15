# Scraping Pipeline - Hot/Warm/Cold dan JSONL Staging

## Tujuan
Dokumen ini menjadi pegangan implementasi pipeline scraping Mayz agar scraping bisa berjalan stabil, bisa dicicil, tidak duplikatif, dan tidak langsung membebani database.

## Alur Utama
```text
Request data/customize period
→ Batch planner
→ Worker scraper
→ JSONL staging
→ Preview/temporary table
→ Validator + deduplicator
→ Batch upsert database
→ Dashboard / Export / Telegram summary
```

## Hot Job
Digunakan untuk monitoring terbaru.

- Rentang: 1 sampai 3 hari terakhir.
- Tujuan: mendeteksi post baru dan update dashboard cepat.
- Telegram: ringkasan batch, bukan satu pesan per post.
- Ingest: boleh langsung setelah JSONL valid.

## Warm Job
Digunakan untuk update engagement terbaru.

- Rentang: 7 sampai 14 hari terakhir.
- Tujuan: update like/comment/view yang berubah.
- Telegram: default off, kecuali ada error atau ringkasan harian.
- Ingest: batch upsert.

## Cold Job
Digunakan untuk backfill historis.

- Rentang: per bulan/per akun.
- Contoh: `djpbaceh_20260101_20260131.jsonl`.
- Tujuan: melengkapi data laporan bulanan/triwulan/semester.
- Telegram: ringkasan selesai/gagal, bukan per postingan.
- Ingest: preview dulu, validasi, baru upsert.

## Folder Staging
```text
data/staging/hot/YYYY-MM-DD/
data/staging/warm/YYYY-MM/
data/staging/cold/YYYY-MM/
data/checkpoints/
```

## Format JSONL
Satu baris adalah satu postingan.

```json
{"batch_id":"cold_202601_djpbaceh","batch_type":"COLD","username":"djpbaceh","unit_name":"Kanwil DJPb Provinsi Aceh","post_url":"https://www.instagram.com/p/xxxx/","shortcode":"xxxx","caption":"...","posted_at":"2026-01-10 09:00","media_type_normalized":"image","like_count":10,"comment_count":1,"view_count":null,"scraped_at":"2026-07-08T10:00:00"}
```

## Deduplicate
Prioritas unique key:
1. `shortcode`
2. `post_url`

Jika data sudah ada, lakukan update metrik. Jangan insert duplicate.

## Customize Data
Fitur customize data harus membuat batch berdasarkan:
- akun/scope
- periode
- tipe job
- zona waktu
- prioritas

Contoh permintaan:
```text
Akun: djpbaceh
Periode: 01/01/2026 - 31/03/2026
Tipe: COLD
Output: JSONL staging + preview + ingest
```

## Zona Waktu
Batch planner mendukung urutan:
```text
WIT → WITA → WIB
```

Ini hanya urutan operasional. Data laporan tetap harus menampilkan waktu posting secara konsisten berdasarkan waktu lokal akun.

## Checkpoint
Setiap batch harus punya status. Minimal:
```text
QUEUED, RUNNING, STAGED, VALIDATED, INGESTED, PARTIAL_FAILED, FAILED
```

Kalau worker mati, batch tidak boleh mulai dari nol jika staging/checkpoint sudah ada.
