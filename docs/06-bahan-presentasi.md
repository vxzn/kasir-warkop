# 06 - Bahan Presentasi (Collaborative Learning)

Durasi saran: 8-10 menit + tanya jawab. Siapkan dua tab browser: aplikasi (`http://localhost:8080`) dan GitHub.

## 1. Alur presentasi

| Menit | Bagian | Isi inti | Bukti yang ditunjukkan |
|---|---|---|---|
| 0:00 | Masalah | Warung kopi kecil: pesanan tertukar, stok tidak sinkron, kembalian lambat | `docs/01` |
| 1:00 | Solusi dan integrasi sistem | Tiga layanan (menu, pesanan, pembayaran) + gateway + frontend berjalan sebagai satu kesatuan | Diagram arsitektur di `README.md` |
| 2:00 | Pengguna | Kasir sebagai pengguna utama; persona (disebutkan sebagai hipotesis) | `docs/01` |
| 3:00 | Desain | Wireframe tiga ukuran dan design system | `design/*.svg` |
| 4:30 | **Demo langsung** | Skenario di bagian 2 | Aplikasi berjalan |
| 7:00 | HCI dan aksesibilitas | Heuristik Nielsen, hukum Fitts, kontras 17/17 lolos | `docs/02`, `docs/03` |
| 8:00 | Evaluasi dan keterbatasan | 43 pemeriksaan otomatis, bug yang ditemukan dan diperbaiki, hasil uji pengguna | `docs/05` |
| 9:00 | Penutup | Pengembangan lanjutan; nilai melayani pengguna | - |

## 2. Skenario demo (jalankan berurutan)

1. **Responsif:** buka aplikasi di jendela lebar, lalu kecilkan jendela (atau pakai mode perangkat di DevTools: F12, ikon HP) hingga navigasi bawah muncul.
2. **Pesan cepat:** klik Kopi Susu dua kali, filter *Makanan*, klik Pisang Goreng. Tunjukkan lencana jumlah dan total.
3. **Pencegahan kesalahan:** tunjukkan menu habis yang nonaktif; coba tambah melebihi stok untuk memunculkan notifikasi.
4. **Buat pesanan:** isi nama dan meja, *Buat Pesanan*. Tunjukkan status "Menunggu bayar" dan stok yang berkurang.
5. **Bayar:** *Bayar*, ketik uang kurang untuk memperlihatkan peringatan, lalu ketuk *Rp 50.000* untuk memperlihatkan kembalian langsung.
6. **Integrasi:** buka tab *Semua*, perlihatkan status berubah "Sudah dibayar" dan laporan "Hari ini" bertambah. Jelaskan: pembayaran memberi tahu layanan pesanan secara otomatis.
7. **Memaafkan kesalahan:** buat pesanan lagi, klik *Batalkan*; tunjukkan fokus awal pada *Kembali*, lalu konfirmasi dan perlihatkan stok kembali.
8. **Keyboard:** tekan Tab untuk memperlihatkan cincin fokus.
9. **Cadangan bila demo gagal:** tampilkan tangkapan layar di `design/screenshots/`.

Sebelum presentasi: `docker compose down -v` lalu `docker compose up -d --build` agar data mulai bersih.

## 3. Pemetaan ke capaian pembelajaran

| Sub-CPMK / ketentuan tugas | Wujud dalam repository |
|---|---|
| Desain App multi-platform | Responsif 3 ukuran + PWA (`docs/04`, `design/wireframe-*.svg`) |
| HCI/UX, user-centric | `docs/01`, `docs/02`, `docs/03`, `docs/05` |
| Antarmuka ergonomis dan fungsional antar platform | Target sentuh >= 44 px, navigasi sesuai perangkat, uji otomatis 43 pemeriksaan |
| Portofolio desain | `design/` (wireframe, design system, tangkapan layar) |
| Dokumen pendukung | `docs/01` sampai `docs/06` |
| Aset struktur kode (prototype frontend) | `frontend/` |
| Mengintegrasikan beberapa sistem menjadi satu | `services/` + `gateway/` + `docker-compose.yml` |
| Sistem berjalan sebagai satu kesatuan | `docker compose up`, `scripts/smoke_test.py`, GitHub Actions |
| Dikumpulkan sebagai satu repository GitHub | Tautan repository di LMS |

## 4. Kemungkinan pertanyaan dan jawaban

**Mengapa web responsif/PWA, bukan aplikasi native?**
Satu basis kode untuk semua platform, tanpa toko aplikasi, mudah di-deploy ke cloud. Kekurangannya akses perangkat keras terbatas; jika butuh cetak struk Bluetooth, hybrid (Flutter/React Native) bisa jadi langkah berikutnya (`docs/04`).

**Bagaimana tiga layanan tetap konsisten kalau satu gagal?**
Layanan pesanan mengembalikan stok bila pembuatan tagihan gagal. Layanan pembayaran mengembalikan status tagihan bila layanan pesanan tidak bisa dihubungi. Pembayaran ganda ditolak.

**Apakah desain ini sudah diuji dengan pengguna?**
Pemeriksaan otomatis dan evaluasi heuristik sudah dilakukan (`docs/05` bagian A dan B). Uji pengguna: *(isi sesuai kenyataan: jumlah peserta dan skor SUS bila sudah dilakukan; bila belum, katakan belum dan tunjukkan rencananya)*.

**Dari mana angka kontras itu?**
Dihitung dengan rumus WCAG 2.x di `scripts/kontras.py`, dijalankan otomatis di CI.

**Apa kelemahan sistem ini?**
Belum ada login, belum diuji dengan pembaca layar sungguhan dan perangkat fisik, offline hanya untuk membuka aplikasi (`docs/02` bagian 6, `docs/04` bagian 7).

**Siapa pengguna utamanya?**
Kasir. Persona adalah hipotesis awal; panduan wawancara untuk memvalidasinya ada di `docs/01`.

## 5. Daftar siap-presentasi

- [ ] Docker berjalan; `docker compose up -d --build` selesai tanpa galat
- [ ] Data bersih; menu tampil lengkap
- [ ] Tab GitHub terbuka pada repository dan README
- [ ] Sudah mencoba skenario demo satu kali penuh
- [ ] Bagian hasil uji pengguna di `docs/05` terisi atau dinyatakan belum
- [ ] Tahu jawaban untuk pertanyaan di bagian 4
