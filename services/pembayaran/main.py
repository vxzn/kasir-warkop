"""Layanan Pembayaran: membuat tagihan, menerima pembayaran, menghitung
kembalian, lalu memberi tahu Layanan Pesanan bahwa pesanan sudah dibayar."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DB_PATH = os.getenv("DB_PATH", "pembayaran.db")
PESANAN_URL = os.getenv("PESANAN_URL", "http://pesanan:8000").rstrip("/")
WIB = timezone(timedelta(hours=7))

app = FastAPI(title="Layanan Pembayaran - Kasir Warkop")


def sekarang() -> datetime:
    return datetime.now(WIB)


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tagihan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pesanan_id INTEGER NOT NULL UNIQUE,
                jumlah INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'BELUM_BAYAR',
                metode TEXT,
                dibayar INTEGER,
                kembalian INTEGER,
                dibuat TEXT NOT NULL,
                waktu_bayar TEXT
            )
            """
        )


init_db()


class TagihanBaru(BaseModel):
    pesanan_id: int
    jumlah: int = Field(gt=0)


class Pembayaran(BaseModel):
    metode: Literal["TUNAI", "QRIS", "TRANSFER"] = "TUNAI"
    # Kosong = uang pas.
    jumlah_bayar: int | None = Field(default=None, gt=0)


def _ambil(conn, pesanan_id: int):
    row = conn.execute(
        "SELECT * FROM tagihan WHERE pesanan_id = ?", (pesanan_id,)
    ).fetchone()
    return dict(row) if row else None


@app.get("/health")
def health():
    return {"status": "ok", "service": "pembayaran"}


@app.post("/tagihan", status_code=201)
def buat_tagihan(data: TagihanBaru):
    with db() as conn:
        try:
            conn.execute(
                "INSERT INTO tagihan (pesanan_id, jumlah, status, dibuat) "
                "VALUES (?, ?, 'BELUM_BAYAR', ?)",
                (data.pesanan_id, data.jumlah, sekarang().isoformat(timespec="seconds")),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Tagihan untuk pesanan ini sudah ada")
        return _ambil(conn, data.pesanan_id)


@app.get("/tagihan")
def daftar_tagihan(status: str | None = None):
    with db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM tagihan WHERE status = ? ORDER BY id DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tagihan ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


# Harus dideklarasikan sebelum /tagihan/{pesanan_id}.
@app.get("/tagihan/laporan")
def laporan_hari_ini():
    hari_ini = sekarang().date().isoformat()
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(jumlah), 0) AS total "
            "FROM tagihan WHERE status = 'LUNAS' AND waktu_bayar LIKE ?",
            (hari_ini + "%",),
        ).fetchone()
    return {
        "tanggal": hari_ini,
        "jumlah_transaksi": row["n"],
        "total_pendapatan": row["total"],
    }


@app.get("/tagihan/{pesanan_id}")
def detail_tagihan(pesanan_id: int):
    with db() as conn:
        t = _ambil(conn, pesanan_id)
    if t is None:
        raise HTTPException(404, "Tagihan tidak ditemukan")
    return t


@app.post("/tagihan/{pesanan_id}/bayar")
def bayar(pesanan_id: int, data: Pembayaran):
    with db() as conn:
        t = _ambil(conn, pesanan_id)
    if t is None:
        raise HTTPException(404, "Tagihan tidak ditemukan")
    if t["status"] != "BELUM_BAYAR":
        raise HTTPException(409, f"Tagihan sudah berstatus {t['status']}")

    dibayar = data.jumlah_bayar if data.jumlah_bayar is not None else t["jumlah"]
    if dibayar < t["jumlah"]:
        raise HTTPException(
            400, f"Uang kurang Rp {t['jumlah'] - dibayar:,}".replace(",", ".")
        )
    kembalian = dibayar - t["jumlah"]

    # Tandai LUNAS secara atomik supaya tidak bisa dibayar dua kali.
    with db() as conn:
        cur = conn.execute(
            "UPDATE tagihan SET status = 'LUNAS', metode = ?, dibayar = ?, "
            "kembalian = ?, waktu_bayar = ? WHERE pesanan_id = ? AND status = 'BELUM_BAYAR'",
            (
                data.metode,
                dibayar,
                kembalian,
                sekarang().isoformat(timespec="seconds"),
                pesanan_id,
            ),
        )
        if cur.rowcount == 0:
            raise HTTPException(409, "Tagihan baru saja diproses, coba muat ulang")

    # Beri tahu Layanan Pesanan. Kalau gagal, kembalikan status tagihan.
    try:
        r = httpx.patch(
            f"{PESANAN_URL}/pesanan/{pesanan_id}/status",
            json={"status": "DIBAYAR"},
            timeout=5,
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        status_baru = "BATAL" if e.response.status_code == 409 else "BELUM_BAYAR"
        _set_status(pesanan_id, status_baru)
        if e.response.status_code == 409:
            raise HTTPException(409, "Pesanan tidak bisa dibayar (mungkin sudah dibatalkan)")
        raise HTTPException(502, "Layanan pesanan menolak pembaruan status")
    except httpx.HTTPError:
        _set_status(pesanan_id, "BELUM_BAYAR")
        raise HTTPException(502, "Layanan pesanan tidak dapat dihubungi")

    with db() as conn:
        return _ambil(conn, pesanan_id)


def _set_status(pesanan_id: int, status: str):
    with db() as conn:
        conn.execute(
            "UPDATE tagihan SET status = ?, metode = NULL, dibayar = NULL, "
            "kembalian = NULL, waktu_bayar = NULL WHERE pesanan_id = ?",
            (status, pesanan_id),
        )


@app.post("/tagihan/{pesanan_id}/batal")
def batalkan_tagihan(pesanan_id: int):
    with db() as conn:
        t = _ambil(conn, pesanan_id)
        if t is None:
            raise HTTPException(404, "Tagihan tidak ditemukan")
        conn.execute(
            "UPDATE tagihan SET status = 'BATAL' "
            "WHERE pesanan_id = ? AND status = 'BELUM_BAYAR'",
            (pesanan_id,),
        )
        return _ambil(conn, pesanan_id)
