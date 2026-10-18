"""Layanan Pesanan: membuat pesanan, memotong stok (via Layanan Menu),
dan meminta tagihan (via Layanan Pembayaran)."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DB_PATH = os.getenv("DB_PATH", "pesanan.db")
MENU_URL = os.getenv("MENU_URL", "http://menu:8000").rstrip("/")
PEMBAYARAN_URL = os.getenv("PEMBAYARAN_URL", "http://pembayaran:8000").rstrip("/")
WIB = timezone(timedelta(hours=7))

app = FastAPI(title="Layanan Pesanan - Kasir Warkop")

# Status yang boleh dituju dari status sekarang.
TRANSISI = {
    "MENUNGGU_PEMBAYARAN": {"DIBAYAR", "BATAL"},
    "DIBAYAR": {"SELESAI"},
    "SELESAI": set(),
    "BATAL": set(),
}


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
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS pesanan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama_pelanggan TEXT NOT NULL,
                meja TEXT,
                total INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'MENUNGGU_PEMBAYARAN',
                dibuat TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS item_pesanan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pesanan_id INTEGER NOT NULL REFERENCES pesanan(id),
                menu_id INTEGER NOT NULL,
                nama TEXT NOT NULL,
                harga INTEGER NOT NULL,
                jumlah INTEGER NOT NULL
            );
            """
        )


init_db()


class ItemBaru(BaseModel):
    menu_id: int
    jumlah: int = Field(gt=0)


class PesananBaru(BaseModel):
    nama_pelanggan: str = Field(default="Pelanggan", min_length=1)
    meja: str | None = None
    item: list[ItemBaru] = Field(min_length=1)


class UbahStatus(BaseModel):
    # BATAL sengaja tidak ada di sini; gunakan POST /pesanan/{id}/batal
    # supaya stok ikut dikembalikan.
    status: Literal["DIBAYAR", "SELESAI"]


def _ambil(conn, pesanan_id: int):
    p = conn.execute("SELECT * FROM pesanan WHERE id = ?", (pesanan_id,)).fetchone()
    if p is None:
        return None
    hasil = dict(p)
    hasil["item"] = [
        dict(i)
        for i in conn.execute(
            "SELECT menu_id, nama, harga, jumlah FROM item_pesanan WHERE pesanan_id = ?",
            (pesanan_id,),
        ).fetchall()
    ]
    return hasil


def _pulihkan_stok(item: list[tuple[int, int]]):
    """Kembalikan stok ke Layanan Menu (best effort)."""
    with httpx.Client(timeout=5) as client:
        for menu_id, jumlah in item:
            try:
                client.post(f"{MENU_URL}/menu/{menu_id}/stok", json={"delta": jumlah})
            except httpx.HTTPError:
                pass


def _gagalkan(dipotong: list[tuple[int, int]], pesanan_id: int | None):
    """Batalkan efek pesanan yang gagal dibuat: stok kembali, data dihapus."""
    _pulihkan_stok(dipotong)
    if pesanan_id is not None:
        with db() as conn:
            conn.execute("DELETE FROM item_pesanan WHERE pesanan_id = ?", (pesanan_id,))
            conn.execute("DELETE FROM pesanan WHERE id = ?", (pesanan_id,))


@app.get("/health")
def health():
    return {"status": "ok", "service": "pesanan"}


@app.post("/pesanan", status_code=201)
def buat_pesanan(data: PesananBaru):
    dipotong: list[tuple[int, int]] = []
    pesanan_id = None
    try:
        with httpx.Client(timeout=5) as client:
            baris = []
            for it in data.item:
                r = client.get(f"{MENU_URL}/menu/{it.menu_id}")
                if r.status_code == 404:
                    raise HTTPException(404, f"Menu dengan id {it.menu_id} tidak ditemukan")
                r.raise_for_status()
                menu = r.json()

                r = client.post(
                    f"{MENU_URL}/menu/{it.menu_id}/stok", json={"delta": -it.jumlah}
                )
                if r.status_code == 409:
                    raise HTTPException(409, f"Stok {menu['nama']} tidak cukup")
                r.raise_for_status()

                dipotong.append((it.menu_id, it.jumlah))
                baris.append((it.menu_id, menu["nama"], menu["harga"], it.jumlah))

            total = sum(harga * jumlah for _, _, harga, jumlah in baris)
            with db() as conn:
                cur = conn.execute(
                    "INSERT INTO pesanan (nama_pelanggan, meja, total, status, dibuat) "
                    "VALUES (?, ?, ?, 'MENUNGGU_PEMBAYARAN', ?)",
                    (
                        data.nama_pelanggan,
                        data.meja,
                        total,
                        datetime.now(WIB).isoformat(timespec="seconds"),
                    ),
                )
                pesanan_id = cur.lastrowid
                conn.executemany(
                    "INSERT INTO item_pesanan (pesanan_id, menu_id, nama, harga, jumlah) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [(pesanan_id, *b) for b in baris],
                )

            r = client.post(
                f"{PEMBAYARAN_URL}/tagihan",
                json={"pesanan_id": pesanan_id, "jumlah": total},
            )
            r.raise_for_status()
    except HTTPException:
        _gagalkan(dipotong, pesanan_id)
        raise
    except httpx.HTTPError:
        _gagalkan(dipotong, pesanan_id)
        raise HTTPException(502, "Layanan menu/pembayaran tidak dapat dihubungi")

    with db() as conn:
        return _ambil(conn, pesanan_id)


@app.get("/pesanan")
def daftar_pesanan(status: str | None = None, limit: int = 50):
    with db() as conn:
        if status:
            rows = conn.execute(
                "SELECT id FROM pesanan WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id FROM pesanan ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_ambil(conn, r["id"]) for r in rows]


@app.get("/pesanan/{pesanan_id}")
def detail_pesanan(pesanan_id: int):
    with db() as conn:
        p = _ambil(conn, pesanan_id)
    if p is None:
        raise HTTPException(404, "Pesanan tidak ditemukan")
    return p


@app.patch("/pesanan/{pesanan_id}/status")
def ubah_status(pesanan_id: int, data: UbahStatus):
    """Dipakai Layanan Pembayaran (-> DIBAYAR) dan tombol 'Selesai' di kasir."""
    with db() as conn:
        p = _ambil(conn, pesanan_id)
        if p is None:
            raise HTTPException(404, "Pesanan tidak ditemukan")
        if data.status not in TRANSISI[p["status"]]:
            raise HTTPException(
                409, f"Pesanan berstatus {p['status']}, tidak bisa diubah ke {data.status}"
            )
        cur = conn.execute(
            "UPDATE pesanan SET status = ? WHERE id = ? AND status = ?",
            (data.status, pesanan_id, p["status"]),
        )
        if cur.rowcount == 0:
            raise HTTPException(409, "Status pesanan baru saja berubah, coba lagi")
        return _ambil(conn, pesanan_id)


@app.post("/pesanan/{pesanan_id}/batal")
def batalkan_pesanan(pesanan_id: int):
    """Batalkan pesanan yang belum dibayar: stok dikembalikan, tagihan dibatalkan."""
    with db() as conn:
        p = _ambil(conn, pesanan_id)
        if p is None:
            raise HTTPException(404, "Pesanan tidak ditemukan")
        cur = conn.execute(
            "UPDATE pesanan SET status = 'BATAL' "
            "WHERE id = ? AND status = 'MENUNGGU_PEMBAYARAN'",
            (pesanan_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(
                409, f"Pesanan berstatus {p['status']}, hanya pesanan yang belum dibayar bisa dibatalkan"
            )

    _pulihkan_stok([(i["menu_id"], i["jumlah"]) for i in p["item"]])
    try:
        httpx.post(f"{PEMBAYARAN_URL}/tagihan/{pesanan_id}/batal", timeout=5)
    except httpx.HTTPError:
        pass

    with db() as conn:
        return _ambil(conn, pesanan_id)
