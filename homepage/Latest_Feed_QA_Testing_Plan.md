# Latest Feed Homepage — QA Testing & Automation Plan
## Test Plan & Architecture Documentation

Dokumen ini adalah rujukan QA untuk menguji fitur baru **Latest Feed** (`page_mode=latest`) pada endpoint `/api/v3/homepage/recommendation`. Mencakup rencana *manual test case* dan rencana *automation testing* yang dapat diintegrasikan/diadaptasi dari framework QA Automation TribunX Recommendation Engine yang sudah ada.

---

## 1. OVERVIEW SISTEM

* **Tujuan Fitur**: Menyajikan feed artikel terbaru (kronologis) yang difilter ketat berdasarkan geolokasi user, dengan fallback bertingkat jika artikel lokal tidak cukup.
* **Endpoint yang Diuji**: `GET /api/v3/homepage/recommendation?page_mode=latest`
* **Karakteristik Unik vs Endpoint Recommendation Reguler**:
  * Tidak ada *personalized/similarity backfill* — murni kronologis (`type: latest_news`).
  * Tidak ada batas *recency* (artikel lama tetap muncul selama urutan tanggalnya benar).
  * Ada mekanisme *visual deduplication* berbasis cover image.
  * Ada *geo-fallback cascade* 5 level: City → Province → Region → Country → National (tribunnews).
  * Dilengkapi *Redis passive fallback* saat database utama (MongoDB/Qdrant) down.

---

## 2. ENDPOINT SPECIFICATION

| Parameter | Tipe | Required | Deskripsi |
|---|---|---|---|
| `client_id` | string | Ya | ID unik user/device |
| `page_mode` | string | Ya | Harus `latest` |
| `localized` | boolean/string | Tidak | `true`/`"local"` = strict geo-filter; `false`/`"global"` = feed global; `"mix"` = blend lokal+global |
| `num_recommendation` | integer | Tidak | Default & max = 20 |
| `ip_address` | string | Tidak | Override IP untuk testing geo-filter |
| `source_url` | string | Tidak | Diisi untuk Web, dikosongkan untuk Mobile App |

**Contoh Response (Mobile App):**
```json
{
  "status": true,
  "data": [
    {
      "site": "tribunnews",
      "publish_date": "2026-07-21T09:14:27+07:00",
      "id": "7856850",
      "title": "...",
      "type": "latest_news",
      "score": 16.109,
      "region": "Jawa",
      "city": "Jakarta",
      "province": "DKI Jakarta"
    }
  ],
  "execution_time": 45.43,
  "user_location": "Jakarta"
}
```

---

## 3. ARSITEKTUR TESTING (RENCANA AUTOMATION)

Mengadaptasi pola *Data Collector* + *Validation Engine* dari framework TribunX Recommendation Engine QA Automation sebelumnya.

### Struktur Folder & Module (Usulan)
* `Latest Feed QA/` (Root Directory)
  * **`config.py`**: Menyimpan `MAX_ARTICLE = 20`, daftar IP test per level geo (city/province/region/country), `client_id` dummy, endpoint base URL & API key.
  * **`test.py`**: Data Collector — iterasi matriks (Client × IP × Mode [local/global/mix]), hit endpoint, dump JSON mentah ke CSV.
  * **`IP address data.csv`**: *Ground truth* pemetaan IP ke city/province/region/country (bisa reuse dari project sebelumnya).
  * **`output/`**: Hasil dump `testing_TIMESTAMP.csv`.
* `Latest Feed QA/qa_automation/` (Engine Directory)
  * **`main.py`**: Entry point Validation Engine.
  * **`data_loader.py`**: Parsing CSV → Python object.
  * **`models.py`**: Data class `TestRequest`, `Article`, `ValidationResult`.
  * **`validators/`**:
    * `sorting_val.py` — validasi urutan kronologis.
    * `geo_fallback_val.py` — validasi cascade City→Province→Region→Country.
    * `dedup_visual_val.py` — validasi duplikasi cover image.
    * `count_val.py` — validasi jumlah artikel ≤ 20.
    * `resilience_val.py` — deteksi `type: "default-value"` (Redis fallback).
    * `latency_val.py` — reuse dari project sebelumnya.
  * **`reporters/html_reporter.py`**: Dashboard HTML hasil validasi (reuse).

### Alur Data
`API Backend` ➔ `JSON Response` ➔ `CSV Dump (test.py)` ➔ `Parsed Objects` ➔ `Validator Pipeline` ➔ `HTML Reporter`.

---

## 4. PARAMETER & VALIDATION RULES (AUTOMATED)

1. **Latency Validation**
   * PASS jika < threshold `config.py`; WARNING di ambang toleransi; FAIL jika melebihi.

2. **Article Count Validation**
   * PASS jika jumlah artikel ≤ `num_recommendation` (default/max 20).
   * FAIL jika melebihi limit yang diminta.

3. **Chronological Sorting Validation**
   * *Logic*: Bandingkan `publish_date` antar artikel berurutan; setiap artikel berikutnya harus ≤ artikel sebelumnya (descending).
   * FAIL jika ditemukan urutan yang terbalik (artikel lebih baru muncul setelah artikel lebih lama).
   * *Catatan*: Tidak ada validasi batas umur (recency), karena fitur ini memang menampilkan berita lama jika urutannya benar.

4. **Geo-Fallback Cascade Validation**
   * *Logic*: Untuk request `localized=true`, tentukan level geo teranchor dari IP (`IP address data.csv`).
   * **[Klarifikasi Backend: tidak ada threshold minimum]** Logic-nya adalah *exact backfill* — sisa kuota yang tidak terpenuhi di satu level langsung ditambal persis dari level berikutnya:
     * `province_backfill_count = requested - city_available_count` (bukan berbasis ambang seperti "< 20 artikel").
     * Jika Province masih kurang → tambal sisa dari **Region**.
     * Jika Region masih kurang → tambal sisa dari **Country** → lalu **National (tribunnews)**.
   * PASS jika `city_count + province_count + region_count + country_count + national_count == num_recommendation diminta` DAN masing-masing count di atas cocok dengan stok riil per level (bukan asumsi jumlah tetap).
   * FAIL jika ada level yang dilewati tanpa alasan (misal langsung lompat ke national padahal province & region belum dicoba), atau total tidak menutup kuota yang diminta.

5. **Visual Deduplication Validation**
   * *Logic*: Bandingkan field `foto` (cover image URL) antar artikel yang bersebelahan (posisi index N dan N+1).
   * FAIL jika dua artikel bersebelahan punya `foto` identik.

6. **Duplicate Article ID Validation**
   * FAIL jika ada ID artikel yang ganda dalam satu response.

7. **Mode Validation (local / global / mix)**
   * `local`/`true`: 100% artikel harus melalui geo-fallback cascade sesuai IP.
   * `global`/`false`: Artikel tidak boleh difilter geografis (harus tersebar dari berbagai lokasi).
   * **[Klarifikasi Backend]** `mix`: Rasio **dinamis tergantung ketersediaan artikel**, mengikuti pola *backfill* yang sama seperti Personalized vs Top-News di project Recommendation Engine reguler — Local diprioritaskan mengisi kuota semaksimal stok yang ada, sisanya ditambal Global. PASS jika `local_count == min(local_stock_available, requested)` DAN `global_count == requested - local_count`.

8. **Resilience / Redis Fallback Validation**
   * *Logic*: Deteksi field `type`.
     * Normal: `"latest_news"` atau `"popular"`.
     * Fallback aktif: `"default-value"`.
   * **[Klarifikasi Backend: tidak ada SLA/batas waktu]** Karena tidak ada batas waktu resmi kapan fallback dianggap "insiden kritikal", automation **tidak boleh mem-FAIL-kan** kondisi fallback berdasarkan durasi — cukup ditandai `"FALLBACK DETECTED"` (informational) setiap kali terdeteksi, dipakai untuk memantau apakah DB utama sedang bermasalah saat testing berjalan.
   * *Catatan QA*: Karena tidak ada SLA otomatis, eskalasi ke tim Infra/Backend soal durasi fallback yang kelamaan tetap harus dilakukan manual (lihat TC-017 di dokumen Test Scenarios), bukan lewat alert otomatis dari automation.

9. **Source Handling Validation (Web vs Mobile)**
   * **[Klarifikasi Backend]** Struktur response identik — `source_url` tidak mengubah bentuk JSON.
   * PASS jika `set(keys_web) == set(keys_mobile)`. FAIL jika ditemukan field yang hanya muncul di salah satu kondisi.

---

## 5. TEST CASE LIST — AUTOMATED (Data Collector + Validator)

| # | Test Case | Parameter yang Diuji | Expected |
|---|---|---|---|
| 1 | Localized feed, IP City valid | `localized=true`, IP city dengan artikel cukup | 100% artikel dari City yang sama |
| 2 | Localized feed, IP City minim artikel | `localized=true`, IP city dengan stok artikel di bawah kuota diminta | Sisa kuota ditambal persis (*exact backfill*) dari Province |
| 3 | Localized feed, Province & Region minim | IP di daerah artikel sangat sedikit | Fallback berjenjang sampai National, tiap level dicoba berurutan |
| 4 | Global feed | `localized=false` | Artikel tersebar lintas lokasi, tidak ada filter geo |
| 5 | Mix feed | `localized=mix` | Local mengisi kuota semaksimal stok, sisanya ditambal Global (pola backfill) |
| 6 | Jumlah artikel default | Tanpa `num_recommendation` | Maksimal 20 artikel dikembalikan |
| 7 | Jumlah artikel custom | `num_recommendation=10` | Tepat ≤ 10 artikel dikembalikan |
| 8 | Sorting kronologis | Semua request | `publish_date` descending tanpa terbalik |
| 9 | Visual dedup | Semua request | Tidak ada `foto` sama persis di posisi bersebelahan |
| 10 | Duplicate ID | Semua request | Tidak ada `id` ganda dalam satu response |
| 11 | Latency | Semua request | Di bawah threshold `config.py` |
| 12 | Redis fallback simulation | Simulasi DB down (staging) | `type: "default-value"` muncul, response tetap 200 OK |
| 13 | Web vs Mobile source | Dengan/tanpa `source_url` | Struktur response sesuai platform |

---

## 6. TEST CASE — MANUAL / EXPLORATORY (SIMULATOR)

Area yang butuh verifikasi visual/manual karena automation tidak bisa menilai relevansi konten secara subjektif:

1. **Visual Dedup Realness Check**
   * Cek manual apakah artikel dengan gambar mirip (bukan identik) tetap lolos wajar (bukan false negative).
2. **Geo-Fallback UX Check**
   * Saat fallback ke level Country/National terjadi, cek apakah user tidak merasa "salah lokasi" secara UX (misal ada label/section yang menjelaskan).
3. **Redis Fallback Content Quality**
   * Karena tidak ada SLA/batas waktu otomatis dari Backend, QA perlu manual mengecek berkala saat `type: "default-value"` muncul apakah artikel default tersebut masih relevan/tidak basi — eskalasi ke tim Infra dilakukan manual, bukan lewat alert otomatis.
4. **Cross-Platform Consistency**
   * Bandingkan hasil Web (`source_url` terisi) vs Mobile (`source_url` kosong) untuk `client_id` & IP yang sama — pastikan tidak ada perbedaan logic yang tidak disengaja.
5. **Load/Concurrency Check**
   * Uji beberapa request bersamaan dari region yang sama untuk memastikan fallback cascade tidak salah anchor akibat *race condition*.

---

## 7. AUTOMATED vs MANUAL SUMMARY

### A. Fully Automated
* Jumlah artikel (≤ 20)
* Sorting kronologis
* Duplicate ID
* Visual deduplication (perbandingan string `foto`)
* Latency
* Deteksi Redis fallback (`type: default-value`)
* Geo-fallback cascade (*exact backfill* — validasi matematis, bukan lagi threshold)
* Mode `mix` (proporsi Local vs Global mengikuti pola backfill, bisa reuse `CompositionValidator` existing)

### B. Semi-Automated
* Kasus ambigu geo-fallback di perbatasan region (butuh review manual sesekali untuk validasi ground-truth IP mapping).

### C. Manual Testing Required
* Kualitas konten saat Redis fallback aktif (basi/tidaknya cache) — tidak ada SLA otomatis, jadi eskalasi durasi tetap manual.
* UX saat fallback geo terjadi (apakah user aware).
* Load/concurrency edge case pada fallback cascade.

> Catatan: Konsistensi Web vs Mobile (`source_url`) sudah dikonfirmasi Backend berstruktur identik — sudah dipindah ke kategori **Fully Automated** (lihat poin 9 di Section 4), cukup validasi `keys` response sama persis.

---

## 8. cURL TEST SCRIPTS (STAGING)

```bash
# Localized Latest Feed
curl -s -H "X-API-Key: c2c32d37d870c155cfc9ee62d03db1dd38c980cde42f8cf20113719bf23a9e36" \
"https://stg-reco-app.tribundata.com/api/v3/homepage/recommendation?client_id=test-1235&page_mode=latest&localized=true&num_recommendation=10"

# Global Latest Feed
curl -s -H "X-API-Key: c2c32d37d870c155cfc9ee62d03db1dd38c980cde42f8cf20113719bf23a9e36" \
"https://stg-reco-app.tribundata.com/api/v3/homepage/recommendation?client_id=test-1235&page_mode=latest&localized=false&num_recommendation=10"

# Mix Mode Latest Feed
curl -s -H "X-API-Key: c2c32d37d870c155cfc9ee62d03db1dd38c980cde42f8cf20113719bf23a9e36" \
"https://stg-reco-app.tribundata.com/api/v3/homepage/recommendation?client_id=test-1235&page_mode=latest&localized=mix&num_recommendation=10"

# Explicit IP override (testing geo-fallback)
curl -s -H "X-API-Key: c2c32d37d870c155cfc9ee62d03db1dd38c980cde42f8cf20113719bf23a9e36" \
"https://stg-reco-app.tribundata.com/api/v3/homepage/recommendation?client_id=test-1235&page_mode=latest&localized=true&ip_address=<TEST_IP>&num_recommendation=10"
```

---

## 9. KLARIFIKASI BACKEND (RESOLVED)

| Pertanyaan | Jawaban Backend | Dampak ke Validation Logic |
| :--- | :--- | :--- |
| Threshold minimum per level geo | **Tidak ada threshold.** Exact backfill — sisa kuota langsung ditambal dari level berikutnya. | `GeoFallbackValidator` diubah dari cek ambang "< 20" menjadi validasi matematis `gap = requested - available_at_level`. |
| SLA/batas waktu Redis fallback | **Tidak ada batas waktu.** Tidak ada definisi resmi kapan fallback dianggap insiden kritikal. | `ResilienceValidator` tetap bersifat *informational-only* (`FALLBACK DETECTED`), tidak boleh generate FAIL berbasis durasi. Eskalasi durasi tetap manual (lihat TC-017 di dokumen Test Scenarios). |
| Rasio mode `mix` | **Dinamis tergantung ketersediaan artikel** — mengikuti pola backfill Personalized vs Top-News di project Recommendation Engine reguler. | `Mode Validator` untuk `mix` naik dari Semi-Automated → **Fully Automated**; formula: `local_count == min(local_stock, requested)`, sisanya `global_count`. |
| Perbedaan struktur Web vs Mobile *(sudah dikonfirmasi sebelumnya)* | **Struktur identik**, `source_url` tidak mengubah bentuk JSON. | `Source Handling Validator` naik ke Fully Automated; assertion `set(keys)` harus sama persis. |
