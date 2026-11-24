# Pemakaian: python scripts/uji_antarmuka/mock_server.py frontend 8099
# Server tiruan (tanpa Docker/FastAPI) untuk menguji tampilan frontend di http://127.0.0.1:8099
"""Server tiruan: melayani frontend + API in-memory dengan perilaku yang sama seperti backend.
Hanya untuk menguji tampilan; BUKAN bagian dari repository."""
import json
import mimetypes
import pathlib
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = pathlib.Path(sys.argv[1]).resolve()
PORT = int(sys.argv[2])
REPO = pathlib.Path(__file__).resolve().parent.parent.parent
# Memakai modul ASLI dari repository (auth, pengguna, pembatas, rekap, contoh_data), bukan tiruan.
for _n in ("auth", "pembayaran"):
    sys.path.insert(0, str(REPO / "services" / _n))
import auth  # noqa: E402
import contoh_data  # noqa: E402
import pengguna  # noqa: E402
import rekap  # noqa: E402
from pembatas import PembatasLogin  # noqa: E402

WIB = timezone(timedelta(hours=7))
RAHASIA = "rahasia-mock-server-minimal-16"
auth.muat_konfigurasi(RAHASIA, "kunci-layanan-mock-16-karakter")
USERS = sqlite3.connect(":memory:", check_same_thread=False)
USERS.row_factory = sqlite3.Row
pengguna.init(USERS)
pengguna.isi_awal(USERS, "pemilik123", "kasir123", datetime.now(WIB).isoformat(timespec="seconds"))
PEMBATAS = PembatasLogin(maks_gagal=5, jendela=300, kunci=60)
PAY = sqlite3.connect(":memory:", check_same_thread=False)
PAY.execute("""CREATE TABLE tagihan (id INTEGER PRIMARY KEY AUTOINCREMENT, pesanan_id INTEGER NOT NULL UNIQUE,
  jumlah INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'BELUM_BAYAR', metode TEXT, dibayar INTEGER,
  kembalian INTEGER, dibuat TEXT NOT NULL, waktu_bayar TEXT)""")
contoh_data.isi(PAY, datetime.now(WIB).date())
mimetypes.add_type("application/json", ".json")
lock = threading.Lock()

MENU = [
    {"id": i + 1, "nama": n, "kategori": k, "harga": h, "stok": s}
    for i, (n, k, h, s) in enumerate([
        ("Kopi Hitam", "Kopi", 8000, 100), ("Kopi Susu", "Kopi", 12000, 100),
        ("Cappuccino", "Kopi", 15000, 50), ("Es Kopi Gula Aren", "Kopi", 15000, 50),
        ("Teh Manis", "Minuman", 5000, 100), ("Es Jeruk", "Minuman", 7000, 60),
        ("Mie Instan Telur", "Makanan", 12000, 40), ("Pisang Goreng", "Makanan", 8000, 8),
        ("Roti Bakar Coklat", "Makanan", 10000, 0),
    ])
]
PESANAN, TAGIHAN = [], {}


def respon(h, code, data):
    body = json.dumps(data).encode()
    h.send_response(code)
    h.send_header("Content-Type", "application/json")
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)


def akses(h, *peran_boleh):
    """Kembalikan klaim, atau kirim 401/403 dan kembalikan None (aturan sama dengan layanan asli)."""
    try:
        return auth.periksa_akses(h.headers.get("Authorization"), None, peran_boleh)
    except auth.AksesDitolak as e:
        respon(h, e.status, {"detail": e.pesan})
        return None


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        if not p.startswith("/api/"):
            f = ROOT / (p.lstrip("/") or "index.html")
            if f.is_dir():
                f = f / "index.html"
            if not f.exists():
                f = ROOT / "index.html"
            data = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(str(f))[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        with lock:
            if p == "/api/auth/me":
                k = akses(self, "kasir", "pemilik")
                return respon(self, 200, k) if k else None
            if p == "/api/menu":
                if not akses(self, "kasir", "pemilik"):
                    return
                return respon(self, 200, MENU)
            if p == "/api/pesanan":
                if not akses(self, "kasir", "pemilik"):
                    return
                return respon(self, 200, list(reversed(PESANAN)))
            if p == "/api/tagihan/laporan":
                if not akses(self, "kasir", "pemilik"):
                    return
                lunas = [t for t in TAGIHAN.values() if t["status"] == "LUNAS"]
                return respon(self, 200, {"tanggal": "x", "jumlah_transaksi": len(lunas),
                                          "total_pendapatan": sum(t["jumlah"] for t in lunas)})
            if p == "/api/tagihan/rekap":
                if not akses(self, "pemilik"):
                    return
                q = parse_qs(urlparse(self.path).query)
                periode = q.get("periode", ["harian"])[0]
                try:
                    acuan = datetime.strptime(q["tanggal"][0], "%Y-%m-%d").date() if "tanggal" in q else datetime.now(WIB).date()
                    return respon(self, 200, rekap.ambil_rekap(PAY, periode, acuan))
                except (ValueError, KeyError):
                    return respon(self, 422, {"detail": "Periode atau tanggal tidak valid"})
        respon(self, 404, {"detail": "tidak ada"})

    def do_POST(self):
        p = urlparse(self.path).path
        d = self.body()
        with lock:
            if p == "/api/auth/login":
                kunci = str(d.get("username", "")).strip().lower() + "|mock"
                sisa = PEMBATAS.sisa_kunci(kunci)
                if sisa:
                    return respon(self, 429, {"detail": f"Terlalu banyak percobaan. Coba lagi dalam {sisa} detik."})
                u = pengguna.autentikasi(USERS, d.get("username", ""), d.get("password", ""))
                if not u:
                    PEMBATAS.gagal(kunci)
                    return respon(self, 401, {"detail": "Nama pengguna atau kata sandi salah"})
                PEMBATAS.berhasil(kunci)
                detik = int(d.get("_detik", 8 * 3600))   # hanya untuk uji sesi kedaluwarsa
                token = auth.buat_token({"sub": u["username"], "nama": u["nama"], "role": u["role"]}, RAHASIA, detik)
                return respon(self, 200, {"access_token": token, "token_type": "bearer", "expires_in": detik,
                                          "user": {"username": u["username"], "nama": u["nama"], "role": u["role"]}})
            if not akses(self, "kasir", "pemilik"):
                return
            if p == "/api/pesanan":
                baris, total = [], 0
                for it in d["item"]:
                    m = next((x for x in MENU if x["id"] == it["menu_id"]), None)
                    if not m:
                        return respon(self, 404, {"detail": "Menu tidak ditemukan"})
                    if m["stok"] < it["jumlah"]:
                        return respon(self, 409, {"detail": f"Stok {m['nama']} tidak cukup"})
                for it in d["item"]:
                    m = next(x for x in MENU if x["id"] == it["menu_id"])
                    m["stok"] -= it["jumlah"]
                    baris.append({"menu_id": m["id"], "nama": m["nama"], "harga": m["harga"], "jumlah": it["jumlah"]})
                    total += m["harga"] * it["jumlah"]
                o = {"id": len(PESANAN) + 1, "nama_pelanggan": d.get("nama_pelanggan") or "Pelanggan",
                     "meja": d.get("meja"), "total": total, "status": "MENUNGGU_PEMBAYARAN",
                     "dibuat": datetime.now().isoformat(), "item": baris}
                PESANAN.append(o)
                TAGIHAN[o["id"]] = {"pesanan_id": o["id"], "jumlah": total, "status": "BELUM_BAYAR"}
                return respon(self, 201, o)
            if p.endswith("/batal") and p.startswith("/api/pesanan/"):
                o = PESANAN[int(p.split("/")[3]) - 1]
                if o["status"] != "MENUNGGU_PEMBAYARAN":
                    return respon(self, 409, {"detail": "Hanya pesanan belum dibayar yang bisa dibatalkan"})
                o["status"] = "BATAL"
                TAGIHAN[o["id"]]["status"] = "BATAL"
                for i in o["item"]:
                    next(x for x in MENU if x["id"] == i["menu_id"])["stok"] += i["jumlah"]
                return respon(self, 200, o)
            if p.endswith("/bayar") and p.startswith("/api/tagihan/"):
                pid = int(p.split("/")[3])
                t = TAGIHAN[pid]
                if t["status"] != "BELUM_BAYAR":
                    return respon(self, 409, {"detail": "Tagihan sudah " + t["status"]})
                dibayar = d.get("jumlah_bayar") or t["jumlah"]
                if dibayar < t["jumlah"]:
                    return respon(self, 400, {"detail": "Uang kurang"})
                t.update(status="LUNAS", dibayar=dibayar, kembalian=dibayar - t["jumlah"], metode=d.get("metode"))
                PAY.execute("INSERT INTO tagihan (pesanan_id, jumlah, status, metode, dibayar, kembalian, dibuat, waktu_bayar) "
                            "VALUES (?,?,?,?,?,?,?,?)", (pid, t["jumlah"], "LUNAS", d.get("metode") or "TUNAI", dibayar,
                                                         dibayar - t["jumlah"], datetime.now(WIB).isoformat(timespec="seconds"),
                                                         datetime.now(WIB).isoformat(timespec="seconds")))
                PESANAN[pid - 1]["status"] = "DIBAYAR"
                return respon(self, 200, t)
        respon(self, 404, {"detail": "tidak ada"})

    def do_PATCH(self):
        p = urlparse(self.path).path
        d = self.body()
        with lock:
            if not akses(self, "kasir", "pemilik"):
                return
            if p.endswith("/status") and p.startswith("/api/pesanan/"):
                o = PESANAN[int(p.split("/")[3]) - 1]
                if d["status"] == "SELESAI" and o["status"] == "DIBAYAR":
                    o["status"] = "SELESAI"
                    return respon(self, 200, o)
                return respon(self, 409, {"detail": "Transisi status tidak valid"})
        respon(self, 404, {"detail": "tidak ada"})


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
