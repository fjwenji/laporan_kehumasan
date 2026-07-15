# Claude Agent Guide - Mayz Monitoring

Baca ini sebelum coding.

## Status Project
Project sudah masuk tahap siap scraping operasional. Jangan perlakukan sebagai redesign UI atau eksperimen.

## Jangan Ubah Tanpa Instruksi
- Desain login/dashboard/settings/export yang sudah benar.
- Auth/login logic.
- Parser Instagram yang sudah stabil.
- Media type normalized.
- Export Excel yang sudah berjalan.
- Database schema tanpa migration.
- Folder `frontend/dist`.

## Fokus Maintenance Berikutnya
1. Bulk scraping hot/warm/cold.
2. JSONL staging.
3. Batch checkpoint.
4. Preview tabel sementara dari JSONL.
5. Deduplicate by shortcode/post_url.
6. Batch upsert database.
7. Telegram summary alert, bukan spam per post.
8. Worker hidup terus melalui Task Scheduler/service.

## Cara Kerja Aman
1. Inspect dulu file terkait.
2. Laporkan file yang akan diubah.
3. Ubah kecil dan terarah.
4. Jalankan build/test yang relevan.
5. Jangan refactor besar.
6. Jangan menghapus file tanpa daftar dan alasan.

## Konsep Data
- JSONL staging = tempat transit sementara.
- Database = source of truth.
- Dashboard/export = baca database.
- Customize Data = bisa baca JSONL untuk preview sebelum ingest.

## Telegram
Default notifikasi adalah summary per batch/job. Per-post alert default OFF kecuali scope kecil/debug.

## Prioritas Zona Waktu
Urutan scraping operasional harus mengikuti:

```text
WIT → WITA → WIB
```

Jangan ubah menjadi WITA/WIB lebih dulu kecuali ada instruksi baru dari user/mentor.

## Setup Dua Device
Asumsi operasional sementara:
- Laptop server rumah menjalankan MySQL, backend, frontend, worker, scheduler, staging, dan logs.
- Laptop kerja/kantor hanya untuk akses dashboard atau remote ke laptop server.
- Jangan desain workflow yang mengharuskan laptop kerja menjalankan worker atau database.


## Scope Control Loop

Every task must follow this loop:

1. Read context docs.
2. State current phase.
3. Confirm allowed files.
4. Confirm locked files.
5. Plan a small step.
6. Ask approval before editing.
7. Execute only approved scope.
8. Validate.
9. Update progress docs.
10. Stop.

Required docs before any task:
- PRD.md
- README.md
- CLAUDE.md
- docs/CURRENT_PROGRESS.md
- docs/NEXT_ACTIONS.md
- docs/DECISION_LOG.md
- docs/TEST_LOG.md
- docs/WORKFLOW_LOOP.md
- docs/PROSES_BISNIS_MAYZ_MONITORING.md

If unsure, reread the relevant docs and stop.

Do not continue when:
- current phase is unclear
- allowed files are unclear
- requested action conflicts with PRD
- task requires changing locked files
- task requires running unapproved commands
- output starts drifting from the original scope

Locked without explicit approval:
- scraper/parser
- media type logic
- export Excel
- frontend design
- database schema
- dist folder
- secrets/env values
- production deployment
- big scraping
- multi-worker mode

Required output before edit:

```md
## Context Check
- Current phase:
- Docs read:
- Scope:

## Allowed Files
- ...

## Locked Files
- ...

## Plan
1. ...
2. ...

## Approval Needed
Waiting for approval