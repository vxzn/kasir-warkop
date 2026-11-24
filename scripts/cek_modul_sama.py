"""Pastikan salinan modul keamanan identik di semua layanan.

auth.py disalin ke setiap layanan karena tiap layanan dibangun sebagai image Docker sendiri.
Bila salah satu salinan berbeda, aturan keamanan antar-layanan bisa tidak konsisten.

Pemakaian:  python scripts/cek_modul_sama.py
"""
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent / "services"
LAYANAN = ["auth", "menu", "pesanan", "pembayaran"]

hash_per_layanan = {}
for nama in LAYANAN:
    f = ROOT / nama / "auth.py"
    if not f.exists():
        print(f"GAGAL: {f} tidak ada")
        sys.exit(1)
    hash_per_layanan[nama] = hashlib.sha256(f.read_bytes()).hexdigest()

if len(set(hash_per_layanan.values())) != 1:
    print("GAGAL: salinan auth.py berbeda:")
    for nama, h in hash_per_layanan.items():
        print(f"  {nama:11s} {h[:16]}")
    print("Perbaiki dengan menyalin services/auth/auth.py ke layanan lain.")
    sys.exit(1)

print(f"ok   : auth.py identik di {len(LAYANAN)} layanan ({next(iter(hash_per_layanan.values()))[:12]})")
