"""Uji alur end-to-end: pesan -> stok berkurang -> tagihan -> bayar -> status DIBAYAR.

Jalankan setelah `docker compose up -d --build`:
    python scripts/smoke_test.py

Variabel opsional (untuk menguji layanan tanpa gateway):
    BASE_URL    default http://localhost:8080
    MENU_URL, PESANAN_URL, TAGIHAN_URL  menimpa alamat tiap layanan
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


def call(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
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
    for _ in range(30):
        try:
            if call("GET", MENU)[0] == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    cek(False, "sistem siap menerima permintaan")


tunggu_siap()

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

print("\nSemua pengujian lolos.")
