# Pemakaian: python scripts/uji_antarmuka/mock_server.py frontend 8099
# Server tiruan (tanpa Docker/FastAPI) untuk menguji tampilan frontend di http://127.0.0.1:8099
"""Server tiruan: melayani frontend + API in-memory dengan perilaku yang sama seperti backend.
Hanya untuk menguji tampilan; BUKAN bagian dari repository."""
import json
import mimetypes
import pathlib
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = pathlib.Path(sys.argv[1]).resolve()
PORT = int(sys.argv[2])
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
            if p == "/api/menu":
                return respon(self, 200, MENU)
            if p == "/api/pesanan":
                return respon(self, 200, list(reversed(PESANAN)))
            if p == "/api/tagihan/laporan":
                lunas = [t for t in TAGIHAN.values() if t["status"] == "LUNAS"]
                return respon(self, 200, {"tanggal": "x", "jumlah_transaksi": len(lunas),
                                          "total_pendapatan": sum(t["jumlah"] for t in lunas)})
        respon(self, 404, {"detail": "tidak ada"})

    def do_POST(self):
        p = urlparse(self.path).path
        d = self.body()
        with lock:
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
                PESANAN[pid - 1]["status"] = "DIBAYAR"
                return respon(self, 200, t)
        respon(self, 404, {"detail": "tidak ada"})

    def do_PATCH(self):
        p = urlparse(self.path).path
        d = self.body()
        with lock:
            if p.endswith("/status") and p.startswith("/api/pesanan/"):
                o = PESANAN[int(p.split("/")[3]) - 1]
                if d["status"] == "SELESAI" and o["status"] == "DIBAYAR":
                    o["status"] = "SELESAI"
                    return respon(self, 200, o)
                return respon(self, 409, {"detail": "Transisi status tidak valid"})
        respon(self, 404, {"detail": "tidak ada"})


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
