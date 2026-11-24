"""Data penjualan CONTOH untuk demo rekap (hanya aktif bila DEMO_DATA=true).

Mengisi tagihan LUNAS fiktif untuk beberapa hari sebelum hari ini, supaya rekap mingguan
dan bulanan tidak kosong saat presentasi. Baris contoh memakai pesanan_id NEGATIF agar
tidak pernah bertabrakan dengan pesanan sungguhan, dan tidak mengisi hari ini sehingga
angka "Hari ini" hanya mencerminkan transaksi nyata.
"""
import random
from datetime import date, timedelta

HARGA_MENU = [8000, 12000, 15000, 15000, 5000, 7000, 12000, 8000, 10000]
CARA_BAYAR = ["TUNAI"] * 11 + ["QRIS"] * 7 + ["TRANSFER"] * 2


def isi(conn, hari_ini: date, hari: int = 60, seed: int = 2026) -> int:
    """Isi data contoh. Aman dipanggil berulang: tidak menambah bila data contoh sudah ada.

    Mengembalikan jumlah baris yang ditambahkan.
    """
    if conn.execute("SELECT COUNT(*) FROM tagihan WHERE pesanan_id < 0").fetchone()[0]:
        return 0
    acak = random.Random(seed)
    baris = []
    nomor = 0
    for mundur in range(hari, 0, -1):
        d = hari_ini - timedelta(days=mundur)
        akhir_pekan = d.weekday() >= 5
        for _ in range(acak.randint(20, 35) if akhir_pekan else acak.randint(12, 22)):
            nomor += 1
            jumlah = sum(acak.choice(HARGA_MENU) for _ in range(acak.randint(1, 3)))
            jam, menit, detik = acak.randint(8, 21), acak.randint(0, 59), acak.randint(0, 59)
            bayar = f"{d.isoformat()}T{jam:02d}:{menit:02d}:{detik:02d}+07:00"
            buat = f"{d.isoformat()}T{jam:02d}:{max(menit - 3, 0):02d}:{detik:02d}+07:00"
            baris.append((-nomor, jumlah, "LUNAS", acak.choice(CARA_BAYAR), jumlah, 0, buat, bayar))
    conn.executemany(
        "INSERT INTO tagihan (pesanan_id, jumlah, status, metode, dibayar, kembalian, dibuat, waktu_bayar) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        baris,
    )
    return len(baris)
