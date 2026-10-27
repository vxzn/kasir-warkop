# 02 - Analisis HCI (Interaksi Manusia dan Komputer)

Dokumen ini memetakan prinsip HCI ke fitur yang **benar-benar ada** di prototype (`frontend/`). Setiap klaim bisa diperiksa di kode atau dilihat di `design/screenshots/`.

## 1. Pendekatan user-centric

Prinsip yang dipakai: kenali pengguna dan tugasnya, rancang alur sependek mungkin, cegah kesalahan lebih dulu daripada memperbaikinya, dan jangan menghukum pengguna yang salah ketuk. Pengguna utama adalah kasir yang bekerja cepat, sering berdiri, dan kadang tangannya sibuk (lihat `01-riset-pengguna.md`).

## 2. Evaluasi terhadap 10 heuristik Nielsen

| # | Heuristik | Wujud di prototype | Berkas |
|---|---|---|---|
| 1 | Visibilitas status sistem | Notifikasi setelah tiap aksi; lencana status berikon + teks; teks "Memuat menu...", tombol berubah "Membuat pesanan..."; spanduk saat offline; daftar pesanan dan laporan menyegar tiap 5 detik | `js/app.js`, `index.html` |
| 2 | Kesesuaian dengan dunia nyata | Bahasa Indonesia sehari-hari ("Uang pas", "Kembalian", "Tandai selesai"); format `Rp 12.000`; kategori warkop (Kopi, Minuman, Makanan) | `js/app.js` |
| 3 | Kendali dan kebebasan pengguna | Tombol +/- jumlah, Kosongkan keranjang, Batalkan pesanan (stok kembali), Tutup dialog, tombol Esc menutup dialog; keranjang tersimpan walau halaman dimuat ulang | `js/app.js` |
| 4 | Konsistensi dan standar | Satu design system: tombol utama/sekunder/bahaya selalu sama; satu pola konfirmasi untuk aksi merusak | `css/style.css`, `docs/03` |
| 5 | Pencegahan kesalahan | Menu habis dinonaktifkan; jumlah dibatasi stok; "Buat Pesanan" nonaktif saat keranjang kosong; konfirmasi batal dengan **fokus awal pada pilihan aman**; peringatan "Uang kurang" sebelum mengirim; klik ganda dicegah saat memproses; server menolak stok minus | `js/app.js`, `services/` |
| 6 | Mengenali, bukan mengingat | Menu tampil sebagai kartu; chip kategori; pencarian; nominal cepat (Uang pas, 50.000, ...) | `js/app.js` |
| 7 | Fleksibilitas dan efisiensi | Nominal cepat; filter + cari untuk pengguna mahir; formulir pembayaran bisa dikirim dengan Enter; navigasi keyboard penuh | `index.html` |
| 8 | Desain estetis dan minimalis | Satu aksi utama per layar; di HP hanya satu bagian tampil sekaligus; info sekunder berwarna redup tapi tetap terbaca | `css/style.css` |
| 9 | Membantu pulih dari galat | Pesan galat berbahasa jelas ("Stok Kopi Susu tidak cukup", "Tidak dapat terhubung ke server..."); tombol *Coba lagi* bila menu gagal dimuat; backend membatalkan perubahan sebagian (stok dikembalikan) | `js/app.js`, `services/pesanan` |
| 10 | Bantuan dan dokumentasi | **Parsial:** ada petunjuk di tempat ("Pilih menu dulu...", keadaan kosong). Belum ada halaman bantuan atau tur pengenalan | - |

## 3. Hukum dan prinsip ergonomi

| Prinsip | Penerapan |
|---|---|
| **Hukum Fitts** (target besar dan dekat lebih cepat ditekan) | Semua target sentuh >= 44 px (kontrol utama 48-56 px, termasuk Bayar/Batalkan di kartu pesanan); kartu menu >= 96 px tingginya; navigasi bawah di HP berada di zona ibu jari |
| **Hukum Hick** (pilihan sedikit = keputusan cepat) | Filter kategori mempersempit menu; satu tombol utama per layar |
| **Hukum Miller** (memori kerja terbatas) | Informasi dikelompokkan: Menu, Keranjang, Pesanan sebagai tiga bagian terpisah |
| **Hukum Jakob** (pengguna terbiasa pola lazim) | Keranjang dan tab bawah mengikuti pola aplikasi pesan makanan yang sudah dikenal |
| **Pengungkapan bertahap** | Pembayaran dibuka di dialog tersendiri; kolom uang diterima hanya muncul untuk tunai |
| **Umpan balik segera** | Kembalian dihitung saat mengetik, tanpa menunggu klik |

## 4. Aksesibilitas

| Aspek | Penerapan | Bukti |
|---|---|---|
| Kontras warna | 17 pasangan warna dihitung dengan rumus WCAG 2.x, semua lolos | `python scripts/kontras.py`, `docs/03` |
| Tidak mengandalkan warna saja | Status memakai ikon + teks | `design/design-system.svg` |
| Navigasi keyboard | Semua kontrol bisa dijangkau dengan Tab; indikator fokus 3 px; tautan "Langsung ke menu" | uji otomatis (`docs/05`) |
| Pembaca layar | Setiap tombol bernama (`aria-label`); `aria-live` untuk notifikasi dan daftar; dialog bersemantik; fokus dikelola | uji otomatis memeriksa tombol tanpa nama |
| Gerakan | `prefers-reduced-motion` dihormati | `css/style.css` |
| Layar sempit dan ukuran teks | Teks 16 px; tidak ada gulir horizontal pada lebar 320, 360, dan 390 px di ketiga tab | uji otomatis (`docs/05`) |

## 5. Nilai pelayanan (integrasi nilai keilmuan)

- **Mengurangi beban orang lain:** kembalian dan total dihitung otomatis agar kasir tidak terbebani dan pelanggan tidak menunggu.
- **Memaafkan kesalahan:** semua kesalahan umum (salah ketuk, uang kurang, stok habis) punya jalan keluar yang jelas.
- **Inklusif:** kontras tinggi, target besar, dan dukungan pembaca layar membuat aplikasi layak dipakai lebih banyak orang, termasuk saat tangan basah atau pencahayaan buruk.
- **Jujur terhadap pengguna:** pesan galat apa adanya, dan status pembayaran tidak berubah sebelum server memastikan.

## 6. Keterbatasan yang diketahui

- Belum diuji dengan **pembaca layar sungguhan** (NVDA/VoiceOver/TalkBack); hanya pemeriksaan semantik otomatis.
- Belum ada login kasir, mode gelap, atau halaman bantuan.
- Saat offline, aplikasi terbuka dari cache tetapi **tidak bisa membuat atau membayar pesanan** (sengaja, agar stok dan pembayaran tidak ganda).
- Persona belum divalidasi lewat wawancara nyata (`docs/01`).
