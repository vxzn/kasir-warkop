# Pemakaian: python scripts/buat_wireframe.py .   (dijalankan dari akar repository; menulis ke design/)
"""Membuat wireframe SVG (low-fidelity) dan lembar design system ke folder design/."""
import importlib.util
import pathlib
import sys
from xml.sax.saxutils import escape

REPO = pathlib.Path(sys.argv[1])
OUT = REPO / "design"
OUT.mkdir(exist_ok=True)

spec = importlib.util.spec_from_file_location("kontras", REPO / "scripts" / "kontras.py")
K = importlib.util.module_from_spec(spec)
spec.loader.exec_module(K)

INK, LINE, FILL, SOFT, BRAND = "#2b1d14", "#8c7a6a", "#ffffff", "#f1ebe3", "#6f4e37"
FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif"


class Svg:
    def __init__(self, w, h, judul, deskripsi):
        self.w, self.h, self.parts = w, h, []
        self.head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
                     f'role="img" aria-labelledby="t d" font-family="{FONT}">'
                     f'<title id="t">{escape(judul)}</title><desc id="d">{escape(deskripsi)}</desc>'
                     f'<rect width="{w}" height="{h}" fill="#f7f1e8"/>')

    def rect(self, x, y, w, h, fill=FILL, stroke=LINE, r=8, sw=1.5, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def text(self, x, y, s, size=14, weight=400, fill=INK, anchor="start"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')

    def circle(self, cx, cy, r, fill=BRAND, stroke="none"):
        self.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}"/>')

    def callout(self, x, y, n):
        self.circle(x, y, 13, fill="#a8201a")
        self.text(x, y + 5, str(n), 14, 700, "#fff", "middle")

    def button(self, x, y, w, h, label, primary=True, size=14):
        self.rect(x, y, w, h, fill=BRAND if primary else FILL, stroke=BRAND, r=8, sw=2)
        self.text(x + w / 2, y + h / 2 + size / 3, label, size, 700, "#fff" if primary else BRAND, "middle")

    def chip(self, x, y, label, active=False, h=30):
        w = 22 + 7.2 * len(label)
        self.rect(x, y, w, h, fill=BRAND if active else FILL, stroke=LINE, r=h / 2)
        self.text(x + w / 2, y + h / 2 + 5, label, 13, 600, "#fff" if active else INK, "middle")
        return w

    def card(self, x, y, w, h, kat, nama, harga, stok, badge=None, disabled=False):
        self.rect(x, y, w, h, fill="#efe8e0" if disabled else "#fffaf4", stroke="#d9c9b8", r=8)
        self.text(x + 10, y + 18, kat, 10, 400, "#5f5045")
        self.text(x + 10, y + 38, nama, 13, 700)
        self.text(x + 10, y + 58, harga, 12, 600)
        self.text(x + 10, y + h - 10, stok, 11, 400, "#5f5045")
        if badge:
            self.circle(x + w - 18, y + 20, 11)
            self.text(x + w - 18, y + 25, str(badge), 12, 700, "#fff", "middle")

    def save(self, nama):
        (OUT / nama).write_text(self.head + "".join(self.parts) + "</svg>\n", encoding="utf-8")
        print("dibuat:", OUT / nama)


def header(s, x, y, w, kecil=False):
    s.rect(x, y, w, 44, fill=BRAND, stroke=BRAND, r=0)
    s.text(x + 14, y + 28, "☕ Kasir Warkop", 16, 700, "#fff")
    s.text(x + w - 14, y + 27, "Hari ini: 3 transaksi, Rp 84.000" if not kecil else "3 trx, Rp 84.000", 11, 400, "#fff", "end")


def nav(s, x, y, w, aktif):
    s.rect(x, y, w, 64, fill="#fff", stroke="#d9c9b8", r=0)
    for i, (lbl, ico) in enumerate([("Menu", "☰"), ("Keranjang", "\U0001F6D2"), ("Pesanan", "\U0001F4CB")]):
        cx = x + w / 6 + i * w / 3
        if i == aktif:
            s.rect(x + i * w / 3, y, w / 3, 4, fill=BRAND, stroke=BRAND, r=0)
        s.text(cx, y + 30, ico, 18, 400, BRAND if i == aktif else "#5f5045", "middle")
        s.text(cx, y + 50, lbl, 12, 600, BRAND if i == aktif else "#5f5045", "middle")


def layar_hp(s, x, y, judul, isi):
    W, H = 340, 700
    s.text(x + W / 2, y - 14, judul, 15, 700, INK, "middle")
    s.rect(x, y, W, H, fill="#fff", stroke=INK, r=26, sw=3)
    s.rect(x + 8, y + 8, W - 16, H - 16, fill="#f7f1e8", stroke="none", r=20)
    header(s, x + 8, y + 8, W - 16, kecil=True)
    isi(x + 8, y + 52, W - 16)
    nav(s, x + 8, y + H - 8 - 64, W - 16, {"Menu": 0, "Keranjang": 1, "Pesanan": 2}[judul.split(". ")[1].split(" ")[0]])
    if judul.startswith("1."):
        s.callout(x + W - 24, y + H - 8 - 64, 1)


def hp_menu(x, y, w):
    s = S
    s.rect(x + 10, y + 8, w - 20, 44, fill="#fff", stroke=LINE, r=10)
    s.text(x + 24, y + 36, "Cari menu, mis. kopi", 13, 400, "#5f5045")
    cx = x + 10
    for i, k in enumerate(["Semua", "Kopi", "Minuman"]):
        cx += s.chip(cx, y + 62, k, i == 0, 36) + 6
    cw = (w - 30) / 2
    data = [("KOPI", "Kopi Hitam", "Rp 8.000", "Stok 98", None), ("KOPI", "Kopi Susu", "Rp 12.000", "Stok 100", 1),
            ("KOPI", "Cappuccino", "Rp 15.000", "Stok 50", None), ("MINUMAN", "Teh Manis", "Rp 5.000", "Stok 99", None),
            ("MAKANAN", "Pisang Goreng", "Rp 8.000", "Sisa 8", None), ("MAKANAN", "Roti Bakar", "Rp 10.000", "Habis", None)]
    for i, d in enumerate(data):
        s.card(x + 10 + (i % 2) * (cw + 10), y + 110 + (i // 2) * 106, cw, 96, *d[:4], badge=d[4], disabled=d[3] == "Habis")
    s.callout(x + w - 8, y + 30, 2)
    s.callout(x + w - 14, y + 80, 3)
    s.callout(x + w - 8, y + 342, 4)


def hp_cart(x, y, w):
    s = S
    s.text(x + 14, y + 28, "Keranjang", 18, 700)
    s.text(x + w - 14, y + 28, "Kosongkan", 12, 600, BRAND, "end")
    s.rect(x + 10, y + 42, w - 120, 44, fill="#fff", stroke=LINE, r=10)
    s.text(x + 22, y + 69, "Nama pelanggan", 12, 400, "#5f5045")
    s.rect(x + w - 100, y + 42, 90, 44, fill="#fff", stroke=LINE, r=10)
    s.text(x + w - 88, y + 69, "Meja", 12, 400, "#5f5045")
    for i, (n, hg) in enumerate([("Kopi Susu", "Rp 12.000"), ("Cappuccino", "2 × Rp 15.000 = Rp 30.000"), ("Teh Manis", "Rp 5.000")]):
        yy = y + 104 + i * 70
        s.text(x + 14, yy + 20, n, 14, 700)
        s.text(x + 14, yy + 40, hg, 11, 400, "#5f5045")
        for j, lbl in enumerate(["−", "1", "+"]):
            bx = x + w - 158 + j * 50
            if lbl == "1":
                s.text(bx + 24, yy + 36, lbl, 17, 700, INK, "middle")
            else:
                s.rect(bx, yy + 10, 48, 48, fill="#fff", stroke=LINE, r=10)
                s.text(bx + 24, yy + 42, lbl, 22, 700, INK, "middle")
    s.text(x + 14, y + 350, "Total", 18, 400)
    s.text(x + w - 14, y + 350, "Rp 47.000", 20, 700, INK, "end")
    s.button(x + 10, y + 370, w - 20, 56, "Buat Pesanan", True, 17)
    s.callout(x + w - 170, y + 130, 3)
    s.callout(x + w - 8, y + 386, 5)


def hp_orders(x, y, w):
    s = S
    s.text(x + 14, y + 28, "Daftar Pesanan", 18, 700)
    cx = x + w - 150
    cx += s.chip(cx, y + 10, "Aktif", True, 36) + 6
    s.chip(cx, y + 10, "Semua", False, 36)
    for i, (t, st, col, btn) in enumerate([("#2 · Budi · Meja 3", "○ Menunggu bayar", "#8a5200", True),
                                           ("#1 · Sari", "● Sudah dibayar", "#1f6b2a", False)]):
        yy = y + 60 + i * 150
        s.rect(x + 10, yy, w - 20, 138, fill="#fff", stroke="#d9c9b8", r=10)
        s.text(x + 22, yy + 26, t, 13, 700)
        s.rect(x + w - 150, yy + 12, 130, 24, fill=col, stroke=col, r=12)
        s.text(x + w - 85, yy + 29, st, 11, 700, "#fff", "middle")
        s.text(x + 22, yy + 52, "• 2 × Kopi Hitam", 12, 400, "#5f5045")
        s.text(x + 22, yy + 70, "• 1 × Teh Manis", 12, 400, "#5f5045")
        s.text(x + 22, yy + 118, "Rp 21.000", 14, 700)
        if btn:
            s.button(x + w - 190, yy + 84, 70, 48, "Bayar", True, 13)
            s.rect(x + w - 112, yy + 84, 92, 48, fill="#fff", stroke="#a8201a", r=8, sw=2)
            s.text(x + w - 66, yy + 113, "Batalkan", 13, 700, "#a8201a", "middle")
        else:
            s.button(x + w - 150, yy + 84, 130, 48, "Tandai selesai", False, 13)
    s.callout(x + w - 8, yy + 50 - 150, 6)


# ---------------- Wireframe HP ----------------
S = Svg(1200, 860, "Wireframe HP Kasir Warkop", "Tiga layar HP: Menu, Keranjang, Pesanan, dengan navigasi bawah.")
S.text(600, 34, "Wireframe HP (lebar 360-430 px): satu fokus per layar, navigasi bawah", 20, 700, INK, "middle")
layar_hp(S, 30, 80, "1. Menu", hp_menu)
layar_hp(S, 430, 80, "2. Keranjang", hp_cart)
layar_hp(S, 830, 80, "3. Pesanan", hp_orders)
legend = ["1  Navigasi bawah di zona jangkauan ibu jari; tab aktif diberi garis + warna.",
          "2  Pencarian + filter kategori mempersingkat daftar menu (kenali, bukan ingat).",
          "3  Semua target sentuh minimal 44 px (kontrol utama 48-56 px); label tombol jelas.",
          "4  Menu habis dinonaktifkan dan diberi teks 'Habis' (pencegahan kesalahan).",
          "5  Satu aksi utama per layar (Buat Pesanan), ukuran besar, kontras tinggi.",
          "6  Status memakai ikon + teks, tidak hanya warna; 'Batalkan' meminta konfirmasi."]
for i, l in enumerate(legend):
    col, row = i // 3, i % 3
    S.text(60 + col * 560, 805 + row * 20, l, 12.5, 400, INK)
S.save("wireframe-hp.svg")

# ---------------- Wireframe tablet ----------------
S = Svg(1120, 960, "Wireframe tablet Kasir Warkop", "Tata letak dua kolom untuk tablet landscape: menu dan pesanan di kiri, keranjang di kanan.")
S.text(560, 34, "Wireframe tablet landscape (700-1099 px): dua kolom, keranjang selalu terlihat", 20, 700, INK, "middle")
fx, fy, fw, fh = 48, 60, 1024, 768
S.rect(fx, fy, fw, fh, fill="#f7f1e8", stroke=INK, r=14, sw=3)
header(S, fx + 2, fy + 2, fw - 4)
lx, lw = fx + 16, 656
S.rect(lx, fy + 68, lw, 530, fill="#fff", stroke="#d9c9b8", r=12)
S.text(lx + 14, fy + 94, "Menu", 18, 700)
S.rect(lx + 14, fy + 104, lw - 28, 48, fill="#fff", stroke=LINE, r=10)
S.text(lx + 28, fy + 134, "Cari menu, mis. kopi", 14, 400, "#5f5045")
cx = lx + 14
for i, k in enumerate(["Semua", "Kopi", "Minuman", "Makanan"]):
    cx += S.chip(cx, fy + 162, k, i == 0, 40) + 8
cw = (lw - 28 - 24) / 3
items = [("KOPI", "Kopi Hitam", "Rp 8.000", "Stok 98", None), ("KOPI", "Kopi Susu", "Rp 12.000", "Stok 100", 1), ("KOPI", "Cappuccino", "Rp 15.000", "Stok 50", 1),
         ("KOPI", "Es Kopi Gula Aren", "Rp 15.000", "Stok 50", None), ("MINUMAN", "Teh Manis", "Rp 5.000", "Stok 99", None), ("MINUMAN", "Es Jeruk", "Rp 7.000", "Stok 60", None),
         ("MAKANAN", "Mie Instan Telur", "Rp 12.000", "Stok 40", None), ("MAKANAN", "Pisang Goreng", "Rp 8.000", "Sisa 8", None), ("MAKANAN", "Roti Bakar", "Rp 10.000", "Habis", None)]
for i, d in enumerate(items):
    S.card(lx + 14 + (i % 3) * (cw + 12), fy + 214 + (i // 3) * 126, cw, 114, *d[:4], badge=d[4], disabled=d[3] == "Habis")
S.rect(lx, fy + 612, lw, 140, fill="#fff", stroke="#d9c9b8", r=12)
S.text(lx + 14, fy + 640, "Daftar Pesanan", 18, 700)
S.chip(lx + lw - 150, fy + 622, "Aktif", True, 36)
S.chip(lx + lw - 80, fy + 622, "Semua", False, 36)
S.text(lx + 14, fy + 678, "#2 · Budi · Meja 3  |  2 × Kopi Hitam, 1 × Teh Manis  |  Rp 21.000", 13, 400, "#5f5045")
S.rect(lx + lw - 164, fy + 668, 70, 48, fill=BRAND, stroke=BRAND, r=8)
S.text(lx + lw - 129, fy + 697, "Bayar", 13, 700, "#fff", "middle")
S.rect(lx + lw - 86, fy + 668, 76, 48, fill="#fff", stroke="#a8201a", r=8, sw=2)
S.text(lx + lw - 48, fy + 697, "Batalkan", 12, 700, "#a8201a", "middle")
rx, rw = lx + lw + 16, 320
S.rect(rx, fy + 68, rw, 330, fill="#fff", stroke="#d9c9b8", r=12)
S.text(rx + 14, fy + 96, "Keranjang", 18, 700)
S.rect(rx + 14, fy + 108, 190, 44, fill="#fff", stroke=LINE, r=10)
S.text(rx + 26, fy + 135, "Nama pelanggan", 12, 400, "#5f5045")
S.rect(rx + 214, fy + 108, 92, 44, fill="#fff", stroke=LINE, r=10)
S.text(rx + 226, fy + 135, "Meja", 12, 400, "#5f5045")
for i, (n, hg) in enumerate([("Kopi Susu", "Rp 12.000"), ("Cappuccino", "Rp 15.000")]):
    yy = fy + 166 + i * 62
    S.text(rx + 14, yy + 22, n, 14, 700)
    S.text(rx + 14, yy + 40, hg, 11, 400, "#5f5045")
    for j, lbl in enumerate(["−", "1", "+"]):
        bx = rx + rw - 156 + j * 50
        if lbl == "1":
            S.text(bx + 24, yy + 36, lbl, 17, 700, INK, "middle")
        else:
            S.rect(bx, yy + 10, 48, 48, fill="#fff", stroke=LINE, r=10)
            S.text(bx + 24, yy + 42, lbl, 22, 700, INK, "middle")
S.text(rx + 14, fy + 322, "Total", 18, 400)
S.text(rx + rw - 14, fy + 322, "Rp 27.000", 20, 700, INK, "end")
S.button(rx + 14, fy + 334, rw - 28, 52, "Buat Pesanan", True, 16)
S.callout(fx + fw - 6, fy + 100, 1)
S.callout(lx + lw - 6, fy + 100, 2)
S.callout(rx + rw - 20, fy + 360, 3)
S.callout(lx + 12, fy + 612, 4)
for i, l in enumerate(["1  Keranjang menempel di kanan (sticky): total dan aksi utama selalu terlihat tanpa menggulir.",
                       "2  Grid menu 3 kolom: kartu cukup besar untuk jari, informasi stok langsung terbaca.",
                       "3  Satu tombol utama berwarna penuh; aksi sekunder berupa tombol garis.",
                       "4  Pesanan aktif di bawah menu: kasir memantau tanpa pindah halaman."]):
    S.text(fx, fy + fh + 30 + i * 22, l, 13, 400, INK)
S.save("wireframe-tablet.svg")

# ---------------- Wireframe desktop ----------------
S = Svg(1250, 800, "Wireframe desktop Kasir Warkop", "Tata letak dua kolom lebar untuk desktop dengan grid menu lima kolom.")
S.text(625, 34, "Wireframe desktop (>= 1100 px): menu lebar, keranjang tetap di kanan", 20, 700, INK, "middle")
fx, fy, fw, fh = 40, 56, 1170, 690
S.rect(fx, fy, fw, fh, fill="#f7f1e8", stroke=INK, r=12, sw=3)
header(S, fx + 2, fy + 2, fw - 4)
lx, lw = fx + 70, 740
S.rect(lx, fy + 66, lw, 360, fill="#fff", stroke="#d9c9b8", r=12)
S.text(lx + 14, fy + 92, "Menu", 18, 700)
S.rect(lx + 14, fy + 100, lw - 28, 44, fill="#fff", stroke=LINE, r=10)
S.text(lx + 28, fy + 128, "Cari menu, mis. kopi", 13, 400, "#5f5045")
cx = lx + 14
for i, k in enumerate(["Semua", "Kopi", "Minuman", "Makanan"]):
    cx += S.chip(cx, fy + 154, k, i == 0, 36) + 8
cw = (lw - 28 - 48) / 5
for i, d in enumerate(items[:9]):
    S.card(lx + 14 + (i % 5) * (cw + 12), fy + 200 + (i // 5) * 110, cw, 100, *d[:4], badge=d[4], disabled=d[3] == "Habis")
S.rect(lx, fy + 440, lw, 130, fill="#fff", stroke="#d9c9b8", r=12)
S.text(lx + 14, fy + 468, "Daftar Pesanan", 18, 700)
S.text(lx + 14, fy + 508, "#2 · Budi · Meja 3  |  2 × Kopi Hitam, 1 × Teh Manis  |  Rp 21.000", 13, 400, "#5f5045")
S.rect(lx + lw - 170, fy + 490, 60, 44, fill=BRAND, stroke=BRAND, r=8)
S.text(lx + lw - 140, fy + 517, "Bayar", 13, 700, "#fff", "middle")
S.rect(lx + lw - 100, fy + 490, 86, 44, fill="#fff", stroke="#a8201a", r=8, sw=2)
S.text(lx + lw - 57, fy + 517, "Batalkan", 12, 700, "#a8201a", "middle")
rx, rw = lx + lw + 20, 300
S.rect(rx, fy + 66, rw, 330, fill="#fff", stroke="#d9c9b8", r=12)
S.text(rx + 14, fy + 94, "Keranjang", 18, 700)
S.rect(rx + 14, fy + 106, 180, 44, fill="#fff", stroke=LINE, r=10)
S.text(rx + 26, fy + 133, "Nama pelanggan", 12, 400, "#5f5045")
S.rect(rx + 204, fy + 106, 82, 44, fill="#fff", stroke=LINE, r=10)
S.text(rx + 216, fy + 133, "Meja", 12, 400, "#5f5045")
for i, (n, hg) in enumerate([("Kopi Susu", "Rp 12.000"), ("Cappuccino", "Rp 15.000")]):
    yy = fy + 164 + i * 62
    S.text(rx + 14, yy + 22, n, 14, 700)
    S.text(rx + 14, yy + 40, hg, 11, 400, "#5f5045")
    for j, lbl in enumerate(["−", "1", "+"]):
        bx = rx + rw - 156 + j * 50
        if lbl == "1":
            S.text(bx + 24, yy + 36, lbl, 17, 700, INK, "middle")
        else:
            S.rect(bx, yy + 10, 48, 48, fill="#fff", stroke=LINE, r=10)
            S.text(bx + 24, yy + 42, lbl, 22, 700, INK, "middle")
S.text(rx + 14, fy + 318, "Total", 18, 400)
S.text(rx + rw - 14, fy + 318, "Rp 27.000", 20, 700, INK, "end")
S.button(rx + 14, fy + 332, rw - 28, 52, "Buat Pesanan", True, 16)
S.callout(lx + lw - 6, fy + 100, 1)
S.callout(rx + rw - 20, fy + 358, 2)
S.callout(lx + 12, fy + 440, 3)
for i, l in enumerate(["1  Grid 5 kolom memanfaatkan layar lebar; pencarian dan filter tetap di atas.",
                       "2  Keranjang sticky: tombol utama tidak pernah hilang saat menu digulir.",
                       "3  Papan pesanan di bawah menu; mouse dan keyboard sama-sama didukung (Tab, Enter, fokus terlihat)."]):
    S.text(fx + 14, fy + 600 + i * 22, l, 13, 400, INK)
S.save("wireframe-desktop.svg")

# ---------------- Lembar design system ----------------
S = Svg(1100, 900, "Design system Kasir Warkop", "Palet warna dengan rasio kontras, skala tipografi, ukuran target sentuh, dan status komponen.")
S.text(550, 38, "Design system Kasir Warkop", 24, 700, INK, "middle")
S.text(40, 78, "Palet warna (rasio kontras dihitung dengan scripts/kontras.py, rumus WCAG 2.x)", 15, 700)
sw = [("bg", "Latar halaman", "ink", 4.5), ("surface", "Panel", "ink", 4.5), ("kartu", "Kartu menu", "ink", 4.5), ("ink", "Teks utama", "surface", 4.5),
      ("muted", "Teks sekunder", "surface", 4.5), ("brand", "Aksi utama", "putih", 4.5), ("brand-dark", "Aksi utama (hover)", "putih", 4.5),
      ("ok", "Dibayar", "putih", 4.5), ("warn", "Menunggu / menipis", "putih", 4.5), ("bad", "Batal / bahaya", "putih", 4.5),
      ("done", "Selesai", "putih", 4.5), ("focus", "Cincin fokus", "surface", 3.0)]
for i, (tok, peran, lawan, amb) in enumerate(sw):
    x, y = 40 + (i % 4) * 262, 96 + (i // 4) * 118
    S.rect(x, y, 244, 104, fill="#fff", stroke="#d9c9b8", r=10)
    S.rect(x + 10, y + 10, 64, 84, fill=K.TOKEN[tok], stroke="#8c7a6a", r=8)
    S.text(x + 86, y + 30, peran, 13, 700)
    S.text(x + 86, y + 50, f"{tok} \u00b7 {K.TOKEN[tok]}", 12, 400, "#5f5045")
    r = K.rasio(K.TOKEN[tok], K.TOKEN[lawan]) if tok != "focus" else K.rasio(K.TOKEN["focus"], K.TOKEN["surface"])
    S.text(x + 86, y + 72, f"vs {lawan}: {r:.2f} : 1", 12, 400)
    S.text(x + 86, y + 90, ("Lolos" if r >= amb else "GAGAL") + f" (min {amb:g} : 1)", 12, 700, "#1f6b2a" if r >= amb else "#a8201a")

S.text(40, 478, "Tipografi (font sistem: cepat dimuat dan akrab di setiap platform)", 15, 700)
for i, (n, sz, wt, c) in enumerate([("Judul halaman  20 / 700", 20, 700, INK), ("Judul bagian  18 / 700", 18, 700, INK), ("Teks isi  16 / 400 (minimum di input agar iOS tidak memperbesar)", 16, 400, INK),
                                    ("Teks bantu  14 / 400", 14, 400, "#5f5045"), ("Keterangan  12-13 / 400-700 (hanya untuk info tambahan)", 12.5, 400, "#5f5045")]):
    S.text(40, 506 + i * 28, n, sz, wt, c)

S.text(40, 668, "Ukuran dan jarak", 15, 700)
S.rect(40, 684, 48, 48, fill="#fff", stroke=LINE, r=10)
S.text(100, 700, "Target sentuh minimum 44 px", 13)
S.text(100, 718, "(kontrol utama 48-56 px: +/−, kolom isian, tombol utama)", 12.5, 400, "#5f5045")
S.text(100, 736, "Jarak antar panel 16 px; radius sudut 10-12 px", 12.5, 400, "#5f5045")

S.text(560, 668, "Status komponen", 15, 700)
S.button(560, 684, 120, 48, "Utama", True, 14)
S.button(692, 684, 120, 48, "Sekunder", False, 14)
S.rect(824, 684, 120, 48, fill="#fff", stroke="#a8201a", r=10, sw=2)
S.text(884, 713, "Bahaya", 14, 700, "#a8201a", "middle")
S.rect(956, 684, 104, 48, fill=BRAND, stroke=BRAND, r=10, sw=2)
S.rect(951, 679, 114, 58, fill="none", stroke="#0b57d0", r=13, sw=3)
S.text(1008, 713, "Fokus", 14, 700, "#fff", "middle")
for i, (lbl, col) in enumerate([("○ Menunggu bayar", "#8a5200"), ("● Sudah dibayar", "#1f6b2a"), ("✔ Selesai", "#4a5560"), ("✕ Dibatalkan", "#a8201a")]):
    S.rect(560 + i * 130, 758, 122, 26, fill=col, stroke=col, r=13)
    S.text(560 + i * 130 + 61, 776, lbl, 11.5, 700, "#fff", "middle")
S.text(560, 806, "Status selalu memakai ikon + teks, tidak hanya warna.", 12.5, 400, "#5f5045")

S.text(40, 780, "Prinsip: sederhana, jelas, memaafkan kesalahan.", 14, 700)
S.text(40, 802, "Aksi yang merusak (batal, kosongkan) selalu meminta konfirmasi,", 13, 400, "#5f5045")
S.text(40, 820, "dengan fokus awal pada pilihan yang aman ('Kembali').", 13, 400, "#5f5045")
S.save("design-system.svg")
