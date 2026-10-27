# 01 - Riset Pengguna (User-Centric)

> **Status jujur:** persona dan kebutuhan di bawah ini adalah **hipotesis awal** yang disusun dari pengamatan umum cara kerja warung kopi, **bukan hasil wawancara nyata**. Bagian 5 berisi panduan wawancara agar hipotesis ini bisa divalidasi dengan pemilik atau kasir warung kopi sungguhan sebelum presentasi.

## 1. Konteks dan masalah

Warung kopi kecil umumnya mencatat pesanan di kertas atau mengandalkan ingatan. Akibatnya:

- pesanan terlewat atau tertukar saat ramai,
- stok habis baru diketahui setelah pelanggan memesan,
- menghitung total dan kembalian memakan waktu,
- pemilik sulit mengetahui pendapatan harian.

**Tujuan produk:** membantu kasir mencatat pesanan dengan cepat dan minim salah, sehingga pelanggan terlayani lebih baik. Nilai yang dipegang: *melayani sesama pengguna dengan mudah, jelas, dan memaafkan kesalahan.*

## 2. Persona (hipotesis)

| | **Rina, kasir** | **Pak Anton, pemilik** | **Dimas, pelanggan** |
|---|---|---|---|
| Usia / peran | 21 th, mahasiswi paruh waktu | 45 th, pemilik warung | 20 th, mahasiswa |
| Perangkat | HP Android; tablet milik warung | HP dan laptop | HP (hanya menerima pesanan, tidak memakai aplikasi langsung) |
| Kemampuan digital | Terbiasa media sosial dan dompet digital | Cukup, tidak suka menu rumit | Tinggi |
| Kebutuhan | Input pesanan cepat saat ramai; kembalian tanpa kalkulator | Laporan pendapatan; stok terpantau | Pesanan benar dan cepat |
| Frustrasi | Salah menulis pesanan; tangan basah/sibuk, tombol kecil sulit ditekan | Stok tidak sinkron dengan catatan | Menunggu lama, pesanan tertukar |
| Implikasi desain | Tombol besar, alur pendek, mode HP | Ringkasan harian, tampilan desktop | Kebenaran pesanan dan kecepatan layanan |

Pengguna utama yang dirancang untuk: **Rina**. Pak Anton dilayani oleh ringkasan "Hari ini" di header.

## 3. Kebutuhan dan prioritas (MoSCoW)

| Prioritas | Kebutuhan | Diwujudkan dalam prototype |
|---|---|---|
| **Must** | Memilih menu dan membuat pesanan dengan cepat | Kartu menu satu ketukan, keranjang |
| **Must** | Total dan kembalian otomatis | Dialog pembayaran, nominal cepat |
| **Must** | Stok tidak boleh minus | Menu habis dinonaktifkan; server menolak melebihi stok |
| **Must** | Membatalkan pesanan yang salah | Tombol Batalkan dengan konfirmasi, stok kembali |
| **Should** | Mencari/menyaring menu | Kolom cari, chip kategori |
| **Should** | Memantau pesanan yang sedang berjalan | Daftar pesanan "Aktif", status berlabel |
| **Should** | Bisa dipakai di HP, tablet, dan komputer | Tata letak responsif 3 ukuran, PWA |
| **Could** | Ringkasan pendapatan harian | Teks "Hari ini" di header |
| **Won't (kali ini)** | Login multi-kasir, cetak struk, diskon | Dicatat sebagai pengembangan lanjutan |

## 4. User story dan alur utama

- *Sebagai kasir, saya ingin menambah menu dengan satu ketukan agar pelanggan tidak menunggu.*
- *Sebagai kasir, saya ingin melihat kembalian langsung agar tidak salah hitung.*
- *Sebagai kasir, saya ingin salah ketuk bisa dibatalkan tanpa kekacauan stok.*
- *Sebagai pemilik, saya ingin melihat pendapatan hari ini sekilas.*

**Alur kasir (user journey):** pelanggan memesan, kasir memilih menu, memeriksa keranjang, *Buat Pesanan*, pelanggan membayar, kasir *Bayar* dan memasukkan uang, kembalian muncul, pesanan disajikan, *Tandai selesai*.

Titik rawan yang diantisipasi: ketukan salah (konfirmasi dan qty +/-), uang kurang (peringatan langsung), koneksi putus (pesan galat jelas dan tombol *Coba lagi*).

## 5. Panduan wawancara (untuk memvalidasi persona)

Wawancarai 1-2 pemilik/kasir warung kopi (10-15 menit). Catat jawaban di tabel bawah.

1. Ceritakan alur dari pelanggan datang sampai membayar.
2. Bagian mana yang paling sering salah atau membuat repot?
3. Perangkat apa yang ada di warung (HP, tablet, laptop)?
4. Saat ramai, berapa pesanan masuk dalam 10 menit?
5. Bagaimana stok dicatat sekarang?
6. Metode bayar apa yang sering dipakai (tunai, QRIS, transfer)?
7. Informasi apa yang ingin Anda lihat di akhir hari?
8. Apa yang membuat Anda enggan memakai aplikasi kasir?

| Pertanyaan | Jawaban narasumber | Dampak ke desain |
|---|---|---|
| 1 | *(isi)* | *(isi)* |
| 2 | *(isi)* | *(isi)* |

Setelah wawancara, perbarui tabel persona dan prioritas di atas.
