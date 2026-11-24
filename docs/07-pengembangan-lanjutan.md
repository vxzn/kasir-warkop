# 07. Pengembangan lanjutan: autentikasi dan rekap penjualan

Permintaan dosen setelah presentasi:
1. Autentikasi untuk akses layanan (menu, pesanan, pembayaran) dari frontend, lewat layanan dan UI/UX.
2. Fungsi/layanan untuk rekap penjualan periode tertentu: harian, mingguan, bulanan.

## 1. Autentikasi

### Keputusan rancangan
| Pertanyaan | Keputusan | Alasan |
|---|---|---|
| Di mana login? | Layanan baru **auth** (layanan ke-4) dengan database sendiri (`auth.db`) | Sejalan dengan prinsip database-per-layanan |
| Bentuk kredensial | **JWT HS256** (header `Authorization: Bearer`), dibuat dengan pustaka standar Python | Tanpa dependensi tambahan; modul kecil yang bisa diuji penuh |
| Siapa memeriksa token? | **Setiap layanan** memeriksa sendiri tanda tangannya (`auth.py`, salinan identik) | Menu/pesanan/pembayaran tetap jalan walau layanan auth mati; tidak ada panggilan jaringan tambahan |
| Kata sandi | PBKDF2-HMAC-SHA256, 200.000 iterasi, garam acak per akun | Sandi asli tidak pernah disimpan |
| Peran | `kasir` dan `pemilik` (RBAC) | Rekap berisi data keuangan, hanya pemilik |
| Panggilan antar-layanan | Header rahasia `X-Service-Key`; gateway **mengosongkannya** untuk permintaan dari luar | Pesanan->Menu/Pembayaran dan Pembayaran->Pesanan tetap bisa jalan tanpa token pengguna, tetapi klien luar tidak bisa meniru |
| Brute force | 5 gagal dalam 5 menit -> blokir 60 detik per (nama pengguna, IP), HTTP 429 | Menekan tebak-tebakan sandi |

### Matriks akses
| Endpoint | Kasir | Pemilik | Antar-layanan |
|---|---|---|---|
| Login | publik | publik | - |
| Lihat menu | ya | ya | ya |
| Tambah menu | tidak (403) | ya | tidak |
| Ubah stok | tidak | ya | ya |
| Buat/lihat/batalkan pesanan | ya | ya | tidak |
| Ubah status ke SELESAI | ya | ya | tidak |
| Ubah status ke DIBAYAR | tidak | tidak | ya |
| Bayar, laporan hari ini | ya | ya | tidak |
| Buat/batalkan tagihan | tidak | tidak | ya |
| **Rekap penjualan** | tidak (403) | ya | tidak |
| Kelola akun | tidak | ya | tidak |

Tanpa token: 401. Token benar tetapi peran tidak berhak: 403.

### Sisi UI/UX
- Halaman **Masuk** tampil lebih dulu; menu, pesanan, dan navigasi disembunyikan sampai login berhasil.
- Pesan galat jelas dan netral ("Nama pengguna atau kata sandi salah", tanpa membocorkan mana yang salah), `role="alert"` untuk pembaca layar, tombol Tampilkan/Sembunyikan sandi, fokus awal di kolom nama pengguna.
- Header menampilkan nama dan peran, serta tombol **Keluar** (dengan konfirmasi karena keranjang dikosongkan).
- Token di `sessionStorage`; sesi bertahan saat muat ulang, hilang saat tab ditutup. Jika server menjawab 401 (token kedaluwarsa/rusak), pengguna dikembalikan ke login dengan pesan "Sesi berakhir".
- Antarmuka menyesuaikan peran: kasir tidak melihat tab/tombol Rekap (dan walau memanggil API langsung tetap 403).

## 2. Rekap penjualan

`GET /api/tagihan/rekap?periode=harian|mingguan|bulanan&tanggal=YYYY-MM-DD` (pemilik), dilayani **layanan pembayaran** karena data pembayaran ada di sana.

- **Harian**: satu tanggal, rincian per jam (24 baris).
- **Mingguan**: Senin-Minggu pada pekan yang memuat tanggal acuan, rincian per hari (7 baris).
- **Bulanan**: bulan kalender, rincian per tanggal.
- Hanya tagihan `LUNAS`; waktu WIB. Respons: total, jumlah transaksi, rata-rata, rincian, per metode, titik tertinggi, periode sebelumnya, dan persentase perubahan (`null` bila periode sebelumnya kosong).
- Logika dipisah di `services/pembayaran/rekap.py` (fungsi murni + satu query terindeks) supaya bisa diuji tanpa FastAPI.
- `DEMO_DATA=true` mengisi 60 hari data contoh (tagihan bernomor pesanan negatif, acak dengan seed tetap, hari ini tidak diisi) supaya rekap bisa didemokan. Data contoh **bukan data nyata**; matikan untuk penggunaan sungguhan.

UI Rekap: pilihan periode, panah geser periode + pemilih tanggal + "Hari ini" (tidak bisa maju ke masa depan), kartu ringkasan, grafik batang (teks alternatif untuk pembaca layar), rincian per metode, dan tabel rincian yang bisa dibuka sebagai alternatif grafik. Ada keadaan memuat, kosong, dan galat (dengan "Coba lagi").

## 3. Bukti pengujian (apa yang benar-benar dijalankan)

| Pengujian | Hasil | Catatan |
|---|---|---|
| `scripts/uji_unit/run_all.py` | 59 uji lolos | JWT (kedaluwarsa, dipalsukan, alg=none, peran), akun, hash, pembatas login, rekap (batas minggu/bulan, tahun kabisat, perbandingan) |
| `scripts/cek_modul_sama.py` | lolos | `auth.py` identik di 4 layanan |
| `scripts/cek_proteksi_route.py` | 25 endpoint lolos | Analisis AST: tiap endpoint punya aturan akses atau memang publik |
| `scripts/uji_antarmuka/uji_ui.py` (Playwright) | 84/84 lolos | Login, peran, rekap, keluar, token rusak, blokir login, 3 ukuran layar |
| `docker compose config` | valid | |
| `scripts/smoke_test.py` | **belum dijalankan di lingkungan pengembangan** | Perlu Docker; dijalankan di CI dan oleh Anda lewat `TUTORIAL.md` |

Server tiruan untuk uji UI memakai modul **asli** `auth.py`, `pengguna.py`, `pembatas.py`, `rekap.py`, dan `contoh_data.py`, tetapi bukan FastAPI, `main.py` layanan, atau Nginx. Artinya kabel FastAPI (dependency, urutan rute) dan `nginx.conf` baru terbukti secara statis dan lewat `docker compose config`; bukti penuhnya adalah `smoke_test.py` hijau setelah `docker compose up`.

## 4. Keterbatasan
Lihat bagian "Keterbatasan yang diketahui" di `README.md` (token tidak bisa dicabut, `sessionStorage`, pembatas di memori, HTTP lokal, rekap tanpa agregasi terjadwal).
