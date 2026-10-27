# 04 - Strategi Multi-platform dan Cloud App

## 1. Pilihan pendekatan

| Pendekatan | Kelebihan | Kekurangan | Cocok untuk kita? |
|---|---|---|---|
| **Web responsif + PWA** (dipilih) | Satu basis kode untuk HP, tablet, desktop; tanpa instalasi toko aplikasi; pembaruan langsung; mudah di-deploy di cloud | Akses perangkat keras terbatas (mis. printer Bluetooth); performa di bawah native untuk animasi berat | **Ya**: kasir butuh formulir dan daftar, bukan grafik berat |
| Native (Android/iOS terpisah) | Performa dan akses perangkat terbaik | Dua basis kode, proses rilis toko aplikasi, biaya lebih besar | Tidak untuk skala proyek ini |
| Hybrid (Flutter, React Native) | Satu kode, akses perangkat baik | Tambahan toolchain, ukuran aplikasi, kurva belajar | Alternatif jika perlu cetak struk Bluetooth |

**Alasan memilih web responsif + PWA:** cocok dengan arsitektur cloud proyek (frontend statis di belakang API gateway), satu kode untuk semua platform, dan pembaruan tidak menunggu pengguna memperbarui aplikasi.

## 2. Titik pisah tata letak (breakpoint)

| Platform | Lebar | Tata letak | Wireframe |
|---|---|---|---|
| **HP** | < 700 px | Satu bagian per layar; navigasi bawah (Menu, Keranjang, Pesanan) dengan lencana jumlah | [`wireframe-hp.svg`](../design/wireframe-hp.svg) |
| **Tablet** | 700-1099 px | Dua kolom: menu + pesanan di kiri, keranjang menempel di kanan (320 px) | [`wireframe-tablet.svg`](../design/wireframe-tablet.svg) |
| **Desktop** | >= 1100 px | Dua kolom lebar: menu 5 kolom, keranjang menempel di kanan (380 px) | [`wireframe-desktop.svg`](../design/wireframe-desktop.svg) |

Tangkapan layar prototype nyata: `design/screenshots/` (`hp-*.png`, `tablet-layar-penuh.png`, `desktop-layar-penuh.png`).

## 3. Adaptasi per jenis masukan

| Masukan | Penyesuaian |
|---|---|
| **Sentuh** (HP, tablet) | Semua target >= 44 px (kontrol utama 48 px ke atas); navigasi di zona ibu jari; `inputmode="numeric"` memunculkan papan angka untuk uang diterima |
| **Mouse** | Efek hover pada tombol dan kartu; keranjang sticky agar tidak perlu menggulir |
| **Keyboard** | Urutan Tab logis, fokus terlihat, Enter mengirim pembayaran, Esc menutup dialog, tautan "Langsung ke menu" |
| **Pembaca layar** | Label aksesibel, daerah `aria-live`, dialog semantik |
| **Layar berlekuk/iOS** | `viewport-fit=cover` dan `env(safe-area-inset-*)` untuk header dan navigasi bawah |

## 4. Konsistensi lintas platform

Bagian yang **sama di semua ukuran**: warna, tipografi, komponen, istilah, urutan alur (pilih menu, buat pesanan, bayar, selesai), dan pola konfirmasi. Bagian yang **berbeda**: hanya penataan (satu bagian per layar di HP vs semua terlihat di tablet/desktop). Dengan begitu kasir yang berpindah dari HP ke tablet tidak perlu belajar ulang.

## 5. Fungsi PWA

| Fitur | Berkas | Perilaku |
|---|---|---|
| Manifest | `frontend/manifest.json` | Nama, warna tema, ikon 192/512 px; bisa "dipasang" ke layar utama |
| Service worker | `frontend/sw.js` | Kerangka aplikasi (HTML/CSS/JS/ikon) di-cache: jaringan dulu, cache sebagai cadangan offline |
| Data | - | Panggilan `/api/*` **tidak pernah di-cache**, agar stok dan pembayaran selalu terkini |
| Offline | `js/app.js` | Spanduk peringatan; membuat/membayar pesanan ditunda sampai tersambung (mencegah data ganda) |

Cara memasang: buka aplikasi di Chrome/Edge, pilih *Instal aplikasi* di bilah alamat (Android: menu, *Tambahkan ke layar utama*). Service worker hanya aktif lewat `https://` atau `localhost`.

## 6. Hubungan dengan arsitektur cloud

```
Browser (HP / tablet / desktop)
        |  HTTP
   API Gateway (Nginx)  -- melayani frontend statis + meneruskan /api/*
        |
   menu  |  pesanan  |  pembayaran     (3 layanan terpisah, masing-masing satu database)
```

Frontend sepenuhnya *stateless* dan statis, sehingga mudah diskalakan: bisa disajikan dari VM, penyimpanan objek + CDN, atau kontainer tanpa mengubah kode. Semua logika data ada di layanan, sehingga satu backend melayani semua platform.

## 7. Cakupan pengujian (jujur)

| Sudah diuji | Belum diuji |
|---|---|
| Chromium pada lebar 320, 360, 390 (HP), 1024 (tablet), 1440 (desktop) dengan emulasi sentuh | Perangkat fisik, Safari/iOS, Firefox |
| Alur lengkap pesan, bayar, selesai, batal (`docs/05`) | Pemasangan PWA di perangkat nyata dan perilaku offline sungguhan |
| Kontras warna (hitungan) | Keterbacaan di bawah sinar matahari langsung |
