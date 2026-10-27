# 03 - Design System

Lembar visual: [`design/design-system.svg`](../design/design-system.svg). Semua nilai di bawah adalah *design token* yang dipakai langsung di `frontend/css/style.css` (bagian `:root`).

## 1. Warna

| Token | Nilai | Peran |
|---|---|---|
| `--bg` | `#f7f1e8` | Latar halaman (krem hangat, nuansa kopi susu) |
| `--surface` | `#ffffff` | Panel, dialog, kolom isian |
| `--kartu` | `#fffaf4` | Kartu menu |
| `--ink` | `#2b1d14` | Teks utama |
| `--muted` | `#5f5045` | Teks sekunder |
| `--brand` / `--brand-dark` | `#6f4e37` / `#55392a` | Aksi utama dan hover (cokelat kopi) |
| `--ok` | `#1f6b2a` | Status Sudah dibayar |
| `--warn` | `#8a5200` | Menunggu bayar, stok menipis |
| `--bad` | `#a8201a` | Batal, aksi berbahaya |
| `--done` | `#4a5560` | Status Selesai |
| `--focus` | `#0b57d0` | Cincin fokus keyboard |
| `--line` / `--line-strong` | `#d9c9b8` / `#8c7a6a` | Garis hias / garis kolom isian dan chip |

### Bukti kontras (WCAG 2.x)

Dihasilkan oleh `python scripts/kontras.py` (teks normal >= 4,5 : 1; komponen antarmuka >= 3 : 1). Skrip ini juga dijalankan di GitHub Actions, sehingga perubahan warna yang melanggar akan menggagalkan build.

| Teks utama di latar halaman | `#2b1d14` | `#f7f1e8` | 14.51 : 1 | 4.5 : 1 | Lolos |
| Teks utama di panel putih | `#2b1d14` | `#ffffff` | 16.30 : 1 | 4.5 : 1 | Lolos |
| Teks utama di kartu menu | `#2b1d14` | `#fffaf4` | 15.70 : 1 | 4.5 : 1 | Lolos |
| Teks sekunder di panel putih | `#5f5045` | `#ffffff` | 7.72 : 1 | 4.5 : 1 | Lolos |
| Teks sekunder di latar halaman | `#5f5045` | `#f7f1e8` | 6.88 : 1 | 4.5 : 1 | Lolos |
| Teks sekunder di kartu menu | `#5f5045` | `#fffaf4` | 7.44 : 1 | 4.5 : 1 | Lolos |
| Teks putih di tombol utama | `#ffffff` | `#6f4e37` | 7.44 : 1 | 4.5 : 1 | Lolos |
| Teks putih di tombol utama (hover) | `#ffffff` | `#55392a` | 10.47 : 1 | 4.5 : 1 | Lolos |
| Teks tombol sekunder (cokelat di putih) | `#6f4e37` | `#ffffff` | 7.44 : 1 | 4.5 : 1 | Lolos |
| Teks tombol batal (merah di putih) | `#a8201a` | `#ffffff` | 7.28 : 1 | 4.5 : 1 | Lolos |
| Lencana: Dibayar (putih di hijau) | `#ffffff` | `#1f6b2a` | 6.57 : 1 | 4.5 : 1 | Lolos |
| Lencana: Menunggu (putih di oranye tua) | `#ffffff` | `#8a5200` | 6.39 : 1 | 4.5 : 1 | Lolos |
| Lencana: Dibatalkan (putih di merah) | `#ffffff` | `#a8201a` | 7.28 : 1 | 4.5 : 1 | Lolos |
| Lencana: Selesai (putih di abu-abu biru) | `#ffffff` | `#4a5560` | 7.61 : 1 | 4.5 : 1 | Lolos |
| Garis tepi kolom isian di panel putih | `#8c7a6a` | `#ffffff` | 4.11 : 1 | 3 : 1 | Lolos |
| Cincin fokus di panel putih | `#0b57d0` | `#ffffff` | 6.39 : 1 | 3 : 1 | Lolos |
| Cincin fokus di latar halaman | `#0b57d0` | `#f7f1e8` | 5.69 : 1 | 3 : 1 | Lolos |

## 2. Tipografi

Font sistem (`system-ui`, Segoe UI, Roboto, ...): tanpa unduhan, cepat dimuat, dan akrab di tiap platform.

| Peran | Ukuran / tebal |
|---|---|
| Judul halaman | 20 px / 700 |
| Judul bagian | 18 px / 700 |
| Teks isi dan kolom isian | 16 px / 400 (16 px di input mencegah iOS memperbesar layar otomatis) |
| Teks bantu | 14 px |
| Keterangan | 12-13 px, hanya info tambahan |

## 3. Ukuran dan jarak

| Token | Nilai | Alasan |
|---|---|---|
| `--target` | 48 px | Ukuran kontrol utama (tombol +/-, kolom isian, aksi di kartu pesanan). Batas mutlak semua target sentuh: 44 px (chip, tombol kecil) |
| Tombol utama besar | 56 px | Aksi terpenting, paling sering ditekan |
| `--gap` | 16 px | Jarak antar panel |
| `--radius` | 12 px | Sudut membulat, kesan ramah |

## 4. Komponen dan statusnya

| Komponen | Varian | Keterangan |
|---|---|---|
| Tombol | Utama (isi cokelat), Sekunder (garis cokelat), Bahaya (garis/isi merah), Teks | Satu tombol utama per layar |
| Chip filter | Aktif (`aria-pressed=true`, isi cokelat) / tidak aktif | Kategori menu, filter pesanan, nominal cepat |
| Kartu menu | Normal, di keranjang (lencana jumlah), stok menipis (teks oranye "Sisa n"), habis (redup dan nonaktif) | Menu habis memakai teks, bukan hanya warna |
| Lencana status | Menunggu bayar `○`, Sudah dibayar `●`, Selesai `✔`, Dibatalkan `✕` | Selalu ikon + teks |
| Dialog | Pembayaran, Konfirmasi | `<dialog>` bawaan: fokus terkunci, Esc menutup |
| Notifikasi | Biasa, galat (merah) | `role="status"`, hilang otomatis 4 detik |
| Fokus | Garis biru 3 px dengan jarak 2 px | Terlihat di latar terang maupun krem |

## 5. Pola interaksi

- **Aksi merusak** (batal pesanan, kosongkan keranjang): selalu lewat dialog konfirmasi, dengan fokus awal pada *Kembali*.
- **Umpan balik**: setiap aksi berakhir dengan notifikasi atau perubahan yang terlihat.
- **Keadaan kosong**: selalu memberi langkah berikut ("Pilih menu", "Tampilkan semua").
