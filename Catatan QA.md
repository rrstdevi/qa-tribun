## **Catatan QA: Recommendation Engine TribunX**

### **1\. Aturan Rekomendasi Artikel**

* **Localized:** Rekomendasi artikel menggunakan filter berdasarkan **IP Address** (lokasi pengguna) dan **History** (minat topik pengguna).  
* **Global:** Rekomendasi artikel hanya difilter berdasarkan **History** pengguna tanpa mempertimbangkan lokasi (mencakup skala lokal hingga internasional).

### **2\. Pengujian Halaman Beranda (Home Page Testing)**

#### **Ekspektasi Hasil:**

* **Komposisi Konten:** Menampilkan total maksimal **20 artikel** dengan proporsi **50% Artikel Personalized (10)** dan **50% Top News (10)**.  
* **Mekanisme Backfill:** Jika kuota artikel *personalized* tidak mencapai 50%, sisa slot harus diisi (*backfill*) menggunakan artikel *Top News*.  
* **Performa (Latency):** Waktu respons harus **$\\le 200$ ms**. Toleransi hingga **0,3 detik** diperbolehkan secara situasional tergantung kondisi koneksi.  
* **Hierarki Lokasi (Localized Mode):** Penentuan urutan peringkat (*ranking*) dilakukan secara berjenjang: **City (Kota) $\\rightarrow$ Province (Provinsi) $\\rightarrow$ Region (Wilayah)**.  
* **Urutan Tampilan:** Tidak ada urutan tetap; artikel *Top News* dan *Personalized* dapat muncul secara acak di posisi 1-20.  
* **Deduplikasi:** Menggunakan *Similarity Threshold* untuk mencegah judul serupa. Nilai ambang batas (*sweet spot*) pengujian adalah **60** dan **70**.  
* **Diversitas Konten (MMR Lambda):** Menggunakan parameter MMR Lambda (rentang 0-1) untuk mengatur variasi konten.  
  * Semakin tinggi nilai, hasil semakin personal sesuai riwayat pengguna.  
  * *Sweet spot* pengujian: **0,50 – 0,70**.  
* **Batas Waktu Publikasi (Recency):**  
  * **Top News:** Diambil secara bertahap dari rentang waktu 12 jam \-\> 1 hari \-\> maksimal 3 hari. Status **Fail** jika artikel \> 3 hari muncul.  
  * **Personalized:** Diambil dari rentang 12 jam \-\> 1 hari \-\> 3 hari \-\>  8 hari \-\> maksimal 30 hari. Status **Fail** jika artikel \> 30 hari muncul.  
* **Logika Topik (User Interest):**  
  * Rekomendasi didasarkan pada topik dari **3 artikel terakhir** yang diklik pengguna.  
  * Topik yang paling sering diklik akan mendominasi hasil, kecuali parameter MMR diatur rendah.  
* **Aturan Eksklusi (Click History):**  
  * Artikel yang sudah pernah diklik tidak boleh direkomendasikan kembali selama topiknya masih berada dalam rentang 3 klik terakhir.  
  * Jika topik sudah bergeser keluar dari rentang 3 klik terakhir, artikel tersebut boleh muncul kembali.  
  * **Pengecualian:** Jika topik masuk kembali ke rentang 3 besar setelah sempat keluar, artikel yang sudah pernah diklik sebelumnya tetap **dilarang muncul**. Jika muncul, status **Fail**.  
* **Filter Konten (Blacklist):** Artikel dengan kata kunci seperti *"lirik lagu", "chord", "kunci jawaban", "zodiak", "lowongan kerja"*, dll tidak boleh muncul.

### **3\. Pengujian Detail Artikel (Detail Article Testing)**

#### **Ekspektasi Hasil:**

* **Komposisi Konten:** Menampilkan total 8 artikel, terdiri dari **7 artikel serupa (Similar to Topic)** dan **1 artikel Top News**.  
* **Performa (Latency):** Waktu respons harus **$\\le 200$ ms** (toleransi 0,3 detik).  
* **Hierarki Lokasi:** Mengikuti urutan **City $\\rightarrow$ Province $\\rightarrow$ Region**.  
* **Urutan Tampilan:** Posisi artikel *Top News* dan *Personalized* bersifat acak (posisi 1-8).  
* **Batas Waktu Publikasi:**  
  * **Top News:** Maksimal 3 hari.  
  * **Personalized:** Maksimal 30 hari.  
* **Izin Konten Khusus:** Berbeda dengan beranda, pada halaman detail artikel, konten seperti *"lirik lagu", "zodiak", "lowongan kerja"*, dll. **diperbolehkan** untuk muncul.  
* **Anti-Looping:** Sistem tidak boleh menampilkan pola rekomendasi berulang (*ping-pong* A-B-A-B). Artikel yang baru saja dibaca tidak boleh muncul dalam daftar rekomendasi selanjutnya di halaman detail artikel yang artikelnya di klik.

