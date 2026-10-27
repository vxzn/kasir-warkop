"""Hitung rasio kontras warna (rumus WCAG 2.x) untuk token warna Kasir Warkop.

Jalankan:  python scripts/kontras.py
Teks normal harus >= 4.5 : 1, komponen antarmuka/ikon >= 3 : 1.
"""

TOKEN = {
    "bg": "#f7f1e8",
    "surface": "#ffffff",
    "kartu": "#fffaf4",
    "ink": "#2b1d14",
    "muted": "#5f5045",
    "brand": "#6f4e37",
    "brand-dark": "#55392a",
    "line-strong": "#8c7a6a",
    "ok": "#1f6b2a",
    "warn": "#8a5200",
    "bad": "#a8201a",
    "done": "#4a5560",
    "focus": "#0b57d0",
    "putih": "#ffffff",
}

# (keterangan, depan, belakang, ambang)
PASANGAN = [
    ("Teks utama di latar halaman", "ink", "bg", 4.5),
    ("Teks utama di panel putih", "ink", "surface", 4.5),
    ("Teks utama di kartu menu", "ink", "kartu", 4.5),
    ("Teks sekunder di panel putih", "muted", "surface", 4.5),
    ("Teks sekunder di latar halaman", "muted", "bg", 4.5),
    ("Teks sekunder di kartu menu", "muted", "kartu", 4.5),
    ("Teks putih di tombol utama", "putih", "brand", 4.5),
    ("Teks putih di tombol utama (hover)", "putih", "brand-dark", 4.5),
    ("Teks tombol sekunder (cokelat di putih)", "brand", "surface", 4.5),
    ("Teks tombol batal (merah di putih)", "bad", "surface", 4.5),
    ("Lencana: Dibayar (putih di hijau)", "putih", "ok", 4.5),
    ("Lencana: Menunggu (putih di oranye tua)", "putih", "warn", 4.5),
    ("Lencana: Dibatalkan (putih di merah)", "putih", "bad", 4.5),
    ("Lencana: Selesai (putih di abu-abu biru)", "putih", "done", 4.5),
    ("Garis tepi kolom isian di panel putih", "line-strong", "surface", 3.0),
    ("Cincin fokus di panel putih", "focus", "surface", 3.0),
    ("Cincin fokus di latar halaman", "focus", "bg", 3.0),
]


def _kanal(c):
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminans(hex_):
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _kanal(r) + 0.7152 * _kanal(g) + 0.0722 * _kanal(b)


def rasio(a, b):
    la, lb = luminans(a), luminans(b)
    terang, gelap = max(la, lb), min(la, lb)
    return (terang + 0.05) / (gelap + 0.05)


if __name__ == "__main__":
    gagal = 0
    print("| Pasangan | Depan | Belakang | Rasio | Ambang | Hasil |")
    print("|---|---|---|---|---|---|")
    for ket, dep, bel, ambang in PASANGAN:
        r = rasio(TOKEN[dep], TOKEN[bel])
        ok = r >= ambang
        gagal += not ok
        print(f"| {ket} | `{TOKEN[dep]}` | `{TOKEN[bel]}` | {r:.2f} : 1 | {ambang:g} : 1 | {'Lolos' if ok else 'GAGAL'} |")
    raise SystemExit(1 if gagal else 0)
