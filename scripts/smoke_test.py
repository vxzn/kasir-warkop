"""Uji alur end-to-end: login -> pesan -> stok berkurang -> tagihan -> bayar -> status DIBAYAR -> rekap,
ditambah pemeriksaan autentikasi (401/403) di ketiga layanan.

Jalankan setelah `docker compose up -d --build`:
    python scripts/smoke_test.py

Variabel opsional (untuk menguji layanan tanpa gateway):
    BASE_URL    default http://localhost:8080
    MENU_URL, PESANAN_URL, TAGIHAN_URL  menimpa alamat tiap layanan
    AUTH_URL                            default BASE_URL/api/auth
    PEMILIK_PASSWORD, KASIR_PASSWORD    sandi akun awal (default sama dengan docker-compose)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.getenv("BASE_URL", "http://localhost:8080").rstrip("/")
MENU = os.getenv("MENU_URL", BASE + "/api/menu").rstrip("/")
PESANAN = os.getenv("PESANAN_URL", BASE + "/api/pesanan").rstrip("/")
TAGIHAN = os.getenv("TAGIHAN_URL", BASE + "/api/tagihan").rstrip("/")
AUTH = os.getenv("AUTH_URL", BASE + "/api/auth").rstrip("/")
SANDI_PEMILIK = os.getenv("PEMILIK_PASSWORD", "pemilik123")
SANDI_KASIR = os.getenv("KASIR_PASSWORD", "kasir123")
TOKEN = None          # token yang dipakai call() bila tidak ditentukan
TANPA = object()      # penanda: kirim tanpa Authorization


def call(method, url, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    pakai = TOKEN if token is None else (None if token is TANPA else token)
    if pakai:
        headers["Authorization"] = "Bearer " + pakai
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def cek(kondisi, pesan):
    if not kondisi:
        print("GAGAL:", pesan)
        sys.exit(1)
    print("ok   :", pesan)


def tunggu_siap():
    for _ in range(40):
        try:
            if call("GET", MENU)[0] in (200, 401):    # 401 = layanan hidup, hanya menolak karena belum masuk
                return
        except Exception:
            pass
        time.sleep(1)
    cek(False, "sistem siap menerima permintaan")


tunggu_siap()

# 0. Autentikasi
s, _ = call("GET", MENU, token=TANPA)
cek(s == 401, "menu tanpa token ditolak (401)")
s, _ = call("GET", PESANAN, token=TANPA)
cek(s == 401, "pesanan tanpa token ditolak (401)")
s, _ = call("GET", TAGIHAN + "/laporan", token=TANPA)
cek(s == 401, "pembayaran tanpa token ditolak (401)")
s, _ = call("GET", MENU, token="bukan.token.sah")
cek(s == 401, "token palsu ditolak (401)")
s, _ = call("POST", TAGIHAN, {"pesanan_id": 999999, "jumlah": 1000}, token=TANPA)
cek(s == 401, "membuat tagihan langsung (tanpa kunci layanan) ditolak")

s, _ = call("POST", AUTH + "/login", {"username": "kasir1", "password": "salah-sekali"}, token=TANPA)
cek(s == 401, "login dengan sandi salah ditolak (401)")

s, k = call("POST", AUTH + "/login", {"username": "kasir1", "password": SANDI_KASIR}, token=TANPA)
cek(s == 200 and k["user"]["role"] == "kasir" and k["access_token"], "login kasir berhasil dan menerima token")
TOKEN_KASIR = k["access_token"]
s, o = call("POST", AUTH + "/login", {"username": "pemilik", "password": SANDI_PEMILIK}, token=TANPA)
cek(s == 200 and o["user"]["role"] == "pemilik", "login pemilik berhasil")
TOKEN_PEMILIK = o["access_token"]

s, _ = call("GET", TAGIHAN + "/rekap?periode=harian", token=TOKEN_KASIR)
cek(s == 403, "kasir tidak boleh membuka rekap (403)")
s, _ = call("POST", MENU, {"nama": "X", "kategori": "Y", "harga": 1000, "stok": 1}, token=TOKEN_KASIR)
cek(s == 403, "kasir tidak boleh menambah menu (403)")

TOKEN = TOKEN_KASIR     # alur kasir selanjutnya memakai token kasir

# 1. Menu tersedia
s, menu = call("GET", MENU)
cek(s == 200 and len(menu) >= 2, "daftar menu terbaca")
a, b = menu[0], menu[1]

# 2. Buat pesanan -> stok berkurang, tagihan otomatis dibuat
s, p = call("POST", PESANAN, {
    "nama_pelanggan": "Uji Otomatis",
    "meja": "1",
    "item": [{"menu_id": a["id"], "jumlah": 2}, {"menu_id": b["id"], "jumlah": 1}],
})
cek(s == 201, "pesanan dibuat")
total = a["harga"] * 2 + b["harga"]
cek(p["total"] == total and p["status"] == "MENUNGGU_PEMBAYARAN", "total & status awal benar")

s, a2 = call("GET", f"{MENU}/{a['id']}")
cek(a2["stok"] == a["stok"] - 2, "stok menu berkurang otomatis")

s, t = call("GET", f"{TAGIHAN}/{p['id']}")
cek(s == 200 and t["status"] == "BELUM_BAYAR" and t["jumlah"] == total, "tagihan otomatis terbuat")

# 3. Uang kurang ditolak
s, _ = call("POST", f"{TAGIHAN}/{p['id']}/bayar", {"metode": "TUNAI", "jumlah_bayar": total - 1})
cek(s == 400, "pembayaran kurang ditolak")

# 4. Bayar dengan kembalian -> pesanan menjadi DIBAYAR
s, t = call("POST", f"{TAGIHAN}/{p['id']}/bayar", {"metode": "TUNAI", "jumlah_bayar": total + 5000})
cek(s == 200 and t["status"] == "LUNAS" and t["kembalian"] == 5000, "pembayaran lunas, kembalian benar")
s, p2 = call("GET", f"{PESANAN}/{p['id']}")
cek(p2["status"] == "DIBAYAR", "status pesanan ikut berubah jadi DIBAYAR")

# 5. Tidak bisa dibayar dua kali
s, _ = call("POST", f"{TAGIHAN}/{p['id']}/bayar", {"metode": "TUNAI"})
cek(s == 409, "pembayaran ganda ditolak")

# 6. Selesaikan pesanan
s, p3 = call("PATCH", f"{PESANAN}/{p['id']}/status", {"status": "SELESAI"})
cek(s == 200 and p3["status"] == "SELESAI", "pesanan diselesaikan")

# 7. Batal mengembalikan stok
s, sebelum = call("GET", f"{MENU}/{b['id']}")
s, q = call("POST", PESANAN, {"item": [{"menu_id": b["id"], "jumlah": 3}]})
cek(s == 201, "pesanan kedua dibuat")
s, _ = call("POST", f"{PESANAN}/{q['id']}/batal")
cek(s == 200, "pesanan dibatalkan")
s, sesudah = call("GET", f"{MENU}/{b['id']}")
cek(sesudah["stok"] == sebelum["stok"], "stok kembali setelah batal")
s, tq = call("GET", f"{TAGIHAN}/{q['id']}")
cek(tq["status"] == "BATAL", "tagihan ikut dibatalkan")

# 8. Stok tidak cukup ditolak dan tidak meninggalkan sisa
s, _ = call("POST", PESANAN, {"item": [{"menu_id": a["id"], "jumlah": 10**6}]})
cek(s == 409, "pesanan melebihi stok ditolak")

# 9. Laporan
s, lap = call("GET", f"{TAGIHAN}/laporan")
cek(s == 200 and lap["total_pendapatan"] >= total, "laporan pendapatan hari ini terbaca")

# 10. Rekap (pemilik): periode berjalan memuat pembayaran yang baru dibuat
TOKEN = TOKEN_PEMILIK
s, r = call("GET", f"{TAGIHAN}/rekap?periode=harian")
cek(s == 200 and r["periode"] == "harian" and len(r["rincian"]) == 24, "rekap harian: 24 jam")
cek(r["total_pendapatan"] >= total and r["jumlah_transaksi"] >= 1, "rekap harian memuat pembayaran uji")
s, r = call("GET", f"{TAGIHAN}/rekap?periode=mingguan")
cek(s == 200 and len(r["rincian"]) == 7 and r["total_pendapatan"] >= total, "rekap mingguan: 7 hari dan memuat pembayaran uji")
s, r = call("GET", f"{TAGIHAN}/rekap?periode=bulanan")
cek(s == 200 and 28 <= len(r["rincian"]) <= 31 and r["total_pendapatan"] >= total, "rekap bulanan: satu baris per tanggal")
cek("periode_sebelumnya" in r and "perubahan_persen" in r, "rekap memuat perbandingan dengan periode sebelumnya")
s, _ = call("GET", f"{TAGIHAN}/rekap?periode=tahunan")
cek(s == 422, "periode tidak dikenal ditolak (422)")
s, _ = call("GET", f"{TAGIHAN}/rekap?periode=harian&tanggal=bukan-tanggal")
cek(s == 422, "tanggal tidak valid ditolak (422)")
s, r = call("GET", f"{TAGIHAN}/rekap?periode=mingguan&tanggal=2020-01-01")
cek(s == 200 and r["total_pendapatan"] == 0, "periode tanpa penjualan -> total 0")

print("\nSemua pengujian lolos.")
