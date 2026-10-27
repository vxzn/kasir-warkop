"""Membuat ikon PNG aplikasi (192 dan 512 px) tanpa pustaka tambahan.

Bentuknya sama dengan frontend/icons/icon.svg: cangkir krem di atas latar cokelat.
Jalankan:  python scripts/buat_ikon.py
"""
import pathlib
import struct
import zlib

CAKLAT = (0x6F, 0x4E, 0x37)
KRIM = (0xF7, 0xF1, 0xE8)
KELUAR = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "icons"


def kotak_bulat(x, y, x0, y0, x1, y1, r):
    """Persegi dengan dua sudut bawah membulat (koordinat 0..1)."""
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    if y > y1 - r:
        if x < x0 + r:
            return (x - (x0 + r)) ** 2 + (y - (y1 - r)) ** 2 <= r * r
        if x > x1 - r:
            return (x - (x1 - r)) ** 2 + (y - (y1 - r)) ** 2 <= r * r
    return True


def krim(x, y):
    # uap
    for cx in (0.36, 0.45, 0.54):
        if abs(x - cx) <= 0.014 and 0.23 <= y <= 0.375:
            return True
    # badan cangkir
    if kotak_bulat(x, y, 0.28, 0.42, 0.64, 0.70, 0.07):
        return True
    # piring alas
    if kotak_bulat(x, y, 0.22, 0.72, 0.70, 0.765, 0.02):
        return True
    # gagang
    d2 = (x - 0.654) ** 2 + (y - 0.529) ** 2
    return x > 0.62 and 0.05 ** 2 <= d2 <= 0.095 ** 2


def piksel(x, y):
    return KRIM if krim(x, y) else CAKLAT


def buat(ukuran, super_=2):
    baris = []
    for j in range(ukuran):
        row = bytearray([0])  # filter 0
        for i in range(ukuran):
            r = g = b = 0
            for sj in range(super_):
                for si in range(super_):
                    x = (i + (si + 0.5) / super_) / ukuran
                    y = (j + (sj + 0.5) / super_) / ukuran
                    pr, pg, pb = piksel(x, y)
                    r += pr; g += pg; b += pb
            n = super_ * super_
            row += bytes((r // n, g // n, b // n))
        baris.append(bytes(row))
    return b"".join(baris)


def tulis_png(path, ukuran):
    mentah = buat(ukuran)

    def chunk(tag, data):
        isi = tag + data
        return struct.pack(">I", len(data)) + isi + struct.pack(">I", zlib.crc32(isi) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", ukuran, ukuran, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(mentah, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


if __name__ == "__main__":
    KELUAR.mkdir(parents=True, exist_ok=True)
    for ukuran in (192, 512):
        tulis_png(KELUAR / f"icon-{ukuran}.png", ukuran)
        print("dibuat:", KELUAR / f"icon-{ukuran}.png")
