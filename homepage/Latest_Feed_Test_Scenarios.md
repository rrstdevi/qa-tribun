# Manual & Automation Testing Scenario
## Latest Feed Homepage QA - TribunX

Dokumen ini merangkum seluruh *Test Case* (Skenario Pengujian) untuk memvalidasi fitur **Latest Feed** (`page_mode=latest`) pada endpoint `/api/v3/homepage/recommendation`.

**Konsep Pengujian Hibrida (Hybrid Testing):**
Pengujian ini menggabungkan **Manual Testing** dan **Automation Testing** ke dalam satu siklus (*pipeline*) yang saling terkait:
1.  **Manual Testing (via Simulator/Postman)** bertindak sebagai **Trigger/State Builder**. QA mengatur parameter (IP, mode, jumlah artikel) untuk membentuk kondisi *request* tertentu.
2.  **Automation Testing (via Script)** bertindak sebagai **Validator**. Script menarik respon JSON dan memastikan aturan bisnis (sorting, deduplikasi, geo-fallback, resilience) berjalan tanpa pelanggaran.

---

## 1. DAFTAR TEST CASE (SCENARIO LIST)

### 1.1 Core Behavior & Sorting
| ID | Skenario | Tipe | Coverage |
| :--- | :--- | :--- | :--- |
| **TC-001** | Chronological Sorting Validation | Positive | Fully Automated |
| **TC-002** | Article Count Limit (Custom `num_recommendation`) | Positive | Fully Automated |
| **TC-003** | Default Article Count (Tanpa Parameter) | Positive | Fully Automated |
| **TC-004** | Visual Deduplication (Cover Image Sama) | Negative | Fully Automated |
| **TC-005** | Duplicate Article ID Detection | Negative | Fully Automated |
| **TC-014** | Latency Validation | Negative | Fully Automated |
| **TC-015** | No-Recency-Limit Behavior (Artikel Lama Tetap Tampil) | Positive | Fully Automated |

### 1.2 Localization & Geo-Fallback
| ID | Skenario | Tipe | Coverage |
| :--- | :--- | :--- | :--- |
| **TC-006** | Localized Feed - City Level Anchor | Positive | Fully Automated |
| **TC-007** | Geo-Fallback Cascade - City Insufficient → Province | Edge Case | Fully Automated |
| **TC-008** | Geo-Fallback Cascade - Full Cascade ke National | Edge Case | Fully Automated |
| **TC-009** | Global Feed Mode | Positive | Fully Automated |
| **TC-010** | Mix Mode Feed (Local + Global) | Positive | Fully Automated |
| **TC-011** | Explicit IP Override Testing | Positive | Fully Automated |

### 1.3 Rules, Constraints & Resilience
| ID | Skenario | Tipe | Coverage |
| :--- | :--- | :--- | :--- |
| **TC-012** | Redis Fallback Detection (DB Down Simulation) | Edge Case | Semi Automated |
| **TC-013** | Source Handling (Web vs Mobile App) | Positive | Fully Automated |
| **TC-016** | Complex: Geo-Fallback Consistency Under Concurrency | Anomaly | Manual Required |
| **TC-017** | Complex: Redis Fallback Content Staleness | Anomaly | Manual Required |

---

## 2. DETAIL TEST CASES

### TC-001: Chronological Sorting Validation
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-001 |
| **Scenario** | Memastikan artikel dalam response `page_mode=latest` terurut kronologis dari yang paling baru ke paling lama, tanpa ada urutan yang terbalik. |
| **Type** | Positive Case |
| **Coverage** | Fully Automated |
| **Objective** | Engine tidak boleh menyisipkan artikel lama di antara artikel baru — feed harus murni "latest first". |
| **Preconditions** | Tidak ada precondition khusus (bisa dijalankan pada mode Local, Global, atau Mix). |
| **Test Data** | `client_id` = `test-1235`, `page_mode=latest`, `num_recommendation=20` |

*   **Manual Testing Steps (Postman/Simulator)**
    1. Hit endpoint `GET /api/v3/homepage/recommendation?page_mode=latest`.
    2. Catat `publish_date` dari seluruh artikel di array `data`.
*   **Expected Manual Result**: Urutan `publish_date` menurun (descending) dari index 0 hingga index terakhir.
*   **Automation Validation**:
    *   `SortingValidator` ➔ Membandingkan `publish_date[i]` dengan `publish_date[i+1]` untuk seluruh pasangan berurutan.
    *   FAIL jika ditemukan `publish_date[i] < publish_date[i+1]` (artikel lebih lama muncul sebelum artikel lebih baru).
*   **Observation Points**: Jika HTML Report menampilkan `Sorting: FAIL at index N`, kemungkinan query database tidak menerapkan `ORDER BY publish_date DESC` dengan benar, atau cache stale tercampur data baru.

---

### TC-002: Article Count Limit (Custom `num_recommendation`)
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-002 |
| **Scenario** | Memastikan jumlah artikel yang dikembalikan sesuai dengan nilai `num_recommendation` yang diminta. |
| **Type** | Positive Case |
| **Coverage** | Fully Automated |
| **Preconditions** | - |
| **Test Data** | `num_recommendation=10` |

*   **Manual Testing Steps**
    1. Hit endpoint dengan `num_recommendation=10`.
    2. Hitung jumlah item pada array `data`.
*   **Expected Manual Result**: Jumlah item = 10 (atau kurang jika stok artikel tidak cukup).
*   **Automation Validation**:
    *   `CountValidator` ➔ PASS jika `len(data) <= num_recommendation`. FAIL jika melebihi.
*   **Observation Points**: Jika jumlah artikel yang kembali > yang diminta (misal minta 10 tapi dapat 15), ini bug kritikal di layer pagination backend.

---

### TC-003: Default Article Count (Tanpa Parameter)
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-003 |
| **Scenario** | Memastikan saat `num_recommendation` tidak disertakan, sistem menggunakan default 8 dan tidak melebihi batas maksimal 8. |
| **Type** | Positive Case |
| **Coverage** | Fully Automated |

*   **Manual Testing Steps**
    1. Hit endpoint tanpa parameter `num_recommendation`.
*   **Expected Manual Result**: Jumlah artikel yang kembali maksimal 8.
*   **Automation Validation**:
    *   `CountValidator` ➔ FAIL jika `len(data) > 8`.
*   **Observation Points**: Perhatikan juga apakah default benar-benar 8 dan bukan nilai lain (misal 15 atau unlimited) — indikasi `config.py` backend belum sinkron dengan dokumentasi.

---

### TC-004: Visual Deduplication (Cover Image Sama)
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-004 |
| **Scenario** | Memastikan dua artikel dengan `foto` (cover image) identik tidak ditampilkan bersebelahan dalam satu response. |
| **Type** | Negative Case |
| **Coverage** | Fully Automated |
| **Objective** | Mencegah *feed* terlihat "kembar" secara visual bagi user, walau kontennya beda artikel. |

*   **Manual Testing Steps**
    1. Hit endpoint dan ambil seluruh field `foto` per artikel secara berurutan.
    2. Bandingkan visual di layar Simulator — cek apakah ada dua thumbnail identik yang berdempetan.
*   **Expected Manual Result**: Tidak ada dua cover image identik pada posisi bersebelahan.
*   **Automation Validation**:
    *   `VisualDedupValidator` ➔ Membandingkan `foto[i]` dengan `foto[i+1]`. FAIL jika sama persis (URL identik).
*   **Observation Points**: Jika FAIL terus terjadi pada artikel dari *section* yang sama (misal semua pakai foto template default), lapor ke tim Redaksi/CMS soal foto generik yang perlu divariasikan, atau ke Backend untuk memperketat logic dedup.

---

### TC-005: Duplicate Article ID Detection
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-005 |
| **Scenario** | Memastikan tidak ada `id` artikel yang muncul dua kali dalam satu response. |
| **Type** | Negative Case |
| **Coverage** | Fully Automated |

*   **Automation Validation**:
    *   `DuplicateIdValidator` ➔ FAIL jika ditemukan `id` ganda di array `data`.
*   **Observation Points**: Bug kritikal — biasanya terjadi saat cascade fallback (city→province) tidak melakukan exclusion terhadap artikel yang sudah diambil di level sebelumnya.

---

### TC-006: Localized Feed - City Level Anchor
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-006 |
| **Scenario** | Memastikan saat `localized=true` dan stok artikel City mencukupi (≥20), seluruh feed berasal dari City yang sama dengan IP user. |
| **Type** | Positive Case |
| **Coverage** | Fully Automated |
| **Preconditions** | IP test berada di kota dengan stok artikel latest yang banyak (contoh: Jakarta). |
| **Test Data** | `ip_address` = IP area Jakarta, `localized=true` |

*   **Manual Testing Steps**
    1. Set `ip_address` ke area dengan artikel melimpah (Jakarta).
    2. Hit endpoint dengan `localized=true`.
*   **Expected Manual Result**: `user_location` = "Jakarta", dan mayoritas/semua `city` artikel = "Jakarta".
*   **Automation Validation**:
    *   `GeoFallbackValidator` ➔ PASS dengan `Anchor Level: city`, `Anchor Value: jakarta`.
*   **Observation Points**: Jika ada artikel dari city lain menyelip padahal stok Jakarta cukup, berarti fallback ke province terpicu secara prematur — cek threshold di backend.

---

### TC-007: Geo-Fallback Cascade - City Insufficient → Province (Exact Backfill, Tanpa Threshold)
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-007 |
| **Scenario** | **[Klarifikasi Backend]** Tidak ada nilai threshold minimum. Logic-nya adalah *exact backfill*: jika stok City hanya menghasilkan 15 dari 20 artikel yang diminta, sisa kuota (5 artikel) langsung ditambal dari Province. Berlaku sama untuk kekurangan sisa dari Province → Region, dan seterusnya. |
| **Type** | Edge Case |
| **Coverage** | Fully Automated |
| **Test Data** | `ip_address` = IP kota kecil dengan stok artikel latest diketahui persis (misal kota dengan stok = 15 artikel) |

*   **Manual Testing Steps**
    1. Pilih/verifikasi kota dengan jumlah stok artikel latest yang **diketahui pasti** (misal 15 artikel).
    2. Hit endpoint `localized=true&num_recommendation=20`.
*   **Expected Manual Result**: Total tetap 20 artikel — 15 dari City asli + 5 dari Province (menutup sisa kuota persis).
*   **Automation Validation**:
    *   `GeoFallbackValidator` ➔ PASS jika `jumlah_artikel_city + jumlah_artikel_province_backfill == num_recommendation diminta` (bukan lagi berbasis threshold "< 20", melainkan *exact gap-filling*: `province_backfill_count == requested - city_available_count`).
    *   FAIL jika jumlah backfill dari Province tidak pas menutup sisa kuota (kurang atau lebih dari gap yang seharusnya).
*   **Observation Points**: Karena tidak ada threshold tetap, validator harus tahu **stok riil per kota** terlebih dulu (via query database test data / endpoint terpisah) sebagai baseline pembanding, bukan angka hardcoded "20". Kalau assertion masih pakai asumsi threshold lama, TC ini akan sering false-fail.

---

### TC-008: Geo-Fallback Cascade - Full Cascade ke National
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-008 |
| **Scenario** | IP berada di daerah terpencil dengan stok artikel City, Province, dan Region semuanya minim. Sistem harus jatuh sampai level Country/National (`tribunnews`). |
| **Type** | Edge Case |
| **Coverage** | Fully Automated |

*   **Manual Testing Steps**
    1. Set IP ke daerah dengan stok artikel lokal sangat minim di semua level.
    2. Hit endpoint `localized=true`.
*   **Expected Manual Result**: Feed tetap terisi 20 artikel, mayoritas berasal dari `site: tribunnews` (nasional).
*   **Automation Validation**:
    *   `GeoFallbackValidator` ➔ PASS dengan `Fallback Level: national`. Memvalidasi urutan cascade dilewati secara berjenjang (city → province → region → country → national), bukan langsung lompat ke national.
*   **Observation Points**: QA harus mengecek log/HTML Report apakah cascade benar-benar mencoba tiap level secara berurutan, atau backend langsung "menyerah" ke national tanpa mencoba province/region dulu (indikasi bug efisiensi/akurasi lokasi).

---

### TC-009: Global Feed Mode
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-009 |
| **Scenario** | Memastikan `localized=false` mengabaikan IP dan menampilkan artikel dari berbagai lokasi tanpa filter geografis. |
| **Type** | Positive Case |
| **Coverage** | Fully Automated |

*   **Manual Testing Steps**
    1. Gunakan IP yang sama dengan TC-006 (Jakarta).
    2. Ubah parameter menjadi `localized=false`.
*   **Expected Manual Result**: Artikel yang tampil berasal dari berbagai city/province, tidak didominasi Jakarta saja.
*   **Automation Validation**:
    *   `GeoFallbackValidator` ➔ SKIPPED/PASS by-design (tidak ada penalti lokasi pada mode global).
*   **Observation Points**: Bandingkan hasil `localized=true` vs `localized=false` untuk IP dan `client_id` yang sama. Jika hasilnya 100% identik, flag `localized` tidak berfungsi di backend.

---

### TC-010: Mix Mode Feed (Local + Global, Backfill Pattern)
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-010 |
| **Scenario** | **[Klarifikasi Backend]** Mode `mix` mengikuti pola *backfill* yang sama seperti Personalized vs Top-News di project Recommendation Engine reguler: artikel **Local diprioritaskan mengisi kuota terlebih dahulu**, sisa kuota yang tidak terpenuhi oleh Local baru ditambal oleh artikel Global. |
| **Type** | Positive Case |
| **Coverage** | Fully Automated |

*   **Manual Testing Steps**
    1. Set `localized=mix` dengan IP area yang stok artikel lokalnya **diketahui pasti** (misal stok lokal = 12 dari 20 yang diminta).
    2. Hit endpoint dan hitung proporsi artikel Local vs Global pada response.
*   **Expected Manual Result**: 12 artikel Local (sesuai stok maksimal yang tersedia) + 8 artikel Global sebagai penambal sisa kuota — total tetap 20.
*   **Automation Validation**:
    *   `MixModeValidator` ➔ Sama seperti `CompositionValidator` pada project sebelumnya: PASS jika `local_count == min(local_stock_available, requested)` DAN `global_count == requested - local_count`.
    *   FAIL jika Local tidak diprioritaskan (misal proporsi Global lebih dominan padahal stok Local sebenarnya cukup).
*   **Observation Points**: Pola ini konsisten dengan `HOMEPAGE_MAX_PERSONALIZED` di project Recommendation Engine — artinya module `CompositionValidator` yang sudah ada berpotensi **di-reuse langsung** untuk validasi TC ini, cukup ganti label `personalized/top-news` menjadi `local/global`.

---

### TC-011: Explicit IP Override Testing
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-011 |
| **Scenario** | Memastikan parameter `ip_address` yang dikirim eksplisit oleh QA benar-benar dipakai backend, bukan IP asli dari header request. |
| **Type** | Positive Case |
| **Coverage** | Fully Automated |
| **Test Data** | `ip_address=114.10.x.x` (area Pontianak) dikirim dari environment testing yang IP aslinya berbeda (misal server CI di Jakarta). |

*   **Manual Testing Steps**
    1. Kirim request dari mesin/CI dengan IP asli berbeda, sertakan `ip_address=<IP Pontianak>` secara eksplisit.
*   **Expected Manual Result**: `user_location` pada response = "Pontianak", bukan lokasi IP asli pengirim request.
*   **Automation Validation**:
    *   `GeoFallbackValidator` ➔ PASS jika `user_location` cocok dengan `ip_address` parameter, bukan IP header asli.
*   **Observation Points**: Jika backend tetap memakai IP header (mengabaikan parameter `ip_address`), seluruh automation testing berbasis matrix IP (TC-006 s/d TC-008) menjadi tidak valid karena tidak bisa disimulasikan dari CI/staging.

---

### TC-012: Redis Fallback Detection (DB Down Simulation)
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-012 |
| **Scenario** | Saat database utama (MongoDB/Qdrant) down atau timeout, backend harus otomatis mengalihkan response ke cache Redis dengan artikel default. |
| **Type** | Edge Case |
| **Coverage** | Semi Automated |
| **Preconditions** | Environment staging memungkinkan simulasi DB down/timeout (perlu koordinasi dengan tim Backend/DevOps). |

*   **Manual Testing Steps**
    1. Koordinasi dengan Backend untuk mematikan/mem-block sementara koneksi MongoDB/Qdrant di staging.
    2. Hit endpoint `page_mode=latest` selama kondisi tersebut aktif.
*   **Expected Manual Result**: Response tetap `status: true`, HTTP 200 (tidak error), namun konten berasal dari cache.
*   **Automation Validation**:
    *   `ResilienceValidator` ➔ Mendeteksi `type: "default-value"` pada artikel. Ditandai `FALLBACK DETECTED` (informational).
*   **Observation Points**: Fully-automated sulit dilakukan rutin karena perlu trigger manual DB down; automation hanya bisa mendeteksi *jika* fallback sedang aktif saat itu, bukan men-trigger-nya sendiri — karena itu statusnya Semi Automated.

---

### TC-013: Source Handling (Web vs Mobile App, Struktur Identik)
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-013 |
| **Scenario** | **[Klarifikasi Backend]** Struktur response Web (`source_url` terisi) dan Mobile App (`source_url` kosong) **sama persis** — parameter `source_url` tidak mengubah bentuk/field JSON, kemungkinan hanya dipakai untuk keperluan internal (tracking/analytics) di sisi backend. |
| **Type** | Positive Case |
| **Coverage** | Fully Automated |

*   **Manual Testing Steps**
    1. Hit endpoint tanpa `source_url` (kondisi Mobile).
    2. Hit endpoint yang sama persis (IP, `client_id`, parameter lain identik) dengan `source_url` diisi domain Web.
*   **Expected Manual Result**: Kedua response punya struktur field yang identik (key JSON sama), dan idealnya isi artikelnya pun konsisten (bukan dua feed yang berbeda).
*   **Automation Validation**:
    *   `SourceValidator` ➔ PASS jika `set(keys_response_web) == set(keys_response_mobile)` untuk setiap artikel. FAIL jika ditemukan field yang hanya muncul di salah satu kondisi.
*   **Observation Points**: Karena sudah dikonfirmasi seharusnya identik, kalau automation mendeteksi ada field yang beda (misal field tracking khusus Web ikut nyelip ke response Mobile atau sebaliknya), ini murni bug — bukan lagi masalah spesifikasi yang belum jelas.

---

### TC-014: Latency Validation
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-014 |
| **Scenario** | Memastikan `execution_time` response berada di bawah threshold performa yang ditetapkan. |
| **Type** | Negative Case |
| **Coverage** | Fully Automated |

*   **Automation Validation**:
    *   `LatencyValidator` ➔ PASS jika `execution_time` < batas di `config.py`; WARNING jika mendekati batas toleransi; FAIL jika melebihi.
*   **Observation Points**: Perhatikan apakah latency naik signifikan saat mode `localized=true` dengan fallback cascade panjang (city→province→region→country) dibanding mode `global` — indikasi query cascade kurang optimal.

---

### TC-015: No-Recency-Limit Behavior (Artikel Lama Tetap Tampil)
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-015 |
| **Scenario** | Memastikan fitur Latest Feed TIDAK menerapkan batas umur artikel (recency limit) — berbeda dari endpoint Recommendation reguler yang punya batas 3/30 hari. Artikel lama tetap boleh tampil selama urutannya benar dan level geo-nya sesuai (misal saat fallback cascade ke daerah dengan sedikit publikasi baru). |
| **Type** | Positive Case |
| **Coverage** | Fully Automated |

*   **Manual Testing Steps**
    1. Pilih IP daerah dengan frekuensi publikasi artikel lokal rendah (jarang ada berita baru).
    2. Hit endpoint `localized=true`.
*   **Expected Manual Result**: Jika artikel terbaru di daerah tersebut sudah berumur lebih dari 3/30 hari, artikel tersebut **tetap muncul** (tidak di-FAIL-kan oleh recency), selama urutan sortingnya tetap benar.
*   **Automation Validation**:
    *   `RecencyValidator` **TIDAK diaktifkan** untuk `page_mode=latest` (berbeda dari endpoint Recommendation reguler). Automation hanya memvalidasi `SortingValidator`, bukan `RecencyValidator`.
*   **Observation Points**: Jika QA menemukan automation men-generate FAIL karena "artikel terlalu lama", cek apakah validator recency reguler ikut ter-load secara tidak sengaja pada test suite Latest Feed — ini adalah *false positive* bug pada automation, bukan pada backend.

---

### TC-016: Complex Edge Case - Geo-Fallback Consistency Under Concurrency
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-016 |
| **Scenario** | Beberapa request bersamaan dari region yang sama (misal saat traffic tinggi) berpotensi menyebabkan *race condition* pada penentuan level fallback, menghasilkan anchor yang tidak konsisten antar request. |
| **Type** | Anomaly |
| **Coverage** | Manual Required |

*   **Manual Testing Steps (Load Test Tool / Postman Runner)**
    1. Kirim 10-20 request paralel dengan `ip_address` dan `client_id` yang sama persis dalam rentang waktu berdekatan.
    2. Bandingkan `Anchor Level` dan komposisi hasil antar response.
*   **Expected Manual Result**: Seluruh response konsisten menghasilkan anchor level dan proporsi artikel yang sama (dengan toleransi kecil karena data bisa berubah antar detik).
*   **Automation Validation**: Tidak dicakup oleh skrip statis karena automation existing bersifat *single-shot per request*, tidak didesain untuk uji concurrency.
*   **Observation Points**: Jika ditemukan anchor level berbeda-beda secara signifikan antar request yang identik (misal kadang "city" kadang "province"), lapor sebagai *Data Anomaly* / *Race Condition* ke tim Backend.

---

### TC-017: Complex Edge Case - Redis Fallback Content Staleness
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-017 |
| **Scenario** | Saat mekanisme Redis fallback aktif dalam waktu lama (DB utama down berkepanjangan), artikel cache default berpotensi menjadi basi (*stale*) karena tidak di-refresh. |
| **Type** | Anomaly |
| **Coverage** | Manual Required |

*   **Manual Testing Steps**
    1. Saat kondisi `type: "default-value"` terdeteksi aktif (lihat TC-012), catat `publish_date` artikel-artikel dalam cache.
    2. Bandingkan dengan tanggal hari pengujian.
*   **Expected Manual Result**: Idealnya cache tetap relatif baru (di-refresh berkala), meskipun statusnya "fallback".
*   **Automation Validation**: Automation hanya mendeteksi *keberadaan* fallback (`FALLBACK DETECTED`), tidak menilai kualitas/usia konten cache — perlu judgment QA manual.
*   **Observation Points**: Jika artikel dalam mode fallback berumur berbulan-bulan, eskalasi ke tim Infra/Backend untuk menjadwalkan refresh cache Redis secara berkala, bukan hanya saat insiden terjadi.

---

## 3. KLARIFIKASI BACKEND (RESOLVED)

| Pertanyaan | Jawaban Backend | Dampak ke Testing |
| :--- | :--- | :--- |
| Threshold minimum per level geo | **Tidak ada threshold.** Logic-nya *exact backfill*: sisa kuota yang tidak terpenuhi di satu level langsung ditambal persis dari level berikutnya (city → province → region → country). | TC-007 & TC-008 naik presisi assertion-nya: validasi berbasis *gap-filling* matematis, bukan lagi "< 20". |
| Rasio mode `mix` | **Mengikuti pola backfill** yang sama seperti Personalized vs Top-News di project Recommendation Engine reguler — Local diprioritaskan penuh dulu, sisanya ditambal Global. | TC-010 naik status dari Semi Automated → **Fully Automated**; module `CompositionValidator` existing berpotensi di-*reuse*. |
| Perbedaan struktur Web vs Mobile | **Struktur response identik.** `source_url` tidak mengubah bentuk JSON. | TC-013 naik status dari Semi Automated → **Fully Automated**; assertion cukup bandingkan `keys` kedua response harus sama persis. |
