# TribunX Recommendation Engine QA Automation
## Technical & Architecture Documentation

Dokumen ini adalah rujukan teknis komprehensif untuk *Automation Testing Framework* yang digunakan dalam memvalidasi akurasi, konsistensi, dan komposisi hasil dari *Recommendation Engine* TribunX.

---

## 1. OVERVIEW SISTEM

*   **Tujuan Automation Testing**: Menghilangkan proses manual QA dengan melakukan validasi masif dan otomatis terhadap respon API rekomendasi. Tujuannya memastikan *business logic* (komposisi artikel, batasan umur/recency, relevansi lokasi, dan batas performa) berjalan sempurna di *production*.
*   **Apa yang Sedang Diuji**: Algoritma AI/ML *Recommendation Engine* di dua skenario utama.
*   **Endpoint yang Diuji**:
    *   `/homepage/recommendation`: Rekomendasi untuk halaman depan aplikasi.
    *   `/article/recommendation`: Rekomendasi lanjutan yang muncul di bawah artikel yang sedang dibaca.
*   **Localized vs Global Concept**:
    *   `Localized`: Rekomendasi di-filter dan diurutkan berdasarkan parameter geografis dari IP pengguna (City, Province, Region).
    *   `Global`: Rekomendasi bersifat umum tanpa memprioritaskan geografi pembaca.
*   **Personalized vs Top-News Concept**:
    *   `Personalized / Similarity`: Artikel yang disajikan khusus untuk user tertentu berdasarkan *click history* (pada Homepage) atau kemiripan teks (pada Article Detail).
    *   `Top-News`: Berita populer yang bertindak sebagai *Backfill* (Penambal Kuota).
*   **Cold Start User Concept**: Simulasi pengguna yang benar-benar baru dan belum memiliki jejak *click history*, sehingga engine secara logika tidak bisa memberikan konten *personalized*.
*   **Mengapa Validation Ini Penting**: Engine rekomendasi adalah sistem deterministik-stokastik yang datanya bisa berubah setiap detik. Validasi statis tidak akan bekerja. Otomasi ini memastikan sistem tidak mendobrak "Pagar Pembatas Bisnis" terlepas dari output dinamis algoritma ML-nya.

---

## 2. ARSITEKTUR TESTING

Sistem ini memisahkan tugas pengumpulan data (Data Collector) dan pemvalidasian (Validation Engine) agar proses pengujian lebih terukur dan *reproducible*.

### Struktur Folder & Module
*   `Data Product/` (Root Directory)
    *   **`config.py`**: *Single Source of Truth*. Memuat seluruh parameter *tuning*, batas threshold, batas *recency*, *client_id*, dan daftar skenario (dinamis) yang akan diuji.
    *   **`test.py`**: Script **Data Collector**. Bertugas membaca *config*, men-generate payload URL, mengeksekusi iterasi matriks (Client × IP × Mode × Scenario), menembak API backend, dan membuang respons mentah JSON-nya ke dalam CSV.
    *   **`IP address data.csv`**: Dataset statis yang berisi pemetaan *IP Address* terhadap koordinat geografi aslinya (*ground truth*).
    *   **`output/`**: Folder hasil *dump* dari `test.py` berupa `testing_TIMESTAMP.csv`.
*   `Data Product/qa_automation/` (Engine Directory)
    *   **`main.py`**: *Entry Point* dari Validation Engine. Mengoordinasikan seluruh proses dari mulai *load data* hingga pembuatan report.
    *   **`data_loader.py`**: Script yang mengekstrak CSV mentah dan membongkar properti JSON string di dalamnya untuk disuntikkan ke dalam *Python Object* (Model).
    *   **`models.py`**: Mendefinisikan *Data Classes* (`TestRequest`, `ValidationResult`, `Article`) yang menjamin standardisasi struktur data di dalam *memory*.
    *   **`utils/location_utils.py`**: Berisi utilitas normalisasi (Translasi EN-ID dan sanitasi spasi).
    *   **`reporters/html_reporter.py`**: Modul yang merakit array hasil validasi menjadi antarmuka Dashboard HTML yang kaya fitur UX (*color grouping*, *collapsible detail*).
    *   **`validators/`**: Direktori modular. Setiap file (seperti `latency_val.py`, `localization_val.py`) merepresentasikan *Validation Rule* tunggal yang terisolasi (*Single Responsibility Principle*).

### Alur Data Global
`API Backend` ➔ `JSON Response` ➔ `CSV Dump (test.py)` ➔ `Parsed Objects (data_loader.py)` ➔ `Validator Pipeline` ➔ `HTML Reporter`.

---

## 3. PARAMETER YANG DITEST

Sistem membedah setiap *request* yang masuk melalui serangkaian lapisan validasi:

1.  **Latency Validation (`latency_val.py`)**
    *   *Tujuan*: Memastikan respon API cukup cepat.
    *   *Pass/Fail*: PASS jika latency < batas di `config.py`. WARNING jika di atas batas tapi di bawah toleransi maksimal. FAIL jika melebihi batas toleransi.
2.  **Article Count Validation (`rules_homepage.py` & `rules_article.py`)**
    *   *Tujuan*: Memastikan limit kuota *request* terpenuhi (misal 20 untuk homepage, 8 untuk article).
3.  **Composition Validation (`rules_homepage.py` & `rules_article.py`)**
    *   *Tujuan*: Mengecek keseimbangan rasio Backfill.
    *   *Logic*: Menjumlahkan tipe `personalized`/`similarity` dan tipe `top-news`.
    *   *Fail Criteria*: Gagal jika jumlah *personalized* melebihi ambang batas maksimal, atau rasio similarity dan top-news melenceng dari spesifikasi (contoh: Homepage maks 10 Personalized, Article wajib 7 Similarity & 1 Top-News).
4.  **Recency Validation (`recency_val.py`)**
    *   *Tujuan*: Memastikan kebaruan konten.
    *   *Logic*: Membandingkan `publish_date` tiap artikel dengan `datetime.now()`.
    *   *Fail Criteria*: `top-news` > 3 hari = FAIL. `personalized` > 30 hari = FAIL.
5.  **Blacklist Keyword (`rules_homepage.py`)**
    *   *Tujuan*: Memfilter topik tidak relevan (seperti zodiak, lirik lagu).
    *   *Fail Criteria*: Judul artikel terdeteksi oleh regex dari `config.BLACKLIST_REGEX_PATTERN`.
6.  **Duplicate ID Validation (`rules_*.py`)**
    *   *Tujuan*: Mencegah duplikasi rekomendasi. FAIL jika terdapat ID artikel yang ganda dalam satu respon.
7.  **Localization Validation (`localization_val.py`)**
    *   *(Detail dijelaskan pada Bab 4)*.
8.  **Cold Start Validation (`cold_start_val.py`)**
    *   *(Detail dijelaskan pada Bab 5)*.

---

## 4. LOCALIZATION VALIDATION FLOW

Skenario validasi lokasi dirancang untuk meniru kecerdasan fleksibel, mengakomodasi mekanisme "penambalan" (*backfill*).

1.  **Normalization**: Properti `city`, `province`, dan `region` milik setiap artikel dilewatkan ke fungsi normalisasi untuk membakukan teks (e.g. `West Java` diubah paksa ke `jawa barat`).
2.  **Majority Anchor Selection**:
    *   Sistem mencari **"Jangkar Hierarki"** (*Anchor*).
    *   Pencarian *Anchor* **HANYA** mempertimbangkan artikel bertipe `personalized` agar tidak terkontaminasi oleh bias `top-news`.
    *   Jika mayoritas artikel memiliki konsistensi `Region` 80%, sedangkan `Province` dan `City` hanya 20%, maka *Anchor* jatuh ke **Region**.
    *   *Syarat Utama*: Konsistensi harus **≥ 50%**.
    *   *Tie-Breaker*: Jika persentase seri, prioritas berurut `City > Province > Region`.
3.  **Dataset IP Validation**: *Anchor Value* yang terpilih disandingkan dengan pemetaan IP Address statis (`IP address data.csv`). Jika IP valid namun lokasinya bertolak belakang dengan *Anchor*, maka result = FAIL (Algoritma engine memberikan rekomendasi lokasi yang salah target).
4.  **Fallback / Backfill Mechanism (Pass/Fail Logic)**:
    *   Semua artikel dikomparasi melawan *Anchor Value* tersebut.
    *   Jika terjadi ketidakcocokan lokasi (*mismatch*):
        *   Bila artikel tersebut bertipe `top-news` ➔ **PASS (BACKFILL DETECTED)**. (Engine dimaafkan karena ini sedang melakukan penambalan sisa kuota).
        *   Bila artikel tersebut bertipe `personalized` ➔ **FAIL (NOT DETECTED)**. (Bocornya lokasi algoritma).

---

## 5. COLD START VALIDATION FLOW

Mengapa butuh skenario *Cold Start*? Karena *user* yang tidak memiliki riwayat penjelajahan akan membuat algoritma kesulitan menebak *Anchor Localization*.

*   **Deteksi**: `ColdStartValidator` bekerja di tahap "Cross-Validation" (Tahap 2). Ia mencari *request* bermode `Localized` yang sudah di-vonis `FAIL` oleh *Localization Validator* akibat ketiadaan *Anchor* (Selected Anchor = NONE).
*   **Logika Fallback Top-News**: Validator mengecek komposisi artikel pada request tersebut. Jika **100% artikelnya adalah `top-news`**, maka kecurigaan meningkat (ini user baru).
*   **Global Mode Cross Check**: Untuk memastikan ini adalah *Cold Start* asli dan bukan *bug* pada mode Localized, Validator melakukan kueri pencarian kepada data request bermode `Global` untuk IP dan Client ID yang persis sama. Jika di mode `Global` ia juga hanya mendapatkan `top-news`, vonisnya dijatuhkan.
*   **Result (PASS)**: Label `FAIL` dari validator lokasi akan dihapus (di-*override*) secara otomatis menjadi `PASS (COLD START USER)`.
*   **Result (FAIL)**: Jika *anchor* gagal ditemukan namun ternyata masih ada *nyempil* artikel `personalized`, berarti Engine memang benar-benar `FAIL` / Inkonsisten, bukan *Cold Start*.

---

## 6. CONFIGURATION SYSTEM (`config.py`)

File konfigurasi diletakkan di luar folder engine agar mempermudah QA mengatur *experimentation* tanpa menyentuh *core logic* engine.

**Parameter Configurable:**
*   `MMR_LAMBDA` & `SIMILARITY_THRESHOLD`: Parameter backend. Parameter ini di-*inject* secara *runtime* ke URL param agar algoritma benar-benar diuji sesuai batasan konfigurasinya.
*   `CLIENT_ID_CONFIG`: Sistem otomatis me-*looping* pembuatan Client ID. Anda bisa mengatur `mode = "range"` (test-001 s/d test-100) atau `mode = "list"` untuk menyuntikkan ID khusus (*edge-case*).
*   `ARTICLE_TEST_SCENARIOS`: Array dinamis. Mengakomodasi *multiple context testing*. Anda dapat menambahkan puluhan struktur objek berisi `item_id`, `site`, dan `article_title` tanpa perlu *copy-paste* blok kode pengetesan.

---

## 7. CLIENT ID & IP EXECUTION FLOW (OSPI Flow A)

Script *Data Collector* menggunakan arsitektur **OSPI Flow A**:
1.  **Looping Matriks**: Loop berjalan layaknya Cartesian Product. Untuk setiap 1 skenario, setiap 1 `client_id` (cth: `test-001`) akan menembak ke *seluruh daftar* `IP Address`.
2.  **Benefit**: Ini sangat vital agar satu *Client ID* (satu profile history) dapat mensimulasikan "pindah-pindah kota" menggunakan IP yang berbeda untuk menganalisa *Consistency Recommendation* versus *IP tracking*.
3.  **URL Building**: API Payload dirakit secara utuh dan hasil respon (HTTP 200) beserta JSON mentahnya langsung dikonversi menjadi baris-baris panjang (flattening) di dalam output CSV.

---

## 8. FLOW TESTING END-TO-END

*   **STEP 1 (Konfigurasi)**: Buka file `Data Product/config.py`.
*   **STEP 2 (Set Parameter & Skenario)**: Setel nilai `MMR`, `Threshold`, dan tambah/kurangi *list of dictionary* di `ARTICLE_TEST_SCENARIOS` (cth: mengubah `item_id` artikel rujukan).
*   **STEP 3 & 4 (Set Client/IP)**: Edit batasan `range` Client ID di *config*, dan pastikan array variabel `ip_addresses` di `test.py` memiliki IP yang relevan.
*   **STEP 5 (Jalankan API Hitter)**: Eksekusi `python test.py` dari direktori `Data Product/`.
*   **STEP 6 (Hasil Hitter)**: Skrip akan menembak backend ratusan kali dan memuntahkan `testing_2026MMDD_HHMMSS.csv` ke dalam folder `output/`.
*   **STEP 7 (Jalankan Validator)**: Eksekusi `python qa_automation/main.py`. Modul `main.py` akan otomatis mendeteksi CSV terbaru yang dibuat pada Step 6.
*   **STEP 8 (Validator Bekerja)**: Engine menyedot isi CSV, menginstansiasi *Class Validator*, membedah Raw JSON untuk mengkalkulasi komposisi, *mismatch*, batas umur, dan mendaftarkannya ke kelas reporter.
*   **STEP 9 (Hasil Final)**: Laporan matang divisualisasikan dalam bentuk antarmuka web, tersimpan sebagai `qa_automation/output/validation_report_YYYYMMDD_HHMMSS.html`.

---

## 9. REPORTING SYSTEM

Arsitektur pelaporan menggunakan metode *Decoupled* (Terpisah antara raw data dan visual).

*   **Raw CSV Output**: *The Source of Truth*. Sangat penting untuk keperluan audit dan pembacaan *machine-to-machine*.
*   **HTML Validation Report**: Layaknya Dashboard Investigasi QA.
    *   **Summary Metrics**: Akumulasi angka PASS, FAIL, WARNING, ERROR, dan COLD START USER dari seluruh *rules* yang dieksekusi.
    *   **Aggregation Logic Fix**: Sebelumnya terdapat *mismatch* karena summary dihitung per *request URL*, padahal 1 URL bisa memiliki 5 *rules* (ada yang PASS ada yang FAIL). Kini agregasi dihitung secara deterministik: 1 *ValidationResult* = 1 iterasi perhitungan di summary.
    *   **Row Grouping**: Tabel diurutkan berdasarkan `client_id` lalu `ip_address`, dipisah dengan *header bar* berwarna solid untuk kemudahan UX pembacaan data.

---

## 10. NORMALIZATION SYSTEM

*   **Tujuan**: Mencegah *false negative* akibat perbedaan bahasa atau *typo* sistem backend (e.g., backend menyimpan "West Java", sedangkan dataset QA menyimpan "jawa barat").
*   **Bagaimana Bekerja**: `location_utils.py` mengaplikasikan `strip().lower()` dan melakukan pencarian terhadap `LOCATION_MAPPING` dictionary. Semua string akan dimutasi menjadi *Canonical Value* (Nilai Baku) bahasa Indonesia.

---

## 11. FUTURE SCALABILITY

Arsitektur sistem dibangun di atas dasar OOP dan SOLID *principles*, membuka jalur lebar untuk fitur di masa depan:
*   **Modular Architecture**: Setiap fase dipecah secara OOP (Validator *base class*, Data Loader, Reporter).
*   **Integrasi RapidFuzz**: Validator baru cukup men-*inherit* `BaseValidator`, menulis fungsi `validate()` yang mengimplementasikan `rapidfuzz` untuk mengukur persentase kemiripan string `article.title` dengan *seed title*, lalu mendaftarkannya ke list `validators` di `main.py`. Tanpa mengubah core logic lain.
*   **Compare Antar Test Run**: Arsitektur yang berbasis CSV Timestamped memungkinkan kita untuk melakukan regresi: menjalankan `main.py` menunjuk pada CSV dari bulan lalu, dan membandingkannya dengan CSV hari ini.

---

## 12. FLOW DIAGRAM / EXECUTION DIAGRAM

```text
 ┌───────────────────┐        ┌───────────────────┐
 │   config.py       │        │  IP Dataset CSV   │
 │ (Global Settings) │        │  (Ground Truth)   │
 └─────────┬─────────┘        └─────────┬─────────┘
           │                            │
           ▼                            │
 ┌───────────────────┐                  │
 │    test.py        │                  │
 │ (Data Collector)  │                  │
 └─────────┬─────────┘                  │
           │ HTTP Matrix Requests       │
           ▼                            │
 ┌───────────────────┐                  │
 │  Backend Engine   │                  │
 │       API         │                  │
 └─────────┬─────────┘                  │
           │ JSON Response              │
           ▼                            │
 ┌───────────────────┐                  │
 │ testing_time.csv  │                  │
 │ (Raw Output Dump) │                  │
 └─────────┬─────────┘                  │
           │                            │
           ▼                            │
 ┌──────────────────────────────────────┴─┐
 │          qa_automation/main.py         │
 │          (Validation Pipeline)         │
 │                                        │
 │  1. data_loader.py (Parse JSON)        │
 │  2. Execute Standard Validators        │
 │     - Recency, Count, Duplicate        │
 │     - Localization (Anchor logic)      │
 │  3. Execute Cross-Validators           │
 │     - Cold Start Override Flow         │
 │  4. html_reporter.py (Aggregation)     │
 └─────────────────┬──────────────────────┘
                   │
                   ▼
 ┌───────────────────┐
 │ validation_report │
 │     .html         │
 │ (QA Dashboard UX) │
 └───────────────────┘
```

---

## 13. BEST PRACTICE

Untuk menjamin kualitas dan keberlangsungan skrip otomatisasi ini, ikuti panduan operasional berikut:

1.  **Cara Menjalankan Pengujian**: Jangan pernah men-hardcode data sensitif ke `test.py`. Biasakan mengubah konfigurasi skenario (ID Artikel, Region) dari `config.py`. Jalankan `test.py` terlebih dahulu untuk *data-mining*, tunggu selesai, baru jalankan `main.py`.
2.  **Cara Compare Testing Session**: Jangan menumpuk data. CSV yang dihasilkan ber-timestamp. Anda bisa membandingkan akurasi ML hari ini dengan kemarin hanya dengan membandingkan file CSV-nya atau men-*generate* ulang HTML report dengan CSV spesifik tersebut.
3.  **Cara Maintain Config**: Jika Backend mengadopsi struktur algoritma baru (contoh MMR diganti bobotnya), langsung buka blok *API Testing Parameters* di `config.py`. Jangan ubah apapun di engine.
4.  **Cara Maintain Dataset IP**: Pastikan `IP address data.csv` rutin diperbarui jika Tribun memiliki rentang demografi target IP baru (seperti ISP baru), agar sistem tak mencetak `SKIPPED`.
5.  **Cara Debugging Validation Fail**:
    *   Buka Validation Report (HTML). Cari baris dengan warna merah / "FAIL".
    *   Buka opsi drop-down **View / Hide Details**. Jangan hanya membaca alasannya, tapi bedah atribut `Raw JSON` yang dilampirkan validator.
    *   Jika *Raw JSON* terlihat benar tapi validator menyatakan salah, barulah inspeksi kode di folder `validators/`. Jika JSON memang melanggar aturan, lempar temuan tersebut ke tim Data Science/Backend.
6.  **Cara Membaca Report dengan Benar**: Abaikan agregasi *warning* yang bersifat informasional. Fokus utama harus diletakkan pada rasio *FAIL* terkait *Composition* dan *Localization*. Status `COLD START USER` sangat krusial dipantau untuk membuktikan bahwa Engine tidak "mabuk" ketika disodori pengguna kosong.

---

## 14. KETERBATASAN SISTEM (LIMITATIONS)

Automation framework yang telah dibangun sangat tangguh untuk verifikasi pasca-kalkulasi (*post-calculation verification*). Namun, mengingat sifat *Machine Learning* dan kompleksitas ekosistem data TribunX, terdapat batasan yang tidak dapat dijangkau oleh skrip otomatisasi ini:

*   **Automation Validator**: Validator hanya mengecek *output akhir* (JSON response). Ia tidak bisa melakukan verifikasi internal logika model *Machine Learning* itu sendiri (*black-box testing*).
*   **Raw CSV Based Validation**: Validasi dilakukan secara retrospektif (setelah data ditarik). Jika respon API berubah skemanya (JSON contract berubah drastis), *Data Loader* bisa *crash* sebelum divalidasi.
*   **Localization Validation**: Sangat bergantung pada data statis `IP address data.csv`. Jika *user* menggunakan VPN atau IP dinamis dari ISP yang belum terdaftar, validasi akan membuahkan status `SKIPPED`.
*   **Dataset Validation**: Dataset bersifat lokal dan tidak diperbarui secara *realtime* mengikuti pergantian *routing* IP jaringan nasional.
*   **Backfill Validation**: Sistem memaafkan *mismatch* lokasi jika tipe artikel adalah `top-news`. Namun, validator tidak dapat memverifikasi apakah `top-news` tersebut benar-benar artikel terpopuler di database, atau sekadar artikel acak.
*   **Cold Start Validation**: Sistem menyimpulkan *Cold Start* berdasarkan output API (100% Top-News). Validator tidak memiliki akses ke database *User Profile* untuk membuktikan apakah ID tersebut benar-benar tidak punya riwayat klik.
*   **Personalization Validation**: Automation memastikan format dan kuota terpenuhi. Namun, automation **tidak tahu** apakah artikel tersebut relevan dengan minat *user*. (Contoh: User suka Politik, tapi API memberi Otomotif dengan flag `personalized`. Automation menganggapnya PASS karena tipe-nya valid).
*   **Recommendation Engine Behavior**: Rekomendasi berubah dinamis mengikuti *trending*. Automation statis kesulitan memvalidasi konsistensi rekomendasi jangka panjang tanpa integrasi ke *data lake*.
*   **MMR Validation**: Automation melempar parameter MMR ke API, tapi tidak bisa mengkalkulasi ulang *Maximal Marginal Relevance* secara matematis untuk menjamin distribusi *diversity*-nya akurat.
*   **Similarity Validation**: Sistem memastikan label tipe `similarity` ada, namun tanpa *Semantic Text Matching* (RapidFuzz), ia tidak bisa membuktikan kemiripan isi konten secara riil.
*   **User History Validation**: Skrip ini bersifat *stateless*. Tidak menyimpan *click history* user di masa lalu untuk di-komparasi.
*   **Anti-Looping Validation**: Automation menembak 1 *request* per user di waktu spesifik. Ia tidak menyimulasikan *refresh* berulang untuk melihat apakah artikel yang sama diulang (*looping*).
*   **Click-History Validation**: Automation ini adalah simulasi pembacaan (Read). Dampak *trigger* sebuah *Click Event* (Write) terhadap rekomendasi selanjutnya tidak masuk dalam cakupan.
*   **Realtime Personalization Adaptation**: Kecepatan Engine mengubah rekomendasi sesaat setelah *user* melakukan aktivitas baru tidak bisa diuji.
*   **Backend, Data, & API Dependency**: Skrip sangat bergantung pada struktur *response* v1 (e.g. `recommended_article`). Jika *key* berubah, automation ini akan gagal tereksekusi.

---

## 15. KATEGORI COVERAGE TESTING

Berdasarkan limitasi di atas, pembagian area pengujian dipetakan ke dalam tiga tingkat *coverage* untuk memandu tim QA:

### A. Fully Automated
Komponen ini diuji 100% oleh skrip `main.py` secara presisi dan objektif:
*   **Latency / Response Time**: Pembatasan degradasi performa API.
*   **Duplicate Article ID**: Pencegahan artikel ganda di satu halaman.
*   **Recency**: Memastikan aturan batas umur rilis berita (Maks 3 hari / 30 hari).
*   **Localization Consistency**: Hierarki (City/Province/Region) wajib > 50%.
*   **Composition Ratio**: Rasio matematis *Backfill* (Top-News) terhadap *Personalized*.
*   **Blacklist Filter**: Eksekusi Regex untuk mencekal kata kunci ilegal.

### B. Semi-Automated
Komponen ini divalidasi oleh sistem, namun kepastian mutlaknya membutuhkan interpretasi logis:
*   **Similarity Validation**: Otomatisasi memastikan keberadaan flag `similarity`, tapi uji rasionalitas kemiripannya kelak bergantung pada implementasi skor *RapidFuzz* atau *Human Check*.
*   **MMR Diversity**: Keberagaman konten diregulasi otomatis oleh kuota komposisi, namun kualitas keragamannya diverifikasi visual.
*   **Backfill Handling**: Automation melabeli "BACKFILL DETECTED", tapi QA manual tetap perlu mengintip sesekali apakah berita penambal tersebut layak tampil.

### C. Manual Testing Required
Area yang **wajib** dikawal tim QA secara manual via *Simulator Testing* (App/Postman/Browser):
*   **Click History Personalization**: Memeriksa akurasi minat (*Interest Targeting*).
*   **Anti-Looping Behavior**: Menguji pola sistem saat di-*refresh* berulang kali.
*   **Realtime Personalization Adaptation**: Kecepatan AI mengubah haluan ketika minat user bergeser.
*   **Category Dominance**: Mencegah *echo chamber* akibat skor klik yang ekstrim.

---

## 16. MANUAL TESTING TEST CASES (SIMULATOR)

Skenario manual berikut dilakukan melalui Simulator dan terintegrasi/terkorelasi secara konseptual dengan skenario *Automation Testing*. (Tindakan pembentukan riwayat seperti *Get History* hanya ada di simulasi manual).

### 1. User Baru (Cold Start)
*   **Skenario**: Membuka aplikasi dengan Device ID baru yang belum memiliki riwayat *cache* (*Get History* bernilai kosong).
*   **Langkah Testing**:
    1. *Clear Cache* aplikasi / gunakan ID Simulator baru.
    2. Buka Homepage / Hit endpoint rekomendasi dengan IP lokal.
    3. Inspeksi jenis berita yang disajikan.
*   **Expected Result**:
    *   **Manual**: 100% berita adalah Nasional / Regional Terpopuler (Top-News). Tidak ada dominasi kategori minat spesifik.
    *   **Korelasi Automation**: Automation juga mengirimkan ID acak dan Engine Automation akan memvalidasi ini sebagai status `PASS (COLD START USER)`.

### 2. User Heavy Personalization
*   **Skenario**: Melatih AI secara intens dengan pola membaca yang sangat spesifik dan monopolistik (Contoh: Penggila Otomotif).
*   **Langkah Testing**:
    1. Hit API simulasi *Get History* dengan 10-15 artikel bertopik Otomotif secara beruntun.
    2. Tutup, lalu buka ulang Endpoint Recommendation (Homepage).
*   **Expected Result**:
    *   **Manual**: Berita otomotif/modifikasi akan menginvasi ruang porsi *Personalized*. Kategori lain tergeser ke bawah.
    *   **Korelasi Automation**: Skrip automation akan terus memantau *Composition Rules* dan akan berteriak `FAIL` jika komposisi otomotif (*personalized*) tersebut sampai merusak ambang batas maksimal kuota (misal memakan jatah *Backfill* secara ilegal).

### 3. Anti-Looping
*   **Skenario**: Mensimulasikan pengguna yang bosan dan menarik layar (*Pull-to-Refresh*) berulang-ulang tanpa melakukan klik sama sekali.
*   **Langkah Testing**:
    1. Buka Homepage, catat ID dari 5 artikel teratas.
    2. Tunggu 5-10 detik.
    3. Lakukan *Refresh* / Hit Endpoint rekomendasi untuk user tersebut lagi tanpa injeksi riwayat baru.
*   **Expected Result**:
    *   **Manual**: Engine harus melakukan rotasi (pengacakan *seed*) atau degradasi bobot bagi artikel yang "dilihat tapi diabaikan". Lima artikel pertama tadi tidak boleh mendominasi layar awal lagi.
    *   **Korelasi Automation**: Karena Automation hanya menembak 1 iterasi *point-in-time*, isu *looping* adalah titik buta (*blind spot*) otomasi, sehingga uji manual ini krusial.

### 4. Repeated Click (Filter Bubble Avoidance)
*   **Skenario**: Menyikapi perilaku tidak wajar di mana pengguna mengklik satu artikel yang **SAMA** berulang-ulang kali (biasanya bot atau user iseng).
*   **Langkah Testing**:
    1. Buka satu Berita Politik, kembali ke Homepage, buka lagi berita politik yang sama persis. Ulangi 10 kali.
    2. Cek susunan rekomendasi pada Homepage/Article.
*   **Expected Result**:
    *   **Manual**: Engine harus memiliki fungsi *throttling* atau deduplikasi *weight* di dalam *history vector*. Beranda tidak boleh rusak/crash karena bobot kata kunci satu artikel membesar hingga nilai *infinity*.

### 5. Category Dominance (MMR Effect Validation)
*   **Skenario**: Memastikan fitur pengereman algoritma berwujud *Maximal Marginal Relevance* (MMR) bekerja untuk mencegah penyajian ruang gema (*echo chamber*).
*   **Langkah Testing**:
    1. Set parameter MMR (`lambda_param`) ke nilai penalti yang tinggi di Simulator.
    2. Lakukan klik baca pada 15 berita tentang "Persib Bandung".
    3. Refresh Homepage.
*   **Expected Result**:
    *   **Manual**: Walaupun bobot "Persib" sangat kuat, layar **tidak boleh** berisi 100% Persib. Engine harus menyisipkan berita rubrik lain (Ekonomi, Kriminal, dsb.) di sela-selanya untuk menjamin keragaman (Diversity).

### 6. Realtime Recommendation Adaptation
*   **Skenario**: Menguji kepekaan (*responsiveness*) algoritma ketika pengguna mendadak mengalami "Pergeseran Minat" (*Interest Shift*).
*   **Langkah Testing**:
    1. Asumsikan *User* memiliki *click history* lama yang didominasi berita "Sepak Bola".
    2. *User* kemudian membaca 4 berita berturut-turut tentang "Tutorial Memasak/Resep" (Injeksi simulasi *history* baru).
    3. Kembali ke Homepage.
*   **Expected Result**:
    *   **Manual**: Engine bereaksi *realtime* (< beberapa detik). Artikel seputar makanan langsung menempati prioritas atas pada segmen *Personalized*, sementara sepak bola berangsur turun prioritasnya, membuktikan bahwa sinyal *Short-term Interest* sukses menimpa *Long-term Interest*.



## PARAMETER YANG DITEST

Sistem membedah setiap *request* yang masuk melalui serangkaian lapisan validasi:

1.  **Latency Validation (`latency_val.py`)**
    *   *Tujuan*: Memastikan respon API cukup cepat.
    *   *Pass/Fail*: PASS jika latency < batas di `config.py`. WARNING jika di atas batas tapi di bawah toleransi maksimal. FAIL jika melebihi batas toleransi.
2.  **Tag Recommendation Validation (`num_recommendation.py`)**
    *   *Tujuan*: Memastikan limit tag yang dimunculkan maksimal 20
3.  **Composition Validation (`rules_header_tag.py`)**
    *   *Tujuan*: Mengecek keseimbangan rasio Backfill.
    *   *Logic*: Mengetahui `similarity` tag dengan menampilkan maksimal 20 tag.
    *   *Fail Criteria*: Gagal jika jumlah tag jauh dari spesifikasi (contoh: Tag maks 20).
4.  **Popular Validation (`rules_page_mode.py`)**
    *   *Tujuan*: Memastikan daftar tag yang sedang trending (populer), dihitung secara dinamis berdasarkan artikel-artikel yang paling banyak dibaca/populer dalam 23 jam terakhir.
    *   *Logic*: Sistem query semua artikel yang punya engagement metric (views, klik, share, dll) dalam rentang waktu 23 jam terakhir.
    *   *Fail Criteria*: `popular` > 23 jam = FAIL.
5.  **NSFW Keyword (`rules_header_tag.py`)**
    *   *Tujuan*: Memfilter tag yang mengandung nsfw content seperti ["nsfw", "porn", "xxx", "sex-", "-sex", "telanjang"].
    *   *Fail Criteria*: Judul tag terdeteksi oleh regex dari `config.BLACKLIST_BANNED_TAG`.
6.  **Duplicate Tag Validation (`similarity_check*.py`)**
    *   *Tujuan*: Mencegah duplikasi tag. FAIL jika terdapat tag yang sama