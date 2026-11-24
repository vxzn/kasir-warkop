"""Hash kata sandi dengan PBKDF2-HMAC-SHA256 (pustaka standar, tanpa dependensi tambahan).

Format tersimpan: pbkdf2_sha256$<iterasi>$<garam hex>$<hash hex>
Kata sandi asli tidak pernah disimpan.
"""
import hashlib
import hmac
import os

SKEMA = "pbkdf2_sha256"
ITERASI = 200_000


def hash_sandi(sandi: str, iterasi: int = ITERASI, garam: bytes | None = None) -> str:
    garam = os.urandom(16) if garam is None else garam
    h = hashlib.pbkdf2_hmac("sha256", sandi.encode(), garam, iterasi)
    return f"{SKEMA}${iterasi}${garam.hex()}${h.hex()}"


def cocok(sandi: str, tersimpan: str) -> bool:
    try:
        skema, iterasi, garam, h = tersimpan.split("$")
        iterasi = int(iterasi)
        garam = bytes.fromhex(garam)
        diharapkan = bytes.fromhex(h)
    except (ValueError, AttributeError):
        return False
    if skema != SKEMA or iterasi < 1:
        return False
    hitung = hashlib.pbkdf2_hmac("sha256", sandi.encode(), garam, iterasi)
    return hmac.compare_digest(hitung, diharapkan)


# Dipakai saat nama pengguna tidak ditemukan, supaya waktu respons tidak membocorkan
# apakah nama pengguna itu ada.
HASH_TIRUAN = hash_sandi("tiruan-untuk-menyamakan-waktu")
