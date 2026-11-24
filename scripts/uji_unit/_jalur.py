"""Menambahkan folder layanan ke sys.path supaya modul murni bisa diimpor tanpa Docker/FastAPI."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
for nama in ("auth", "pembayaran"):
    jalur = str(ROOT / "services" / nama)
    if jalur not in sys.path:
        sys.path.insert(0, jalur)
