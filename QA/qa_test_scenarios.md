# Manual & Automation Testing Scenario
## Recommendation Engine QA - TribunX

Dokumen ini merangkum seluruh *Test Case* (Skenario Pengujian) untuk memvalidasi algoritma *Recommendation Engine* TribunX. 

**Konsep Pengujian Hibrida (Hybrid Testing):**
Pengujian ini menggabungkan **Manual Testing** dan **Automation Testing** ke dalam satu siklus (*pipeline*) yang saling terkait:
1.  **Manual Testing (via Simulator)** bertindak sebagai **Trigger/State Builder**. QA akan menggunakan simulator untuk melakukan aksi seperti membaca artikel, melakukan klik, atau berpindah lokasi, guna membentuk *User History* / *Context*.
2.  **Automation Testing (via Script)** bertindak sebagai **Validator**. Script akan menarik respon JSON (berdasarkan *state* yang dibentuk manual sebelumnya) dan memastikan aturan bisnis (komposisi, lokasi, batas waktu) berjalan tanpa pelanggaran.

---

## 1. DAFTAR TEST CASE (SCENARIO LIST)

### 1.1 Core Behavior & Personalization
| ID | Skenario | Tipe | Coverage |
| :--- | :--- | :--- | :--- |
| **TC-001** | Cold Start User | Edge Case | Fully Automated |
| **TC-002** | Heavy Personalized User | Positive | Semi Automated |
| **TC-003** | Anti-Looping Recommendation | Negative | Manual Required |
| **TC-004** | Repeated Click Behavior | Negative | Manual Required |
| **TC-005** | Category Dominance (MMR Effect) | Edge Case | Semi Automated |
| **TC-006** | Realtime Recommendation Adaptation | Positive | Manual Required |
| **TC-015** | Personalized vs Top-News Composition | Positive | Fully Automated |

### 1.2 Localization & Geography
| ID | Skenario | Tipe | Coverage |
| :--- | :--- | :--- | :--- |
| **TC-008** | Personalized Localization | Positive | Fully Automated |
| **TC-009** | Global Recommendation | Positive | Fully Automated |
| **TC-010** | Localization Mismatch (Anchor vs IP) | Edge Case | Fully Automated |
| **TC-011** | Dataset Hierarchy Validation | Negative | Fully Automated |
| **TC-012** | Multilingual & Normalization Mapping | Edge Case | Fully Automated |

### 1.3 Rules, Constraints & Anomalies
| ID | Skenario | Tipe | Coverage |
| :--- | :--- | :--- | :--- |
| **TC-007** | Backfill Top News Validity | Edge Case | Fully Automated |
| **TC-013** | Duplicate Article Detection | Negative | Fully Automated |
| **TC-014** | Recency Validation (Stale Articles) | Negative | Fully Automated |
| **TC-016** | Complex: Personalized Cross-Region | Edge Case | Fully Automated |
| **TC-017** | Complex: Cold Start With Illegal Personalized | Anomaly | Fully Automated |

---

## 2. DETAIL TEST CASES

### TC-001: Cold Start User
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-001 |
| **Scenario** | Memastikan *user* baru yang tidak memiliki *history* klik akan mendapatkan 100% berita *Top News* terbaru (nasional/regional). |
| **Type** | Edge Case |
| **Coverage** | Fully Automated |
| **Objective** | Engine tidak memaksakan *personalisasi* fiktif kepada pengguna yang profil datanya masih nol. |
| **Preconditions** | App *Cache* dibersihkan. Device ID di Simulator diganti dengan ID yang benar-benar baru. |
| **Test Data** | `client_id` = `test-new-999`, IP = `140.x.x.x` (Jakarta) |

*   **Manual Testing Steps (Simulator)**
    1. Masukkan `client_id` baru di Simulator. Pastikan fitur *Get History* me-*return* *null* atau kosong.
    2. Set Dropdown "Homepage Feed" ke `Localized`.
    3. Eksekusi request API (Get Recommendation).
*   **Expected Manual Result**: Feed layar menampilkan artikel populer terkini. Tidak ada blok kategori yang mendominasi.
*   **Automation Validation**:
    *   `Composition Validation` ➔ Mengecek `top-news` rasio.
    *   `Localization Validation` ➔ FAIL (Tidak ada jangkar / anchor level yang tercapai karena ketiadaan `personalized`).
    *   `Cold Start Validation` ➔ **PASS**. (Secara pintar menganulir FAIL lokasi karena sadar ini user baru).
*   **Observation Points**: QA harus mengamati status `COLD START USER` pada HTML Report. Jika status berubah menjadi `FAIL` di Automation, berarti Engine "bocor" (memberi tag `personalized` ke user tanpa *history*).

---

### TC-002: Heavy Personalized User
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-002 |
| **Scenario** | Memastikan ketahanan komposisi Engine ketika disuapi histori yang sangat monopolistik (satu topik). |
| **Type** | Positive Case |
| **Coverage** | Semi Automated |
| **Objective** | Memastikan bahwa engine bisa mengenali pola ekstrim tanpa melanggar batas *maksimal* kuota *personalized*. |
| **Preconditions** | User memiliki *history* yang padat. |
| **Test Data** | `client_id` = `test-sport-01` |

*   **Manual Testing Steps (Simulator)**
    1. Lakukan klik/baca pada 20 artikel bertema "Sepak Bola" (Liga 1, Persib, dll) via Simulator.
    2. Tarik API Homepage Recommendation untuk *client_id* tersebut.
*   **Expected Manual Result**: Mayoritas feed menampilkan konten sepak bola di slot *personalized*.
*   **Automation Validation**:
    *   `HomepageRulesValidator` ➔ **PASS**. Meskipun minat *user* sangat spesifik, jumlah tipe `personalized` dalam respon **TIDAK BOLEH** melebihi `HOMEPAGE_MAX_PERSONALIZED` (misal maks 10 dari 20 artikel). Sisanya wajib diisi oleh `top-news`.
*   **Observation Points**: Indikasi Bug: Jika QA mendapati laporan komposisi Automation mengembalikan angka 15 *Personalized* dan 5 *Top-News*, berarti fungsi *Backfill Limitation* Backend rusak.

---

### TC-003: Anti-Looping Recommendation
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-003 |
| **Scenario** | User melakukan *Refresh* terus-menerus tanpa klik untuk melihat perilaku *shuffling* engine. |
| **Type** | Negative Case |
| **Coverage** | Manual Required |
| **Objective** | Menghindari *fatigue* (kebosanan) pengguna dengan tidak menampilkan susunan artikel statis berkali-kali. |
| **Preconditions** | User memiliki profil sejarah standar. |

*   **Manual Testing Steps (Simulator)**
    1. Buka Simulator, hit `Homepage Recommendation`.
    2. *Screenshot* / catat ID artikel urutan 1 sampai 5.
    3. Tarik layar (Simulasi *Pull-to-refresh*) / Hit ulang Endpoint setelah jeda 10 detik.
    4. Ulangi 3 kali.
*   **Expected Manual Result**: Posisi artikel harus berubah (di-*shuffle*), atau artikel yang sudah tampil lebih dari 2 kali harus di-*drop* ke bawah dan diganti artikel baru.
*   **Automation Validation**: Tidak di-cover oleh skrip statis saat ini karena keterbatasan *stateless request*.
*   **Observation Points**: Jika urutan 1-5 terus-menerus menampilkan ID yang sama persis setelah 5 kali refresh, lapor ke Backend bahwa *Impression Penalty* atau *Anti-Looping Weight* tidak berfungsi.

---

### TC-004: Repeated Click Behavior (Filter Bubble)
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-004 |
| **Scenario** | User (atau bot) mengklik satu artikel yang SAMA berulang-ulang kali. |
| **Type** | Negative Case |
| **Coverage** | Manual Required |
| **Objective** | Algoritma harus melakukan de-duplikasi atau *throttling* *weight* untuk satu *item_id* yang sama di dalam histori. |
| **Preconditions** | Simulator mampu menyuntikkan ID secara spesifik ke *history*. |

*   **Manual Testing Steps (Simulator)**
    1. Suntikkan *item_id* = `1104407` (Berita Kriminal) sebanyak 15 kali ke riwayat klik user secara beruntun.
    2. Refresh rekomendasi Homepage.
*   **Expected Manual Result**: Rekomendasi tidak boleh *crash*. Bobot kriminalitas meningkat wajar, tidak naik ke level *infinity*.
*   **Automation Validation**: `Duplicate Article Detection` ➔ **PASS** (Memastikan API tidak memberikan artikel ganda akibat *history* ganda tersebut).
*   **Observation Points**: Indikasi anomali: Jika beranda memuat artikel duplikat atau merespon dengan HTTP 500 (karena *math overflow* di *machine learning*).

---

### TC-005: Category Dominance (MMR Effect)
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-005 |
| **Scenario** | Menguji bekerjanya *Maximal Marginal Relevance* untuk menghambat dominasi satu rubrik absolut. |
| **Type** | Edge Case |
| **Coverage** | Semi Automated |
| **Objective** | Menciptakan keragaman (*diversity*) informasi di *feed* pembaca. |

*   **Manual Testing Steps (Simulator)**
    1. Ubah setting `MMR_LAMBDA` ke angka pinalti yang drastis (contoh 0.2 atau 0.8).
    2. Bentuk sejarah *user* yang sangat monoton (100% berita selebriti).
    3. Generate rekomendasi.
*   **Expected Manual Result**: Terdapat penyisipan berita tipe lain (misal Ekonomi atau Olahraga) akibat paksaan parameter MMR.
*   **Automation Validation**:
    *   `Composition Validation` ➔ PASS.
*   **Observation Points**: Skrip Automation akan memastikan `top-news` tetap hadir, tapi keberagaman spesifik (`diversity`) dari blok `personalized` harus diverifikasi secara visual oleh QA. Jika isinya selebriti semua padahal MMR aktif, berarti filter MMR backend mati.

---

### TC-006: Realtime Recommendation Adaptation
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-006 |
| **Scenario** | User mendadak beralih ketertarikan (dari Sepakbola ke Resep Masakan). |
| **Type** | Positive Case |
| **Coverage** | Manual Required |

*   **Manual Testing Steps (Simulator)**
    1. Masukkan *client_id* dengan profil "Sepakbola". Buka feed.
    2. Inject *history* baru: Baca 4 berita "Resep Masakan".
    3. Hit ulang *Homepage Recommendation*.
*   **Expected Manual Result**: Algoritma langsung bereaksi *real-time*. Rekomendasi memasak masuk ke posisi teratas *Personalized*, mendorong berita bola ke urutan bawah.
*   **Observation Points**: Mengukur Latensi adaptasi. Jika setelah di-klik rekomendasi tidak berubah sama sekali, *realtime data-streaming* mungkin bermasalah.

---

### TC-008: Personalized Localization Consistency
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-008 |
| **Scenario** | Memastikan bahwa untuk *request* bermode `Localized`, *Engine* menyajikan artikel yang konsisten dengan titik kordinat/IP user. |
| **Type** | Positive Case |
| **Coverage** | Fully Automated |
| **Preconditions** | Mode pada simulator = `Localized`. IP yang digunakan berada di dataset (contoh: Pontianak, Kalimantan Barat). |

*   **Manual Testing Steps (Simulator)**
    1. Set IP Address di profil Simulator (contoh: `114.10.x.x` area Pontianak).
    2. Set Dropdown Feed = `Localized`. Get Data.
*   **Expected Manual Result**: Artikel bernuansa berita lokal Pontianak / Kalimantan mendominasi *feed*.
*   **Automation Validation**:
    *   `LocalizationValidator` (Anchor Selection) ➔ **PASS**. (Menemukan *Region: kalimantan* atau *City: pontianak* dengan dominasi > 50%).
    *   `LocalizationValidator` (Dataset Validation) ➔ **PASS**. (Membandingkan *Anchor* dengan IP `114.10.x.x` dan status cocok).
*   **Observation Points**: Ini adalah fungsi krusial. Perhatikan HTML Report bagian **Consistency Score**. Jika persentase hierarki sering berada di angka ~51% (sangat rawan gagal), berarti akurasi filter lokasi backend perlu di-tuning (*radius* pencarian diperketat).

---

### TC-009: Global Recommendation Mode
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-009 |
| **Scenario** | Memastikan parameter `Global` mengabaikan *IP-address* dan menyajikan *Personalized* murni secara nasional. |
| **Type** | Positive Case |
| **Coverage** | Fully Automated |

*   **Manual Testing Steps (Simulator)**
    1. Gunakan IP Pontianak (seperti di TC-008).
    2. Ubah Dropdown Feed = `Global`. Get Data.
*   **Expected Manual Result**: Rekomendasi lokal Pontianak hilang/tersamar, berganti menjadi rekomendasi yang lebih luas (Nasional).
*   **Automation Validation**:
    *   `LocalizationValidator` ➔ **SKIPPED / PASS**. Validator akan melihat mode `Global` dan secara by-design tidak akan memaksakan hukuman jika artikel datang dari berbagai wilayah acak.
*   **Observation Points**: Bandingkan output `Localized` dan `Global` untuk ID yang sama. Jika keduanya menghasilkan daftar berita yang 100% sama, maka API flag *Localized* tidak bekerja di backend.

---

### TC-010: Localization Mismatch Edge Case
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-010 |
| **Scenario** | *Engine* memuntahkan lokasi *Anchor* Jawa Tengah, tapi IP address pengguna berasal dari Sulawesi. |
| **Type** | Edge Case |
| **Coverage** | Fully Automated |

*   **Automation Validation**:
    *   `Dataset Validation` ➔ **FAIL**. Report akan mencetak: `Result: FAIL (Anchor contradicts IP Dataset)`.
*   **Observation Points**: QA harus mengamati Raw JSON. Jika hal ini terjadi, kemungkinan *Engine ML* salah melakukan *Geolocation Mapping*, atau IP Address tersebut diregistrasikan ke area yang salah di *Provider* internet. Lapor sebagai *Data Anomaly*.

---

### TC-011: Dataset Hierarchy Validation (City/Prov/Region)
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-011 |
| **Scenario** | Memastikan logika penurunan level (*Hierarchy Downgrade*) bekerja. Ketika `City` gagal mendominasi (>50%), `Province` gagal, maka `Region` harus diangkat sebagai *Anchor*. |
| **Type** | Positive Case |
| **Coverage** | Fully Automated |

*   **Automation Validation**:
    *   `LocalizationValidator` ➔ PASS dengan pesan `Selected Anchor Level: region`.
*   **Observation Points**: Buka detail *Consistency Score* di HTML. Jika City = 20%, Prov = 30%, Region = 60%, maka wajar Region menjadi pemenang. Ini menandakan berita tersebar di satu pulau, bukan di satu kota spesifik.

---

### TC-012: Multilingual & Normalization Mapping
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-012 |
| **Scenario** | Backend mengembalikan string `province: "West Java"` atau `"  DKI Jakarta "`, automation harus bisa memahaminya sebagai `"jawa barat"` dan `"dki jakarta"`. |
| **Type** | Edge Case |
| **Coverage** | Fully Automated |

*   **Automation Validation**:
    *   `LocalizationValidator` ➔ PASS. Proses *Normalization* berhasil men-translasi teks.
*   **Observation Points**: Jika Automation me-return `FAIL`, QA harus memeriksa detail Mismatch. Jika *Anchor* adalah "jawa barat" tapi artikel di-FAIL-kan karena "West Java", berarti *mapping* kamus di `location_utils.py` QA kurang lengkap. Tambahkan ke kamus.

---

### TC-013: Duplicate Article Detection
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-013 |
| **Scenario** | Memastikan satu respon rekomendasi tidak menampilkan Artikel ID ganda. |
| **Type** | Negative Case |
| **Coverage** | Fully Automated |

*   **Automation Validation**:
    *   `Duplicate Detection` ➔ FAIL.
*   **Observation Points**: Jika status merah muncul, ini murni *Critical Bug* pada Backend/Algoritma, karena mereka gagal membuang array ganda sebelum men-serialize JSON.

---

### TC-014: Recency Validation (Stale Articles)
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-014 |
| **Scenario** | Mengecek ketatnya batas waktu publikasi (kebaruan) konten. Top-News (max 3 hari) dan Personalized (max 30 hari). |
| **Type** | Negative Case |
| **Coverage** | Fully Automated |

*   **Automation Validation**:
    *   `Recency Validation` ➔ FAIL.
*   **Observation Points**: HTML Report akan mengurai detail tiap artikel. QA akan melihat `Age: 45 days | Max: 30 days | FAIL`. Ini adalah bukti otentik bahwa algoritma memasukkan berita "basi" (*Stale Content*) ke dalam daftar rekomendasi aktif. Harus di-escalate ke tim ML.

---

### TC-016: Complex Edge Case - Personalized Cross-Region
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-016 |
| **Scenario** | Mode `Localized` aktif. IP berada di Jakarta. Tapi sistem merekomendasikan artikel bertipe `personalized` dari region "Papua" (karena *user history*-nya pernah membaca berita papua). |
| **Type** | Edge Case |
| **Coverage** | Fully Automated |

*   **Automation Validation**:
    *   `LocalizationValidator` (Anchor) ➔ "jawa", `Dataset` ➔ PASS (Jakarta).
    *   Artikel "Papua" ➔ `Result: FAIL (NOT DETECTED)`.
*   **Observation Points**: Tipe *Personalized* TIDAK DIIZINKAN berada di luar *Anchor Region* pada mode Localized. Ini membuktikan bahwa meskipun artikel tersebut sangat diminati *user*, *Constraint Localized* harusnya mem-blokir berita papua tersebut dan memindahkannya ke mode *Global* saja.

---

### TC-017: Complex Edge Case - Cold Start With Illegal Personalized
| Field | Detail |
| :--- | :--- |
| **Test Case ID** | TC-017 |
| **Scenario** | User baru (*Cold Start*), tidak ada history. Namun Backend API malah mengembalikan 1 artikel bertipe `personalized` secara misterius bersama 19 `top-news`. |
| **Type** | Anomaly |
| **Coverage** | Fully Automated |

*   **Automation Validation**:
    *   `ColdStartValidator` ➔ **FAIL**. HTML Report akan mencetak pesan: `Localized inconsistency detected but personalized article still exists. ID: [xxx]`.
*   **Observation Points**: Ini adalah pencegahan *false-positive*. Sistem dengan cerdas menyimpulkan bahwa ini BUKAN skenario pengguna baru normal, melainkan Engine bocor (membuat personifikasi fiktif). Bug level: *Medium*.
