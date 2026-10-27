# Tutorial: Menjalankan Kasir Warkop

Panduan ini ditulis untuk **Windows + PowerShell** (VS Code). Pengguna Linux/Mac cukup mengganti `python` dengan `python3`.

Ada tiga cara menjalankan. Pilih sesuai kebutuhan:

| Cara | Cocok untuk | Butuh |
|---|---|---|
| **A. Docker (lengkap)** | Demo penuh: antarmuka + 3 layanan backend | Docker Desktop |
| **B. Antarmuka saja** | Melihat tampilan dan desain tanpa Docker | Python |
| **C. Dari HP** | Mencoba tampilan HP sungguhan | Cara A + Wi-Fi yang sama |

---

## Cara A. Docker (sistem lengkap)

### 1. Pasang Docker Desktop
1. Unduh dari https://www.docker.com/products/docker-desktop dan pasang.
2. Jalankan Docker Desktop, tunggu ikon paus di pojok kanan bawah berhenti bergerak.
3. Cek di terminal:
   ```powershell
   docker --version
   docker compose version
   ```

### 2. Buka folder proyek
Di VS Code: **File > Open Folder** dan pilih `kasir-warkop`, lalu **Terminal > New Terminal**. Pastikan alamat terminal berakhir dengan `kasir-warkop` (folder yang berisi `docker-compose.yml`).

### 3. Jalankan
```powershell
docker compose up -d --build
```
Build pertama butuh beberapa menit karena mengunduh image. Selanjutnya hanya beberapa detik.

### 4. Pastikan semua hidup
```powershell
docker compose ps
```
Empat baris (`menu`, `pembayaran`, `pesanan`, `gateway`) harus berstatus `running` atau `healthy`.

### 5. Buka aplikasi
Browser ke **http://localhost:8080**

### 6. Coba alur utamanya
1. Ketuk kartu menu (mis. Kopi Susu) sampai jumlahnya sesuai. Gunakan kolom **Cari** atau chip kategori untuk menyaring.
2. Isi nama pelanggan dan meja, lalu **Buat Pesanan**. Stok menu berkurang otomatis.
3. Di daftar pesanan, ketuk **Bayar**, pilih metode, isi uang diterima. Kembalian muncul langsung.
4. Ketuk **Selesai** setelah pesanan disajikan.
5. Coba **Batalkan** pada pesanan yang belum dibayar. Stok akan kembali.
6. Lihat pendapatan hari ini di bagian atas.

### 7. Uji otomatis (opsional)
Setelah aplikasi hidup, di terminal yang sama:
```powershell
python scripts/smoke_test.py
```
Kalau semua baris diawali `ok` dan berakhir "Semua pengujian lolos", ketiga layanan terintegrasi dengan benar.

Kalau `python` tidak dikenali, pasang Python dari https://www.python.org/downloads/ dan **centang "Add python.exe to PATH"**, lalu buka ulang terminal. Alternatifnya, coba `py scripts/smoke_test.py`.

### 8. Mematikan
```powershell
docker compose down        # data tetap tersimpan
docker compose down -v     # hapus semua data (kembali ke awal)
```

---

## Cara B. Antarmuka saja (tanpa Docker)

Cara ini memakai server tiruan yang meniru aturan backend (stok, status, kembalian), jadi tampilan bisa dicoba penuh.

```powershell
python scripts/uji_antarmuka/mock_server.py frontend 8099
```
Buka **http://localhost:8099**. Hentikan dengan `Ctrl + C`.

Data di mode ini hanya hidup di memori dan hilang saat server dihentikan.

---

## Cara C. Mencoba dari HP

1. Jalankan Cara A di laptop.
2. Sambungkan HP dan laptop ke **Wi-Fi yang sama**.
3. Cari alamat IP laptop: jalankan `ipconfig`, lihat **IPv4 Address** (misalnya `192.168.1.10`).
4. Di browser HP, buka `http://192.168.1.10:8080`.
5. Kalau tidak terbuka, izinkan Docker lewat Windows Firewall (muncul pop-up saat pertama kali, pilih **Allow**).

Catatan: tombol "pasang sebagai aplikasi" (PWA) hanya muncul di `localhost` atau alamat HTTPS. Lewat IP biasa, tampilan dan fungsi tetap bisa dicoba, tetapi aplikasi tidak bisa dipasang. Setelah di-deploy ke cloud dengan HTTPS, fitur itu aktif.

### Menguji tampilan HP tanpa HP
Di Chrome/Edge: tekan `F12`, lalu `Ctrl + Shift + M` (mode perangkat). Pilih ukuran HP atau tablet dari menu di atas halaman.

### Memasang sebagai aplikasi (di komputer)
Buka http://localhost:8080 di Chrome/Edge, lalu klik ikon **Pasang** di ujung kanan bilah alamat.

---

## Menjalankan uji antarmuka otomatis (opsional)

Memeriksa tata letak 3 ukuran layar, area sentuh, aksesibilitas, dan alur lengkap (43 pemeriksaan).

```powershell
pip install playwright
playwright install chromium
```
Terminal 1:
```powershell
python scripts/uji_antarmuka/mock_server.py frontend 8099
```
Terminal 2:
```powershell
python scripts/uji_antarmuka/uji_ui.py design/screenshots
```
Hasil akhir yang diharapkan: `43/43 pemeriksaan lolos`. Tangkapan layar tersimpan di `design/screenshots`.

---

## Mengunggah ke GitHub

```powershell
git add .
git commit -m "Pesan perubahan"
git push
```
Setelah push, tab **Actions** di GitHub menjalankan build dan uji integrasi otomatis.

---

## Mengatasi masalah

| Gejala | Penyebab | Solusi |
|---|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop belum berjalan | Buka Docker Desktop, tunggu siap, ulangi |
| `port is already allocated` (8080) | Port dipakai program lain | Ubah `"8080:80"` di `docker-compose.yml` menjadi `"8081:80"`, buka `localhost:8081` |
| Halaman terbuka tapi menu kosong / error 502 | Layanan belum siap atau gagal | `docker compose ps`, lalu `docker compose logs -f` |
| Perubahan kode tidak terlihat | Cache browser/service worker | `Ctrl + Shift + R`, atau jalankan `docker compose up -d --build` |
| `python` tidak dikenali | Python belum terpasang atau belum di PATH | Pasang Python dan centang "Add to PATH", buka ulang terminal |
| `python3` membuka Microsoft Store | Di Windows, `python3` hanya pintasan | Pakai `python` atau `py` |
| Data ingin direset | | `docker compose down -v`, lalu `docker compose up -d --build` |

Perintah log yang berguna: `docker compose logs -f pesanan` (ganti nama layanan sesuai kebutuhan).
