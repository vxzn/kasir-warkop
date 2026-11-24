"""Modul keamanan bersama.

Salinan modul ini identik di services/auth, services/menu, services/pesanan, dan
services/pembayaran (diperiksa oleh scripts/cek_modul_sama.py), karena setiap layanan
dibangun sebagai image Docker yang terpisah.

- Token pengguna: JWT HS256 yang dibuat dan diperiksa hanya dengan pustaka standar.
- Peran: 'kasir' dan 'pemilik'.
- Antar-layanan: header X-Service-Key (rahasia bersama), terpisah dari token pengguna.

Logika keputusan (periksa_akses) sengaja dibuat murni, tanpa FastAPI, supaya bisa
diuji langsung. FastAPI baru diimpor di dibutuhkan().
"""
import base64
import hashlib
import hmac
import json
import os
import time

ISSUER = "kasir-warkop-auth"
PERAN = ("kasir", "pemilik")
PANJANG_MINIMAL_RAHASIA = 16

_konfig = {"jwt": None, "layanan": None}


class TokenError(Exception):
    """Token tidak valid atau kedaluwarsa. Pesannya aman ditampilkan ke pengguna."""


class AksesDitolak(Exception):
    """Permintaan tidak boleh lanjut. status: 401 (belum masuk) atau 403 (tidak berhak)."""

    def __init__(self, status: int, pesan: str):
        super().__init__(pesan)
        self.status = status
        self.pesan = pesan


# ---------- Konfigurasi ----------
def muat_konfigurasi(jwt_secret=None, service_key=None, butuh_service_key=True):
    """Baca rahasia dari variabel lingkungan (atau argumen, untuk pengujian).

    Layanan menolak berjalan bila rahasia kosong atau terlalu pendek, supaya tidak
    pernah aktif tanpa perlindungan yang sebenarnya.
    """
    jwt = os.getenv("JWT_SECRET", "") if jwt_secret is None else jwt_secret
    if len(jwt) < PANJANG_MINIMAL_RAHASIA:
        raise RuntimeError("JWT_SECRET belum diatur atau kurang dari 16 karakter")
    svc = os.getenv("SERVICE_KEY", "") if service_key is None else service_key
    if butuh_service_key and len(svc) < PANJANG_MINIMAL_RAHASIA:
        raise RuntimeError("SERVICE_KEY belum diatur atau kurang dari 16 karakter")
    _konfig["jwt"] = jwt
    _konfig["layanan"] = svc or None


def rahasia_jwt() -> str:
    if not _konfig["jwt"]:
        raise RuntimeError("JWT_SECRET belum dimuat")
    return _konfig["jwt"]


def header_layanan() -> dict:
    """Header untuk pemanggilan antar-layanan (mis. pesanan -> menu)."""
    if not _konfig["layanan"]:
        raise RuntimeError("SERVICE_KEY belum dimuat")
    return {"X-Service-Key": _konfig["layanan"]}


# ---------- JWT HS256 ----------
def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _tanda(bagian: str, rahasia: str) -> bytes:
    return hmac.new(rahasia.encode(), bagian.encode(), hashlib.sha256).digest()


def buat_token(klaim: dict, rahasia: str, berlaku_detik: int, sekarang=None) -> str:
    t = int(time.time() if sekarang is None else sekarang)
    isi = {**klaim, "iss": ISSUER, "iat": t, "exp": t + int(berlaku_detik)}
    kepala = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    badan = _b64e(json.dumps(isi, separators=(",", ":"), sort_keys=True).encode())
    bagian = kepala + "." + badan
    return bagian + "." + _b64e(_tanda(bagian, rahasia))


def baca_token(token: str, rahasia=None, sekarang=None) -> dict:
    """Periksa tanda tangan, penerbit, masa berlaku, dan peran. Mengembalikan klaim."""
    rahasia = _konfig["jwt"] if rahasia is None else rahasia
    if not rahasia:
        raise RuntimeError("JWT_SECRET belum dimuat")
    try:
        kepala_b64, badan_b64, tanda_b64 = token.split(".")
        kepala = json.loads(_b64d(kepala_b64))
        tanda_kirim = _b64d(tanda_b64)
        if not isinstance(kepala, dict) or kepala.get("alg") != "HS256":
            raise TokenError("Token tidak valid")
        if not hmac.compare_digest(_tanda(kepala_b64 + "." + badan_b64, rahasia), tanda_kirim):
            raise TokenError("Token tidak valid")
        isi = json.loads(_b64d(badan_b64))
    except (ValueError, TypeError, AttributeError):
        raise TokenError("Token tidak valid")

    if not isinstance(isi, dict) or isi.get("iss") != ISSUER:
        raise TokenError("Token tidak valid")
    exp = isi.get("exp")
    if not isinstance(exp, int) or isinstance(exp, bool):
        raise TokenError("Token tidak valid")
    if (time.time() if sekarang is None else sekarang) >= exp:
        raise TokenError("Sesi sudah berakhir. Silakan masuk lagi.")
    if isi.get("role") not in PERAN or not isinstance(isi.get("sub"), str):
        raise TokenError("Token tidak valid")
    return isi


# ---------- Keputusan akses ----------
def _sama(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def periksa_akses(authorization, kunci_layanan, peran_boleh=(), layanan_boleh=False, sekarang=None) -> dict:
    """Putuskan apakah permintaan boleh lanjut. Mengembalikan klaim, atau melempar AksesDitolak.

    - Kunci layanan yang benar diterima hanya pada endpoint yang mengizinkan layanan.
    - Selain itu wajib token Bearer yang valid dengan peran yang diizinkan.
    """
    if kunci_layanan and layanan_boleh and _konfig["layanan"] and _sama(kunci_layanan, _konfig["layanan"]):
        return {"sub": "layanan", "nama": "layanan", "role": "layanan"}

    if not authorization:
        raise AksesDitolak(401, "Silakan masuk terlebih dahulu")
    skema, _, token = authorization.partition(" ")
    if skema.lower() != "bearer" or not token.strip():
        raise AksesDitolak(401, "Format Authorization harus 'Bearer <token>'")
    try:
        klaim = baca_token(token.strip(), sekarang=sekarang)
    except TokenError as e:
        raise AksesDitolak(401, str(e))
    if klaim["role"] not in peran_boleh:
        raise AksesDitolak(403, f"Peran '{klaim['role']}' tidak berhak mengakses sumber daya ini")
    return klaim


def dibutuhkan(*peran_boleh, layanan=False):
    """Dependensi FastAPI. Pakai: @app.get(..., dependencies=[Depends(auth.dibutuhkan('kasir'))]).

    peran_boleh: peran pengguna yang diizinkan. layanan=True: izinkan juga pemanggil
    antar-layanan yang membawa X-Service-Key. Tanpa peran dan layanan=True = khusus layanan.
    """
    for p in peran_boleh:
        if p not in PERAN:
            raise ValueError(f"Peran tidak dikenal: {p}")

    from fastapi import Header, HTTPException  # diimpor di sini agar modul ini bisa diuji tanpa FastAPI

    def dependensi(
        authorization: str | None = Header(default=None),
        x_service_key: str | None = Header(default=None),
    ):
        try:
            return periksa_akses(authorization, x_service_key, peran_boleh, layanan)
        except AksesDitolak as e:
            headers = {"WWW-Authenticate": "Bearer"} if e.status == 401 else None
            raise HTTPException(status_code=e.status, detail=e.pesan, headers=headers)

    return dependensi
