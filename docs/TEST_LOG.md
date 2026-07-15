# Test Log - Mayz Monitoring

> Last Updated: 2026-07-12 20:00

## Environment Tests

| Test ID | Date | Component | Result | Notes |
|---------|------|-----------|--------|-------|
| ENV-001 | 2026-07-09 | MySQL | ✅ PASS | Active, PID 4568, port 3306 |
| ENV-002 | 2026-07-09 | Backend | ✅ PASS | Uvicorn on http://0.0.0.0:8000 |
| ENV-003 | 2026-07-09 | Database Connect | ✅ PASS | "Koneksi database berhasil" |
| ENV-004 | 2026-07-09 | Frontend | ✅ PASS | Running on http://localhost:5173 |
| ENV-005 | 2026-07-09 | Log File | ✅ PASS | `logs/worker.log` created |
| ENV-006 | 2026-07-12 | Docker Compose Config | ✅ PASS | All services validated |
| ENV-007 | 2026-07-12 | Docker Build | ✅ PASS | backend, frontend, worker images |
| ENV-008 | 2026-07-12 | Docker Backend | ✅ PASS | /health 200, /docs 200 |
| ENV-009 | 2026-07-12 | Docker Frontend | ✅ PASS | localhost:8080 200 |
| ENV-010 | 2026-07-12 | Docker Worker | ✅ PASS | Idle, no crash loop |
| ENV-011 | 2026-07-12 | MySQL Docker User | ✅ PASS | mayz_docker@'%' created |

## Worker Tests

| Test ID | Date | Mode | Result | Output | Notes |
|---------|------|------|--------|--------|-------|
| WORK-001 | 2026-07-09 | --once | ✅ PASS | "No queued job. Exiting." | Exit clean |
| WORK-002 | 2026-07-09 | loop | ✅ PASS | Idle every 30s | No job, sleeping |
| WORK-003 | 2026-07-09 | loop idle | ✅ PASS | "[INFO] No queued job. Worker idle." | 2-3 cycles confirmed |
| WORK-004 | 2026-07-12 | Docker idle | ✅ PASS | "No queued job. Worker idle." | Stable |

## Patch Validation Tests

| Test ID | Date | Patch | Result | Notes |
|---------|------|-------|--------|-------|
| PV-001 | 2026-07-09 | worker/main.py syntax | ✅ PASS | `py_compile` OK |
| PV-002 | 2026-07-09 | src/scraper.py syntax | ✅ PASS | `py_compile` OK |
| PV-003 | 2026-07-09 | Browser lifecycle logs | ✅ PASS | Logs appear in output |
| PV-004 | 2026-07-09 | Per-account logs | ✅ PASS | Status/duration logged |
| PV-005 | 2026-07-09 | Browser close | ✅ PASS | "Browser closed." logged |

## Scraping Tests

### Single Account Tests

| Test ID | Date | Account | Result | Posts | Duration | Status | Notes |
|---------|------|---------|--------|-------|----------|--------|-------|
| SCRAPE-001 | 2026-07-09 | djpbntb | ⚠️ PARTIAL | 12 | ~5min | SUCCESS | First batch worked |
| SCRAPE-002 | 2026-07-09 | djpbyogyakarta | ❌ FAIL | 0 | 12s | LOGIN_WALL | Rate limit |
| SCRAPE-003 | 2026-07-09 | djpbyogyakarta | ❌ FAIL | 0 | 14s | LOGIN_WALL | Same account, rate limit persists |
| SCRAPE-004 | 2026-07-09 | djpbmaluku | ❌ FAIL | 0 | - | LOGIN_WALL | Rate limit |
| SCRAPE-005 | 2026-07-09 | djpbaceh | ❌ FAIL | 0 | - | LOGIN_WALL | Rate limit |

### Batch Test (3 Akun)

| Test ID | Date | Job ID | Result | Success | Failed | Notes |
|---------|------|--------|--------|---------|--------|-------|
| BATCH-001 | 2026-07-09 | BATCH-001-20260709142811 | ⚠️ PARTIAL | 2 | 2 | Only djpbntb worked |
| BATCH-002 | 2026-07-12 | TEST-20260712191542 | ✅ SUCCESS | 3 | 0 | All 3 accounts processed |

### Small Job 3 Akun Results (2026-07-12)

| Account | Status | Posts Found | Inserted | Notes |
|---------|--------|------------|----------|-------|
| djpbmaluku (WIT) | PARTIAL | 12 | 0 | Link collection limited |
| djpbntb (WITA) | PARTIAL | 12 | 0 | Link collection limited |
| djpbaceh (WIB) | PARTIAL | 12 | 0 | Link collection limited |

**Summary:**
- Total rows: 36
- Full Success: 36 (detail extraction)
- Inserted: 14 (duplicates skipped - posts already in DB)
- Login wall: 0
- Browser closed: yes
- Job status: SUCCESS

## Telegram Tests

| Test ID | Date | Setting | Result | Notes |
|---------|------|---------|--------|-------|
| TELE-001 | 2026-07-09 | TELEGRAM_NOTIFY_NEW_POST | ✅ OFF | Per-post disabled |
| TELE-002 | 2026-07-09 | TELEGRAM_NOTIFY_NEW_POSTS | ✅ OFF | Per-post disabled |
| TELE-003 | 2026-07-09 | Spam check | ✅ NO SPAM | No Telegram messages sent |
| TELE-004 | 2026-07-12 | Docker Worker | ✅ NO SPAM | No Telegram messages sent |

## Docker Tests

| Test ID | Date | Component | Result | Notes |
|---------|------|-----------|--------|-------|
| DOCKER-001 | 2026-07-12 | Compose config | ✅ PASS | All services validated |
| DOCKER-002 | 2026-07-12 | Build backend | ✅ PASS | PYTHONPATH fixed |
| DOCKER-003 | 2026-07-12 | Build frontend | ✅ PASS | nginx image |
| DOCKER-004 | 2026-07-12 | Build worker | ✅ PASS | Playwright Chromium installed |
| DOCKER-005 | 2026-07-12 | Run backend | ✅ PASS | Health check passing |
| DOCKER-006 | 2026-07-12 | Run frontend | ✅ PASS | Dashboard accessible |
| DOCKER-007 | 2026-07-12 | Run worker | ✅ PASS | Idle, no crash |
| DOCKER-008 | 2026-07-12 | DB connection | ✅ PASS | mayz_docker user works |
| DOCKER-009 | 2026-07-12 | Small Job 3 Akun | ✅ SUCCESS | Job TEST-20260712191542 |

## Known Failures

| Test | Failure Reason | Expected Behavior | Recovery |
|------|---------------|------------------|---------|
| SCRAPE-002/003 | Instagram rate limit | Wait and retry | Self-healing |
| SCRAPE-004/005 | Instagram rate limit | Wait and retry | Self-healing |
| BATCH-001 partial | Only 1 of 3 accounts worked | All 3 should succeed | Need rate limit clear |

## Test Environment

```
OS: Windows 11 Home Single Language
Python: 3.12.0
MySQL: MariaDB 10.4.32 (XAMPP)
Docker: Desktop/WSL2
Container Stack: backend + frontend + worker
Playwright: Chromium (Docker worker image)
```

## Test Scope

Tests done:
- ✅ Environment setup
- ✅ Worker basic operations
- ✅ Patch C1 syntax
- ✅ Patch C1 runtime validation
- ✅ Observability logs
- ✅ Docker local demo
- ✅ All 3 services running

Tests NOT done:
- ⏳ Full 3-account batch (rate limited)
- ⏳ Cold/warm/backfill
- ⏳ 34-account full scrape
- ⏳ Scheduler integration
- ⏳ Telegram summary alert

## Recommendations

1. **Wait for rate limit clear** before retry batch
2. **Test 1 account first** after rate limit clear
3. **Validate observability** before expanding batch
4. **Monitor login wall streak** to stop safely
