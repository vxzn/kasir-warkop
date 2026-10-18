"""Layanan Menu: daftar menu, harga, dan stok."""
import os
import sqlite3
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DB_PATH = os.getenv("DB_PATH", "menu.db")

app = FastAPI(title="Layanan Menu - Kasir Warkop")

# Data awal, hanya dimasukkan kalau tabel masih kosong.
SEED = [
    ("Kopi Hitam", "Kopi", 8000, 100),
    ("Kopi Susu", "Kopi", 12000, 100),
    ("Cappuccino", "Kopi", 15000, 50),
    ("Es Kopi Gula Aren", "Kopi", 15000, 50),
    ("Teh Manis", "Minuman", 5000, 100),
    ("Es Jeruk", "Minuman", 7000, 60),
    ("Mie Instan Telur", "Makanan", 12000, 40),
    ("Pisang Goreng", "Makanan", 8000, 40),
    ("Roti Bakar Coklat", "Makanan", 10000, 30),
]


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
            CREATE TABLE IF NOT EXISTS menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT NOT NULL,
                kategori TEXT NOT NULL DEFAULT 'Lainnya',
                harga INTEGER NOT NULL CHECK (harga > 0),
                stok INTEGER NOT NULL DEFAULT 0 CHECK (stok >= 0)
            )
            """
        )
        if conn.execute("SELECT COUNT(*) FROM menu").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO menu (nama, kategori, harga, stok) VALUES (?, ?, ?, ?)",
                SEED,
            )


init_db()


class MenuBaru(BaseModel):
    nama: str = Field(min_length=1)
    kategori: str = "Lainnya"
    harga: int = Field(gt=0)
    stok: int = Field(default=0, ge=0)


class PerubahanStok(BaseModel):
    # Negatif = mengurangi stok (pesanan), positif = menambah (batal/restock).
    delta: int


@app.get("/health")
def health():
    return {"status": "ok", "service": "menu"}


@app.get("/menu")
def daftar_menu(kategori: str | None = None):
    with db() as conn:
        if kategori:
            rows = conn.execute(
                "SELECT * FROM menu WHERE kategori = ? ORDER BY id", (kategori,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM menu ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@app.get("/menu/{menu_id}")
def detail_menu(menu_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM menu WHERE id = ?", (menu_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Menu tidak ditemukan")
    return dict(row)


@app.post("/menu", status_code=201)
def tambah_menu(data: MenuBaru):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO menu (nama, kategori, harga, stok) VALUES (?, ?, ?, ?)",
            (data.nama, data.kategori, data.harga, data.stok),
        )
        row = conn.execute("SELECT * FROM menu WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.post("/menu/{menu_id}/stok")
def ubah_stok(menu_id: int, data: PerubahanStok):
    """Ubah stok secara atomik. Gagal (409) kalau stok akan menjadi negatif."""
    with db() as conn:
        cur = conn.execute(
            "UPDATE menu SET stok = stok + ? WHERE id = ? AND stok + ? >= 0",
            (data.delta, menu_id, data.delta),
        )
        row = conn.execute("SELECT * FROM menu WHERE id = ?", (menu_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Menu tidak ditemukan")
        if cur.rowcount == 0:
            raise HTTPException(409, "Stok tidak cukup")
    return dict(row)
