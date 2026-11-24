"""Uji hash kata sandi, akun pengguna, dan pembatas percobaan masuk."""
import sqlite3
import unittest

import _jalur  # noqa: F401
import kata_sandi
import pengguna
from pembatas import PembatasLogin

WAKTU = "2026-11-18T10:00:00+07:00"


class UjiKataSandi(unittest.TestCase):
    def test_cocok_dan_tidak(self):
        h = kata_sandi.hash_sandi("rahasia123", iterasi=1000)
        self.assertTrue(kata_sandi.cocok("rahasia123", h))
        self.assertFalse(kata_sandi.cocok("Rahasia123", h))
        self.assertFalse(kata_sandi.cocok("", h))

    def test_sandi_asli_tidak_tersimpan_dan_garam_berbeda(self):
        a = kata_sandi.hash_sandi("sama", iterasi=1000)
        b = kata_sandi.hash_sandi("sama", iterasi=1000)
        self.assertNotIn("sama", a)
        self.assertNotEqual(a, b)

    def test_format_rusak_ditolak_tanpa_error(self):
        for rusak in ["", "abc", "a$b$c$d", "pbkdf2_sha256$x$00$00", "lain$1$00$00", "pbkdf2_sha256$0$00$00"]:
            with self.subTest(rusak=rusak):
                self.assertFalse(kata_sandi.cocok("x", rusak))


class UjiPengguna(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.addCleanup(self.conn.close)
        pengguna.init(self.conn)

    def test_isi_awal_sekali_saja(self):
        self.assertEqual(pengguna.isi_awal(self.conn, "pemilik123", "kasir123", WAKTU), 2)
        self.assertEqual(pengguna.isi_awal(self.conn, "lain123", "lain123", WAKTU), 0)
        self.assertEqual([u["role"] for u in pengguna.daftar(self.conn)], ["pemilik", "kasir"])

    def test_login_berhasil_dan_gagal(self):
        pengguna.isi_awal(self.conn, "pemilik123", "kasir123", WAKTU)
        u = pengguna.autentikasi(self.conn, "kasir1", "kasir123")
        self.assertEqual((u["username"], u["role"]), ("kasir1", "kasir"))
        self.assertNotIn("sandi", u)
        self.assertIsNone(pengguna.autentikasi(self.conn, "kasir1", "salah"))
        self.assertIsNone(pengguna.autentikasi(self.conn, "tidak-ada", "kasir123"))

    def test_nama_pengguna_tidak_peka_huruf_besar(self):
        pengguna.isi_awal(self.conn, "pemilik123", "kasir123", WAKTU)
        self.assertIsNotNone(pengguna.autentikasi(self.conn, "  KASIR1 ", "kasir123"))

    def test_sandi_disimpan_dalam_bentuk_hash(self):
        pengguna.isi_awal(self.conn, "pemilik123", "kasir123", WAKTU)
        tersimpan = self.conn.execute("SELECT sandi FROM pengguna WHERE username='kasir1'").fetchone()[0]
        self.assertTrue(tersimpan.startswith("pbkdf2_sha256$"))
        self.assertNotIn("kasir123", tersimpan)

    def test_validasi_pembuatan_akun(self):
        kasus = [
            ("ab", "Nama", "kasir", "sandi123", 422),          # nama pengguna terlalu pendek
            ("Ada Spasi", "Nama", "kasir", "sandi123", 422),
            ("budi", "  ", "kasir", "sandi123", 422),          # nama kosong
            ("budi", "Budi", "admin", "sandi123", 422),        # peran tidak dikenal
            ("budi", "Budi", "kasir", "12345", 422),           # sandi terlalu pendek
        ]
        for u, n, r, s, kode in kasus:
            with self.subTest(u=u, r=r, s=s):
                with self.assertRaises(pengguna.PenggunaError) as c:
                    pengguna.buat(self.conn, u, n, r, s, WAKTU)
                self.assertEqual(c.exception.status, kode)

    def test_nama_pengguna_ganda_409(self):
        pengguna.buat(self.conn, "budi", "Budi", "kasir", "sandi123", WAKTU)
        with self.assertRaises(pengguna.PenggunaError) as c:
            pengguna.buat(self.conn, "BUDI", "Budi Dua", "kasir", "sandi123", WAKTU)
        self.assertEqual(c.exception.status, 409)

    def test_akun_nonaktif_tidak_bisa_masuk(self):
        pengguna.buat(self.conn, "budi", "Budi", "kasir", "sandi123", WAKTU)
        self.conn.execute("UPDATE pengguna SET aktif = 0 WHERE username = 'budi'")
        self.assertIsNone(pengguna.autentikasi(self.conn, "budi", "sandi123"))

    def test_ganti_sandi(self):
        pengguna.buat(self.conn, "budi", "Budi", "kasir", "sandi123", WAKTU)
        with self.assertRaises(pengguna.PenggunaError) as c:
            pengguna.ganti_sandi(self.conn, "budi", "salah", "baru12345")
        self.assertEqual(c.exception.status, 403)
        with self.assertRaises(pengguna.PenggunaError):
            pengguna.ganti_sandi(self.conn, "budi", "sandi123", "abc12")   # 5 karakter
        pengguna.ganti_sandi(self.conn, "budi", "sandi123", "baru12345")
        self.assertIsNone(pengguna.autentikasi(self.conn, "budi", "sandi123"))
        self.assertIsNotNone(pengguna.autentikasi(self.conn, "budi", "baru12345"))


class JamPalsu:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class UjiPembatas(unittest.TestCase):
    def setUp(self):
        self.jam = JamPalsu()
        self.p = PembatasLogin(maks_gagal=3, jendela=300, kunci=60, jam=self.jam)

    def test_terkunci_setelah_batas(self):
        for _ in range(2):
            self.p.gagal("budi|1.1.1.1")
        self.assertEqual(self.p.sisa_kunci("budi|1.1.1.1"), 0)
        self.p.gagal("budi|1.1.1.1")
        self.assertEqual(self.p.sisa_kunci("budi|1.1.1.1"), 60)

    def test_kunci_berakhir(self):
        for _ in range(3):
            self.p.gagal("k")
        self.jam.t += 30
        self.assertEqual(self.p.sisa_kunci("k"), 30)
        self.jam.t += 31
        self.assertEqual(self.p.sisa_kunci("k"), 0)

    def test_kunci_lain_tidak_terpengaruh(self):
        for _ in range(3):
            self.p.gagal("budi|1.1.1.1")
        self.assertEqual(self.p.sisa_kunci("siti|1.1.1.1"), 0)
        self.assertEqual(self.p.sisa_kunci("budi|2.2.2.2"), 0)

    def test_berhasil_menghapus_catatan(self):
        self.p.gagal("k")
        self.p.gagal("k")
        self.p.berhasil("k")
        self.p.gagal("k")
        self.p.gagal("k")
        self.assertEqual(self.p.sisa_kunci("k"), 0)    # hitungan mulai dari nol lagi

    def test_kegagalan_lama_kedaluwarsa(self):
        self.p.gagal("k")
        self.p.gagal("k")
        self.jam.t += 301                              # di luar jendela 300 detik
        self.p.gagal("k")
        self.assertEqual(self.p.sisa_kunci("k"), 0)

    def test_memori_dibersihkan(self):
        for i in range(50):
            self.p.gagal(f"k{i}")
        self.jam.t += 1000
        self.p.gagal("baru")
        self.assertLessEqual(len(self.p._gagal), 1)


if __name__ == "__main__":
    unittest.main()
