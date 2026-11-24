"""Penyimpanan dan pemeriksaan akun pengguna (SQLite). Fungsi murni terhadap koneksi sqlite3."""
import re

import sqlite3

from auth import PERAN
from kata_sandi import HASH_TIRUAN, cocok, hash_sandi

POLA_USERNAME = re.compile(r"^[a-z0-9_.-]{3,30}$")
SANDI_MINIMAL = 6
SANDI_MAKSIMAL = 200


class PenggunaError(Exception):
    """Kesalahan yang aman ditampilkan ke pengguna. status: kode HTTP yang cocok."""

    def __init__(self, pesan: str, status: int = 422):
        super().__init__(pesan)
        self.pesan = pesan
        self.status = status


def init(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pengguna (
            username TEXT PRIMARY KEY,
            nama TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('kasir', 'pemilik')),
            sandi TEXT NOT NULL,
            aktif INTEGER NOT NULL DEFAULT 1,
            dibuat TEXT NOT NULL
        )
        """
    )


def _tampil(r) -> dict:
    return {"username": r[0], "nama": r[1], "role": r[2], "aktif": bool(r[3]), "dibuat": r[4]}


def _periksa_sandi(sandi: str):
    if len(sandi) < SANDI_MINIMAL:
        raise PenggunaError(f"Kata sandi minimal {SANDI_MINIMAL} karakter")
    if len(sandi) > SANDI_MAKSIMAL:
        raise PenggunaError(f"Kata sandi maksimal {SANDI_MAKSIMAL} karakter")


def jumlah(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM pengguna").fetchone()[0]


def buat(conn, username: str, nama: str, role: str, sandi: str, dibuat_iso: str) -> dict:
    u = username.strip().lower()
    if not POLA_USERNAME.match(u):
        raise PenggunaError("Nama pengguna 3-30 karakter: huruf kecil, angka, titik, garis bawah, atau strip")
    nama = nama.strip()
    if not 1 <= len(nama) <= 60:
        raise PenggunaError("Nama lengkap wajib diisi (maksimal 60 karakter)")
    if role not in PERAN:
        raise PenggunaError("Peran harus 'kasir' atau 'pemilik'")
    _periksa_sandi(sandi)
    try:
        conn.execute(
            "INSERT INTO pengguna (username, nama, role, sandi, aktif, dibuat) VALUES (?, ?, ?, ?, 1, ?)",
            (u, nama, role, hash_sandi(sandi), dibuat_iso),
        )
    except sqlite3.IntegrityError:
        raise PenggunaError("Nama pengguna sudah dipakai", 409)
    return cari(conn, u)


def cari(conn, username: str):
    r = conn.execute(
        "SELECT username, nama, role, aktif, dibuat FROM pengguna WHERE username = ?",
        (username.strip().lower(),),
    ).fetchone()
    return _tampil(r) if r else None


def daftar(conn) -> list:
    rows = conn.execute(
        "SELECT username, nama, role, aktif, dibuat FROM pengguna ORDER BY role DESC, username"
    ).fetchall()
    return [_tampil(r) for r in rows]


def autentikasi(conn, username: str, sandi: str):
    """Kembalikan data pengguna bila nama dan kata sandi cocok dan akun aktif; selain itu None."""
    r = conn.execute(
        "SELECT username, nama, role, aktif, dibuat, sandi FROM pengguna WHERE username = ?",
        (username.strip().lower(),),
    ).fetchone()
    if r is None:
        cocok(sandi, HASH_TIRUAN)
        return None
    if not cocok(sandi, r[5]) or not r[3]:
        return None
    return _tampil(r)


def ganti_sandi(conn, username: str, sandi_lama: str, sandi_baru: str):
    if autentikasi(conn, username, sandi_lama) is None:
        raise PenggunaError("Kata sandi lama salah", 403)
    _periksa_sandi(sandi_baru)
    conn.execute(
        "UPDATE pengguna SET sandi = ? WHERE username = ?",
        (hash_sandi(sandi_baru), username.strip().lower()),
    )


def isi_awal(conn, sandi_pemilik: str, sandi_kasir: str, dibuat_iso: str) -> int:
    """Buat akun bawaan hanya bila tabel masih kosong. Kembalikan jumlah akun yang dibuat."""
    if jumlah(conn) > 0:
        return 0
    buat(conn, "pemilik", "Pemilik Warkop", "pemilik", sandi_pemilik, dibuat_iso)
    buat(conn, "kasir1", "Kasir 1", "kasir", sandi_kasir, dibuat_iso)
    return 2
