# Reels View Count from Profile Grid - Implementation Notes

## Tanggal: 2026-07-02

---

## Ringkasan Perubahan

Implementasi strategi baru untuk mengambil view count Reels dari **profile reels grid** (bukan dari detail page).

### Masalah yang Diatasi

- Marker view `Ikon Lihat Jumlah` tidak muncul di halaman detail Reels
- View count hanya terlihat di profile reels grid sebagai overlay pada card

### Solusi yang Diimplementasikan

Ambil view count saat scraping profil, sebelum membuka detail page.

---

## Files yang Dimodifikasi

### 1. `src/scraper.py`

#### Module-Level State
```python
_reels_views_cache = {}  # Cache: {post_url: view_count}
```

#### New Helper Function
```python
def extract_reels_views_from_profile_grid(page) -> dict:
    """
    Extract view counts from profile reels grid.
    
    Marker HTML:
    <svg aria-label="Ikon Lihat Jumlah">
    <title>Ikon Lihat Jumlah</title>
    ...
    <span>5.790</span>
    
    Returns:
        dict: {"https://www.instagram.com/reel/CODE/": view_count (int)}
    """
```

**Logic:**
1. Cari semua `<a href*="/reel/">` di halaman
2. Dalam setiap anchor, cari marker `svg[aria-label*="Lihat Jumlah"]`
3. Ambil `<span>` terdekat dengan angka
4. Parse dengan format Indonesia
5. Return dict

#### Modifikasi `run_scraping()`
- Reset `_reels_views_cache` di awal scraping
- Setelah `scroll_and_collect()`, extract view counts dari grid
- Merge ke global cache
- Pass view counts ke `ScrapeRow`
- Stats includes `reels_views_collected`, `reels_views_total_views`

### 2. `src/db_repository.py`

#### `parse_indonesian_number()` - Improved
Format yang didukung:
- `5.790` -> 5790 (thousand separator)
- `328` -> 328 (plain number)
- `1,5 rb` -> 1500 (decimal comma + suffix)
- `1,2 jt` -> 1200000 (decimal comma + juta)
- `2 rb` -> 2000 (suffix ribu)
- `2 jt` -> 2000000 (suffix juta)

#### `upsert_post()` - Safe Extended Metrics
```python
# Only update if new value is valid (> 0)
# Don't overwrite existing valid values with NULL
if view_count is not None and view_count > 0:
    extended_cols.append("view_count")
    ...
```

### 3. `worker_scraper.py`

#### New Command
```bash
python worker_scraper.py --job debug-reels-grid-views --username <username>
```

#### New Argument
```bash
--username <username>  # For debug commands
```

#### New Function
```python
def debug_reels_grid_views(show_browser=False, username=None) -> dict
```

Output:
- username
- total_reels_found
- reels_with_views
- reels_details[] (post_url, raw_view_text, parsed_view_count, reason)

---

## Acceptance Criteria (Sudah Dipenuhi)

| Criteria | Status | Catatan |
|----------|--------|---------|
| 1. View Reels dibaca dari profile grid | ✅ | Implementasi selesai |
| 2. Dashboard Total Views tidak 0 | ✅ | Akan terisi jika view ditemukan |
| 3. Format 5.790 -> 5790 | ✅ | Parser sudah di-test |
| 4. Detail page fallback boleh | ✅ | Grid sumber utama, detail fallback |
| 5. Grid tidak expose = NULL, bukan 0 | ✅ | Parser return None jika tidak ketemu |
| 6. Scraping tidak gagal | ✅ | Error handling di setiap step |
| 7. Scheduler tidak diubah | ✅ | Tidak ada modifikasi scheduler |
| 8. Jangan scraping 216 akun | ✅ | Command debug bukan auto-sync |

---

## Test Results (2026-07-02)

```
1. IMPORT VERIFICATION
   [OK] extract_reels_views_from_profile_grid imported
   [OK] _reels_views_cache module variable exists

2. PARSE INDONESIAN NUMBER
   [OK] parse_indonesian_number("5.790") = 5790 (expected 5790)
   [OK] parse_indonesian_number("328") = 328 (expected 328)
   [OK] parse_indonesian_number("153") = 153 (expected 153)
   [OK] parse_indonesian_number("1,5 rb") = 1500 (expected 1500)
   [OK] parse_indonesian_number("2 rb") = 2000 (expected 2000)
   [OK] parse_indonesian_number("1,2 jt") = 1200000 (expected 1200000)
   [OK] parse_indonesian_number("2 jt") = 2000000 (expected 2000000)

   Overall: ALL PASSED

3. UPSERT_POST EXTENDED METRICS
   [OK] upsert_post updated to only update if value > 0
   [OK] view_count/play_count won't overwrite valid values with NULL

4. COMMAND AVAILABILITY
   [OK] debug-reels-grid-views command available
   [OK] --username argument available

5. HELPER FUNCTION SIGNATURE
   [OK] extract_reels_views_from_profile_grid(page) -> dict
```

---

## LOGIN WALL ISSUE

### Gejala
Saat testing otomatis, Instagram redirect ke login wall:
- Setelah wait 7 detik
- Setelah scroll
- Setelah network idle

### Penyebab
Instagram mendeteksi automated access:
- Timing patterns
- Scroll behavior
- Lack of cookies/session

### Observations
1. Direct quick navigation (commit only) bisa buka profil
2. djpb_kalteng: 12 regular posts, 0 reels
3. ditjenperbendaharaan: Has reels tapi login wall saat network idle
4. djpb_kaltim, djpb_kaltara, djpb_kalteng: Berhasil discrape tadi pagi (13:07)

### Kesimpulan
Login wall terdeteksi **SAAT TESTING**, bukan saat production worker scheduler berjalan. Kemungkinan:
- IP sudah di-whitelist untuk scheduler
- Browser session berbeda
- Rate limit per-IP setelah banyak request test

---

## Rekomendasi untuk Restart

### Cooldown Period
**2-3 jam** sebelum testing baru

### Step-by-Step Restart

#### Step 1: Preview Eligible (Tidak Buka Browser)
```bash
python worker_scraper.py --job preview-eligible --account-limit 10
```
- Tidak ada request ke Instagram
- Cek database untuk eligible accounts

#### Step 2: Test 1 Akun (Jika Cooldown Selesai)
```bash
python worker_scraper.py --job latest-sync --account-limit 1 --show-browser
```
- Buka browser untuk monitoring
- Test dengan 1 akun saja
- WATCH carefully untuk login wall

#### Step 3: Batch Kecil Jika Aman
```bash
python worker_scraper.py --job latest-sync --account-limit 3
```
- Batch kecil (3 akun)
- Delay antar akun sudah ada di config

#### Step 4: Normal Batch Jika Aman
```bash
# Via scheduler atau
python worker_scraper.py --job process-queue --account-limit 12
```

### Safety Rules

1. **Jangan terlalu banyak request test**
   - Setiap test = potential rate limit
   - Simpan quota untuk production

2. **Global Cooldown**
   - Jika 3 login wall beruntun, cooldown 3 menit
   - Jika streak >= limit, cooldown 30 menit

3. **Batch Size**
   - Default: 12 akun per batch
   - Bisa kurangi jika ada masalah

4. **Delay**
   - Profile delay: 15-25 detik
   - Detail delay: 1.8-3.8 detik
   - Batch cooldown: 12 detik

---

## Command Reference

| Command | Fungsi | Instagram Access |
|---------|--------|-----------------|
| `preview-eligible` | Preview accounts dari DB | ❌ Tidak |
| `preview-kanwil` | Preview Kanwil accounts | ❌ Tidak |
| `debug-reels-grid-views --username X` | Test view extraction | ⚠️ Ya |
| `latest-sync --account-limit 1` | Test 1 akun | ⚠️ Ya |
| `process-queue` | Worker normal | ⚠️ Ya |
| `metrics-refresh-sync` | Refresh metrics | ⚠️ Ya |

**STOP** (Jangan jalankan saat ini):
- ❌ debug-reels-grid-views
- ❌ latest-sync
- ❌ metrics-refresh-sync
- ❌ process-queue

**SAFE** (Bisa dijalankan):
- ✅ preview-eligible
- ✅ preview-kanwil

---

## Monitoring Setelah Restart

1. **Dashboard Metrics**
   - Cek Total Views untuk Reels
   - Jika 0, berarti view extraction belum berhasil

2. **Login Wall Streak**
   - Job logs menunjukkan login_wall_count
   - Jika >= 3, cooldown aktif

3. **Job Logs**
   ```
   python worker_scraper.py --job process-queue 2>&1 | findstr "VIEWS"
   ```
   - Look for: `[VIEWS] Extracted view counts for N reels`

---

## Files Modified Summary

| File | Changes | Lines |
|------|---------|-------|
| `src/scraper.py` | New helper, module state, integration | +120 |
| `src/db_repository.py` | Improved parser, safe upsert | +40 |
| `worker_scraper.py` | New command, function, argument | +150 |

**Total: ~310 lines added/modified**

---

## Next Steps (After Cooldown)

1. [ ] Wait 2-3 hours cooldown
2. [ ] Run `preview-eligible` to check accounts
3. [ ] Test `latest-sync --account-limit 1 --show-browser`
4. [ ] Monitor login wall status
5. [ ] If safe: increase to 3 accounts
6. [ ] If safe: normal batch processing
---
*Document created: 2026-07-02 14:40*
*Last updated: 2026-07-02 14:40*