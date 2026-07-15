# Decision Log - Mayz Monitoring

> Last Updated: 2026-07-09 15:40

## Architectural Decisions

### D1: Dashboard Tidak Menjalankan Scraping
| Item | Value |
|------|-------|
| Decision | Dashboard tidak boleh menjalankan scraping berat |
| Rationale | Dashboard harus ringan, worker jalan terpisah |
| Status | Approved |
| Date | 2026-07-09 |

### D2: Worker Menjalankan Scraping
| Item | Value |
|------|-------|
| Decision | Worker adalah satu-satunya yang menjalankan scraping |
| Rationale | Worker bisa loop, retry, heartbeat, dan monitoring |
| Status | Approved |
| Date | 2026-07-09 |

### D3: Export Excel Tidak Scraping Ulang
| Item | Value |
|------|-------|
| Decision | Export Excel ambil data dari database, bukan scraping ulang |
| Rationale | Database adalah source of truth |
| Status | Approved |
| Date | 2026-07-09 |

### D4: Telegram Tidak Spam Per Postingan
| Item | Value |
|------|-------|
| Decision | Default: Telegram ringkasan per batch, bukan per post |
| Rationale | Hindari overload grup dengan notifikasi massal |
| Exception | Per-post boleh untuk scope kecil atau debug |
| Status | Approved |
| Date | 2026-07-09 |

### D5: media_type_normalized sebagai Field Utama
| Item | Value |
|------|-------|
| Decision | `media_type_normalized` adalah field yang dipakai dashboard/export |
| Rationale | Field ini sudah dinormalisasi dengan benar |
| Constraint | Jangan ubah tanpa bukti teknis |
| Status | Approved |
| Date | 2026-07-09 |

### D6: Unknown Tidak Dipaksa
| Item | Value |
|------|-------|
| Decision | `unknown` tidak boleh dipaksa jadi `image` atau `carousel` tanpa bukti |
| Rationale | Data harus akurat, bukan dipaksa match |
| Status | Approved |
| Date | 2026-07-09 |

## Infrastructure Decisions

### D7: Single Worker Mode
| Item | Value |
|------|-------|
| Decision | Untuk laptop kantor sementara, hanya boleh 1 worker aktif |
| Rationale | MariaDB 10.4 tidak support `FOR UPDATE SKIP LOCKED` |
| Impact | Multi-worker ditahan sampai upgrade database |
| Status | Approved |
| Date | 2026-07-09 |

### D8: MariaDB 10.4 Limitation
| Item | Value |
|------|-------|
| Issue | `FOR UPDATE SKIP LOCKED` tidak tersedia |
| Workaround | Single worker mode, hapus SKIP LOCKED clause |
| Production | Upgrade ke MariaDB 10.5+ atau MySQL 8.0+ |
| Status | Technical Debt |
| Date | 2026-07-09 |

## Scraping Decisions

### D9: Urutan Zona Waktu
| Item | Value |
|------|-------|
| Decision | Urutan scraping: WIT → WITA → WIB |
| Rationale | Wilayah timur diproses lebih dulu untuk laporan harian |
| Status | Approved |
| Date | 2026-07-09 |

### D10: ZERO_POST Valid
| Item | Value |
|------|-------|
| Decision | `ZERO_POST` valid jika memang tidak ada post dalam periode |
| Criteria | - Log jelas<br>- Tidak ada exception<br>- Browser closed<br>- Periode benar |
| Status | Approved |
| Date | 2026-07-09 |

### D11: Login Wall Self-Healing
| Item | Value |
|------|-------|
| Decision | Login wall dianggap rate-limit sementara, tunggu dan retry |
| Rationale | Instagram rate-limit pulih sendiri dalam waktu |
| Constraint | Jangan spam retry, beri jeda |
| Status | Approved |
| Date | 2026-07-09 |

## Scraper Decisions

### D12: Playwright over Selenium
| Item | Value |
|------|-------|
| Decision | Scraper menggunakan Playwright, bukan Selenium |
| Rationale | Playwright lebih modern dan stealth |
| Files | `src/scraper.py` |
| Status | Implemented |
| Date | 2026-07-09 |

### D13: Browser Lifecycle Logging
| Item | Value |
|------|-------|
| Decision | Browser lifecycle harus di-log untuk observability |
| Log Points | - Browser starting/started<br>- Browser closing/closed |
| Status | Implemented (Patch C1) |
| Date | 2026-07-09 |

### D14: Per-Account Logging
| Item | Value |
|------|-------|
| Decision | Setiap akun harus punya log dengan status dan durasi |
| Log Format | `[ACCOUNT] 1/3 finish: username | status=SUCCESS | posts=X | inserted=X | duration=Ns` |
| Status | Implemented (Patch C1) |
| Date | 2026-07-09 |

## Batch Decisions

### D15: Batch 3 Akun Awal
| Item | Value |
|------|-------|
| Decision | Batch awal 3 akun: djpbmaluku, djpbntb, djpbaceh |
| Urutan | WIT → WITA → WIB |
| Periode | 3-7 hari terakhir |
| Mode | HOT / LATEST_SYNC |
| Status | Pending Execution |
| Date | 2026-07-09 |

### D16: Jangan Cold/Warm/Backfill Dulu
| Item | Value |
|------|-------|
| Decision | Fokus HOT/LATEST_SYNC dulu, cold/warm/backfill nanti |
| Rationale | Stabilkan pipeline hot, baru expand |
| Status | Approved |
| Date | 2026-07-09 |

### D17: Jangan 34 Akun Sekaligus
| Item | Value |
|------|-------|
| Decision | Jangan scraping 34 akun sekaligus |
| Rationale | Risiko rate-limit tinggi, sulit monitoring |
| Approach | Batch kecil 1-3 akun, monitoring, baru lanjut |
| Status | Approved |
| Date | 2026-07-09 |

## File Scope Decisions

### D18: Locked Files
| Category | Files |
|----------|-------|
| Dashboard UI | Jangan ubah desain yang sudah benar |
| Auth/Login | Jangan ubah logic |
| Parser | Jangan ubah selector yang sudah stabil |
| Media Type | Jangan ubah normalize logic |
| Export | Jangan ubah yang sudah berjalan |
| Schema | Jangan ubah tanpa migration plan |
| Dist | Jangan edit `frontend/dist` |

### D19: Allowed Files (Maintenance)
| File | Scope |
|------|-------|
| `worker/main.py` | Worker logic, logging, job handling |
| `src/scraper.py` | Browser lifecycle, logging, retry logic |

## Rejected Ideas

| Idea | Reason Rejected |
|------|----------------|
| Multi-worker sekarang | MariaDB 10.4 tidak support SKIP LOCKED |
| Cold backfill sekarang | Fokus HOT dulu |
| Scraping 34 akun sekaligus | Risiko rate-limit |
| Per-post Telegram alert | Spam grup |
| Hardcode media_type | Data tidak akurat |
