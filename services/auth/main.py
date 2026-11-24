"""Layanan Auth: masuk (login), identitas pengguna, dan kelola akun.

Layanan ini hanya menerbitkan token. Layanan lain (menu, pesanan, pembayaran) memeriksa token
sendiri dengan rahasia bersama, jadi tetap berjalan walau layanan Auth sedang mati
(sesi yang sudah ada tidak terputus).
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

import auth
import pengguna
from pembatas import PembatasLogin

DB_PATH = os.getenv("DB_PATH", "auth.db")
TOKEN_JAM = float(os.getenv("TOKEN_JAM", "8"))
WIB = timezone(timedelta(hours=7))

auth.muat_konfigurasi(butuh_service_key=False)

app = FastAPI(title="Layanan Auth - Kasir Warkop")
pembatas = PembatasLogin(maks_gagal=5, jendela=300, kunci=60)


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def sekarang_iso() -> str:
    return datetime.now(WIB).isoformat(timespec="seconds")


def _mulai():
    with db() as conn:
        pengguna.init(conn)
        pengguna.isi_awal(
            conn,
            os.getenv("PEMILIK_PASSWORD", "pemilik123"),
            os.getenv("KASIR_PASSWORD", "kasir123"),
            sekarang_iso(),
        )


_mulai()


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=200)


class PenggunaBaru(BaseModel):
    username: str
    nama: str
    role: str
    password: str


class GantiSandi(BaseModel):
    sandi_lama: str
    sandi_baru: str


def _kunci_percobaan(request: Request, username: str) -> str:
    # Nginx mengisi X-Real-IP dengan alamat klien yang sebenarnya.
    ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "?")
    return f"{username.strip().lower()}|{ip}"


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth"}


# Satu-satunya endpoint tanpa token, karena memang pintu masuknya.
@app.post("/auth/login")
def masuk(data: LoginIn, request: Request):
    kunci = _kunci_percobaan(request, data.username)
    sisa = pembatas.sisa_kunci(kunci)
    if sisa > 0:
        raise HTTPException(
            status_code=429,
            detail=f"Terlalu banyak percobaan. Coba lagi dalam {sisa} detik.",
            headers={"Retry-After": str(sisa)},
        )
    with db() as conn:
        user = pengguna.autentikasi(conn, data.username, data.password)
    if user is None:
        pembatas.gagal(kunci)
        # Pesan sengaja sama untuk nama salah maupun kata sandi salah.
        raise HTTPException(status_code=401, detail="Nama pengguna atau kata sandi salah")
    pembatas.berhasil(kunci)
    detik = int(TOKEN_JAM * 3600)
    token = auth.buat_token(
        {"sub": user["username"], "nama": user["nama"], "role": user["role"]},
        auth.rahasia_jwt(),
        detik,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": detik,
        "user": {"username": user["username"], "nama": user["nama"], "role": user["role"]},
    }


@app.get("/auth/me")
def saya(klaim: dict = Depends(auth.dibutuhkan("kasir", "pemilik"))):
    with db() as conn:
        user = pengguna.cari(conn, klaim["sub"])
    if user is None or not user["aktif"]:
        raise HTTPException(status_code=401, detail="Akun tidak ditemukan atau dinonaktifkan")
    return {
        "username": user["username"],
        "nama": user["nama"],
        "role": user["role"],
        "berlaku_sampai": klaim["exp"],
    }


@app.post("/auth/ganti-sandi")
def ganti_sandi(data: GantiSandi, klaim: dict = Depends(auth.dibutuhkan("kasir", "pemilik"))):
    try:
        with db() as conn:
            pengguna.ganti_sandi(conn, klaim["sub"], data.sandi_lama, data.sandi_baru)
    except pengguna.PenggunaError as e:
        raise HTTPException(status_code=e.status, detail=e.pesan)
    return {"pesan": "Kata sandi diperbarui"}


@app.get("/auth/users", dependencies=[Depends(auth.dibutuhkan("pemilik"))])
def daftar_pengguna():
    with db() as conn:
        return pengguna.daftar(conn)


@app.post("/auth/users", status_code=201, dependencies=[Depends(auth.dibutuhkan("pemilik"))])
def tambah_pengguna(data: PenggunaBaru):
    try:
        with db() as conn:
            return pengguna.buat(conn, data.username, data.nama, data.role, data.password, sekarang_iso())
    except pengguna.PenggunaError as e:
        raise HTTPException(status_code=e.status, detail=e.pesan)
