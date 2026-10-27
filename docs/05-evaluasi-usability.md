# 05 - Evaluasi Usability

Dokumen ini memisahkan dengan tegas **apa yang sudah diuji** dan **apa yang masih harus diuji dengan pengguna nyata**.

## A. Pemeriksaan otomatis (sudah dijalankan)

Skrip: [`scripts/uji_antarmuka/uji_ui.py`](../scripts/uji_antarmuka/uji_ui.py) (Playwright + Chromium) terhadap prototype dengan server API tiruan [`mock_server.py`](../scripts/uji_antarmuka/mock_server.py), yang meniru aturan backend (stok, status, kembalian). Hasil terakhir: **43 dari 43 pemeriksaan lolos**.

| Kelompok | Yang diperiksa |
|---|---|
| Alur fungsional (HP) | 9 menu tampil; menu habis nonaktif; filter kategori; pencarian dan pesan "tidak ada yang cocok"; tanda stok menipis; lencana keranjang; total benar; keranjang bertahan setelah muat ulang; buat pesanan lalu otomatis pindah tab; uang kurang ditandai langsung; kembalian dihitung langsung; bayar lalu status berubah; laporan harian bertambah; pesanan selesai; filter Aktif/Semua |
| Pencegahan kesalahan | Dialog batal: fokus awal di "Kembali"; memilih "Kembali" tidak membatalkan; konfirmasi membatalkan dan mengembalikan stok |
| Tata letak | Tidak ada gulir horizontal pada 390 (HP), 1024 (tablet), 1440 px (desktop), dan pada 320/360/390 px di ketiga tab HP |
| Area sentuh | Semua kontrol terlihat berukuran >= 44 px pada tiga ukuran layar |
| Aksesibilitas dasar | Setiap tombol punya nama aksesibel; indikator fokus keyboard terlihat (garis 3 px) |
| Keyboard | Enter di kolom uang mengonfirmasi pembayaran; Esc menutup dialog tanpa efek samping |
| Stabilitas | Tidak ada error di konsol browser selama alur lengkap |
| Kontras warna | 17 pasangan warna lolos (`python scripts/kontras.py`, lihat `docs/03`) |

Cara mengulang:

```bash
pip install playwright && playwright install chromium
python scripts/uji_antarmuka/mock_server.py frontend 8099 &
python scripts/uji_antarmuka/uji_ui.py design/screenshots
```

Uji integrasi backend sungguhan (tiga layanan + gateway) ada di `scripts/smoke_test.py` dan dijalankan di GitHub Actions.

## B. Evaluasi heuristik oleh pengembang

Temuan nyata selama pengembangan, dan perbaikannya:

| # | Temuan | Ditemukan lewat | Dampak | Perbaikan |
|---|---|---|---|---|
| 1 | Kolom "Uang diterima" memakai `step="500"` dengan `min="1"`, sehingga browser menganggap Rp 50.000 tidak valid dan menolak mengirim formulir | Uji otomatis (pembayaran macet) | **Parah:** kasir tidak bisa membayar dengan nominal bulat | Atribut `step` dihapus |
| 2 | Label "Meja (opsional)" terbungkus dua baris di desktop sehingga kolom tidak sejajar dengan "Nama pelanggan" | Pemeriksaan tangkapan layar | Kosmetik | Label dipersingkat; "opsional" pindah ke placeholder |
| 3 | Rincian harga di keranjang tablet ("Rp 12.000 x 1 = Rp 12.000") terpotong ke baris kedua | Pemeriksaan tangkapan layar | Sedang: sulit dibaca | Menampilkan subtotal saja; rincian "n x harga" hanya bila jumlah lebih dari 1 |

Keterbatasan metode ini: dilakukan oleh pembuat aplikasi, sehingga cenderung melewatkan masalah yang hanya terlihat oleh orang baru. Karena itu bagian C penting.

## C. Uji dengan pengguna (belum dilakukan, diisi sebelum presentasi)

**Peserta:** 3-5 orang (teman sekelas atau kasir sungguhan) yang belum pernah melihat aplikasi. Lima peserta umumnya cukup untuk menemukan sebagian besar masalah usability yang menonjol (Nielsen).
**Cara:** pandu dengan skenario berikut tanpa menjelaskan cara memakainya; amati dan catat; jangan membantu kecuali peserta macet lebih dari 1 menit.

| Skenario | Tugas | Target |
|---|---|---|
| S1 | Buat pesanan 2 Kopi Susu dan 1 Pisang Goreng atas nama "Budi", meja 4 | <= 60 detik, tanpa salah |
| S2 | Bayar pesanan itu tunai dengan uang Rp 50.000 dan sebutkan kembaliannya | <= 30 detik |
| S3 | Pelanggan mengganti pikiran: buat pesanan baru lalu batalkan sebelum dibayar | Tidak ada salah klik |
| S4 | Cari menu "teh" dan tambahkan ke keranjang | <= 20 detik |
| S5 | Cari tahu berapa pendapatan hari ini | <= 10 detik |

**Lembar pengamatan** (satu baris per peserta per skenario):

| Peserta | Perangkat | Skenario | Berhasil? | Waktu (dtk) | Salah ketuk | Catatan / kutipan |
|---|---|---|---|---|---|---|
| P1 | | S1 | | | | |
| P1 | | S2 | | | | |
| P2 | | S1 | | | | |

**Kuesioner SUS** (skala 1 = sangat tidak setuju sampai 5 = sangat setuju):

1. Saya ingin sering memakai aplikasi ini.
2. Aplikasi ini terasa rumit tanpa perlu.
3. Aplikasi ini mudah dipakai.
4. Saya butuh bantuan orang teknis untuk memakainya.
5. Fitur-fiturnya terpadu dengan baik.
6. Ada terlalu banyak ketidakkonsistenan.
7. Kebanyakan orang akan cepat mempelajarinya.
8. Aplikasi ini sangat merepotkan.
9. Saya merasa percaya diri memakainya.
10. Saya harus belajar banyak hal dulu sebelum bisa memakainya.

**Menghitung skor SUS:** butir ganjil: skor - 1; butir genap: 5 - skor; jumlahkan semua, lalu kalikan 2,5 (hasil 0-100). Rata-rata umum sekitar 68; di atas itu dianggap baik.

| Peserta | Skor SUS |
|---|---|
| P1 | |
| P2 | |
| **Rata-rata** | |

## D. Temuan dari uji pengguna dan tindak lanjut (isi setelah uji)

| Masalah yang terlihat | Seberapa sering (n dari N) | Tingkat keparahan (1-4) | Perbaikan yang diusulkan | Status |
|---|---|---|---|---|
| | | | | |
