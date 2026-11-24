"""Uji rekap penjualan harian/mingguan/bulanan dan data contoh."""
import sqlite3
import unittest
from datetime import date

import _jalur  # noqa: F401
import contoh_data
import rekap

BUAT_TABEL = """
CREATE TABLE tagihan (
    id INTEGER PRIMARY KEY AUTOINCREMENT, pesanan_id INTEGER NOT NULL UNIQUE, jumlah INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'BELUM_BAYAR', metode TEXT, dibayar INTEGER, kembalian INTEGER,
    dibuat TEXT NOT NULL, waktu_bayar TEXT)
"""


_koneksi = []


def db_kosong():
    c = sqlite3.connect(":memory:")
    c.execute(BUAT_TABEL)
    _koneksi.append(c)
    return c


def tearDownModule():
    for c in _koneksi:
        c.close()


def tambah(c, pid, jumlah, waktu, metode="TUNAI", status="LUNAS"):
    c.execute(
        "INSERT INTO tagihan (pesanan_id, jumlah, status, metode, dibuat, waktu_bayar) VALUES (?,?,?,?,?,?)",
        (pid, jumlah, status, metode, waktu, waktu if status == "LUNAS" else None),
    )


class UjiRentang(unittest.TestCase):
    def test_harian(self):
        self.assertEqual(rekap.rentang("harian", date(2026, 11, 18)), (date(2026, 11, 18), date(2026, 11, 19)))

    def test_mingguan_senin_sampai_minggu(self):
        # 18 Nov 2026 hari Rabu -> pekan 16 (Sen) s.d. 22 (Min) Nov
        self.assertEqual(rekap.rentang("mingguan", date(2026, 11, 18)), (date(2026, 11, 16), date(2026, 11, 23)))
        self.assertEqual(date(2026, 11, 16).weekday(), 0)
        # Senin dan Minggu termasuk pekan yang sama
        self.assertEqual(rekap.rentang("mingguan", date(2026, 11, 16))[0], date(2026, 11, 16))
        self.assertEqual(rekap.rentang("mingguan", date(2026, 11, 22))[0], date(2026, 11, 16))
        # Senin berikutnya sudah pekan baru
        self.assertEqual(rekap.rentang("mingguan", date(2026, 11, 23))[0], date(2026, 11, 23))

    def test_mingguan_melintasi_bulan_dan_tahun(self):
        dari, sampai = rekap.rentang("mingguan", date(2026, 12, 31))   # Kamis
        self.assertEqual((dari, sampai), (date(2026, 12, 28), date(2027, 1, 4)))

    def test_bulanan(self):
        self.assertEqual(rekap.rentang("bulanan", date(2026, 11, 18)), (date(2026, 11, 1), date(2026, 12, 1)))
        self.assertEqual(rekap.rentang("bulanan", date(2026, 12, 5)), (date(2026, 12, 1), date(2027, 1, 1)))
        self.assertEqual(rekap.rentang("bulanan", date(2028, 2, 10)), (date(2028, 2, 1), date(2028, 3, 1)))  # kabisat

    def test_periode_tidak_dikenal(self):
        with self.assertRaises(ValueError):
            rekap.rentang("tahunan", date(2026, 1, 1))


class UjiSusun(unittest.TestCase):
    ACUAN = date(2026, 11, 18)
    DATA = [
        ("2026-11-18T08:15:00+07:00", 20000, "TUNAI"),
        ("2026-11-18T08:50:00+07:00", 10000, "QRIS"),
        ("2026-11-18T14:05:00+07:00", 30000, "TUNAI"),
        ("2026-11-16T09:00:00+07:00", 40000, "TRANSFER"),    # Senin pekan yang sama
        ("2026-11-22T21:59:59+07:00", 5000, "QRIS"),         # Minggu pekan yang sama
        ("2026-11-23T08:00:00+07:00", 99999, "TUNAI"),       # pekan berikutnya: tidak ikut
        ("2026-10-31T23:59:59+07:00", 88888, "TUNAI"),       # bulan lalu: tidak ikut
    ]

    def test_harian(self):
        r = rekap.susun_rekap(self.DATA, "harian", self.ACUAN)
        self.assertEqual((r["jumlah_transaksi"], r["total_pendapatan"]), (3, 60000))
        self.assertEqual(r["rata_rata_transaksi"], 20000)
        self.assertEqual(len(r["rincian"]), 24)
        per_jam = {x["kunci"]: x for x in r["rincian"]}
        self.assertEqual((per_jam["08"]["jumlah_transaksi"], per_jam["08"]["total"]), (2, 30000))
        self.assertEqual(per_jam["14"]["total"], 30000)
        self.assertEqual(per_jam["10"]["total"], 0)
        self.assertEqual(r["puncak"]["total"], 30000)

    def test_mingguan(self):
        r = rekap.susun_rekap(self.DATA, "mingguan", self.ACUAN)
        self.assertEqual((r["dari"], r["sampai"]), ("2026-11-16", "2026-11-22"))
        self.assertEqual((r["jumlah_transaksi"], r["total_pendapatan"]), (5, 105000))
        self.assertEqual([x["kunci"] for x in r["rincian"]][0], "2026-11-16")
        self.assertEqual(len(r["rincian"]), 7)
        self.assertEqual(r["rincian"][0]["label"], "Sen 16")
        self.assertEqual(r["rincian"][6]["total"], 5000)           # Minggu 22 masuk
        self.assertEqual(sum(x["total"] for x in r["rincian"]), r["total_pendapatan"])
        self.assertEqual((r["puncak"]["kunci"], r["puncak"]["total"]), ("2026-11-18", 60000))   # Rabu paling ramai
        self.assertEqual(r["label"], "16 Nov 2026 - 22 Nov 2026")

    def test_bulanan(self):
        r = rekap.susun_rekap(self.DATA, "bulanan", self.ACUAN)
        self.assertEqual(len(r["rincian"]), 30)                    # November 30 hari
        self.assertEqual((r["jumlah_transaksi"], r["total_pendapatan"]), (6, 204999))
        self.assertEqual(r["label"], "November 2026")
        self.assertEqual(r["rincian"][22]["kunci"], "2026-11-23")

    def test_per_metode_lengkap_dan_konsisten(self):
        r = rekap.susun_rekap(self.DATA, "mingguan", self.ACUAN)
        m = {x["metode"]: x for x in r["per_metode"]}
        self.assertEqual(set(m), {"TUNAI", "QRIS", "TRANSFER"})
        self.assertEqual((m["TUNAI"]["total"], m["QRIS"]["total"], m["TRANSFER"]["total"]), (50000, 15000, 40000))
        self.assertEqual(sum(x["jumlah_transaksi"] for x in r["per_metode"]), r["jumlah_transaksi"])

    def test_kosong(self):
        r = rekap.susun_rekap([], "bulanan", self.ACUAN)
        self.assertEqual((r["jumlah_transaksi"], r["total_pendapatan"], r["rata_rata_transaksi"]), (0, 0, 0))
        self.assertIsNone(r["puncak"])
        self.assertTrue(all(x["total"] == 0 for x in r["rincian"]))

    def test_februari_kabisat(self):
        self.assertEqual(len(rekap.susun_rekap([], "bulanan", date(2028, 2, 10))["rincian"]), 29)
        self.assertEqual(len(rekap.susun_rekap([], "bulanan", date(2026, 2, 10))["rincian"]), 28)


class UjiDatabase(unittest.TestCase):
    def setUp(self):
        self.c = db_kosong()
        self.c.row_factory = sqlite3.Row      # sama seperti layanan pembayaran
        tambah(self.c, 1, 20000, "2026-11-18T08:15:00+07:00", "TUNAI")
        tambah(self.c, 2, 30000, "2026-11-17T10:00:00+07:00", "QRIS")
        tambah(self.c, 3, 15000, "2026-11-18T09:00:00+07:00", "QRIS", status="BATAL")        # bukan LUNAS
        tambah(self.c, 4, 12000, "2026-11-18T09:30:00+07:00", "TUNAI", status="BELUM_BAYAR")  # bukan LUNAS
        tambah(self.c, 5, 50000, "2026-11-09T12:00:00+07:00", "TUNAI")                       # pekan lalu

    def test_hanya_tagihan_lunas_dihitung(self):
        r = rekap.ambil_rekap(self.c, "harian", date(2026, 11, 18))
        self.assertEqual((r["jumlah_transaksi"], r["total_pendapatan"]), (1, 20000))

    def test_batas_tengah_malam(self):
        tambah(self.c, 6, 7000, "2026-11-18T00:00:00+07:00")
        tambah(self.c, 7, 9000, "2026-11-18T23:59:59+07:00")
        tambah(self.c, 8, 11000, "2026-11-19T00:00:00+07:00")
        r = rekap.ambil_rekap(self.c, "harian", date(2026, 11, 18))
        self.assertEqual(r["total_pendapatan"], 20000 + 7000 + 9000)

    def test_perbandingan_periode_sebelumnya(self):
        r = rekap.ambil_rekap(self.c, "mingguan", date(2026, 11, 18))
        self.assertEqual(r["total_pendapatan"], 50000)              # 17 Nov (30.000) + 18 Nov (20.000)
        self.assertEqual(r["periode_sebelumnya"]["total_pendapatan"], 50000)  # pekan 9-15 Nov
        self.assertEqual(r["perubahan_persen"], 0.0)

    def test_perubahan_persen_naik_turun_dan_tanpa_pembanding(self):
        tambah(self.c, 9, 50000, "2026-11-19T10:00:00+07:00")
        r = rekap.ambil_rekap(self.c, "mingguan", date(2026, 11, 18))
        self.assertEqual(r["perubahan_persen"], 100.0)              # 100.000 vs 50.000
        r2 = rekap.ambil_rekap(self.c, "bulanan", date(2026, 11, 18))
        self.assertIsNone(r2["perubahan_persen"])                    # Oktober kosong -> tidak ada pembanding

    def test_bulan_sebelumnya_lintas_tahun(self):
        tambah(self.c, 10, 10000, "2026-12-30T10:00:00+07:00")
        tambah(self.c, 11, 20000, "2026-11-30T10:00:00+07:00")
        r = rekap.ambil_rekap(self.c, "bulanan", date(2027, 1, 5))
        self.assertEqual(r["periode_sebelumnya"]["label"], "Desember 2026")
        self.assertEqual(r["periode_sebelumnya"]["total_pendapatan"], 10000)


class UjiContohData(unittest.TestCase):
    HARI_INI = date(2026, 11, 18)

    def test_mengisi_tanpa_menyentuh_hari_ini(self):
        c = db_kosong()
        n = contoh_data.isi(c, self.HARI_INI, hari=60)
        self.assertGreater(n, 60 * 12 - 1)
        awal, akhir = c.execute("SELECT MIN(waktu_bayar), MAX(waktu_bayar) FROM tagihan").fetchone()
        self.assertTrue(awal.startswith("2026-09-19"), awal)         # 60 hari sebelum hari ini
        self.assertTrue(akhir.startswith("2026-11-17"), akhir)       # kemarin; hari ini tetap kosong
        self.assertEqual(c.execute("SELECT COUNT(*) FROM tagihan WHERE waktu_bayar LIKE '2026-11-18%'").fetchone()[0], 0)

    def test_idempoten_dan_tidak_bentrok(self):
        c = db_kosong()
        pertama = contoh_data.isi(c, self.HARI_INI)
        self.assertEqual(contoh_data.isi(c, self.HARI_INI), 0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM tagihan").fetchone()[0], pertama)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM tagihan WHERE pesanan_id >= 0").fetchone()[0], 0)

    def test_deterministik(self):
        a, b = db_kosong(), db_kosong()
        contoh_data.isi(a, self.HARI_INI)
        contoh_data.isi(b, self.HARI_INI)
        q = "SELECT SUM(jumlah), COUNT(*) FROM tagihan"
        self.assertEqual(a.execute(q).fetchone(), b.execute(q).fetchone())

    def test_cocok_dengan_rekap(self):
        c = db_kosong()
        contoh_data.isi(c, self.HARI_INI)
        r = rekap.ambil_rekap(c, "bulanan", date(2026, 11, 10))
        self.assertGreater(r["jumlah_transaksi"], 0)
        self.assertEqual(sum(x["total"] for x in r["rincian"]), r["total_pendapatan"])
        self.assertEqual(sum(x["total"] for x in r["per_metode"]), r["total_pendapatan"])
        self.assertGreater(r["periode_sebelumnya"]["total_pendapatan"], 0)
        self.assertIsNotNone(r["perubahan_persen"])


if __name__ == "__main__":
    unittest.main()
