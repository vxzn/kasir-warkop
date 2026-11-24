"""Uji modul keamanan bersama (token JWT dan keputusan akses). Tanpa FastAPI, tanpa jaringan."""
import base64
import json
import unittest

import _jalur  # noqa: F401
import auth

RAHASIA = "rahasia-uji-minimal-16-karakter"
KUNCI = "kunci-layanan-uji-16-karakter"
T0 = 1_800_000_000


def klaim(role="kasir", sub="rina"):
    return {"sub": sub, "nama": "Rina", "role": role}


def ubah_badan(token, **perubahan):
    """Ubah isi token tanpa menghitung ulang tanda tangan (simulasi pemalsuan)."""
    kepala, badan, tanda = token.split(".")
    isi = json.loads(base64.urlsafe_b64decode(badan + "=" * (-len(badan) % 4)))
    isi.update(perubahan)
    baru = base64.urlsafe_b64encode(json.dumps(isi).encode()).rstrip(b"=").decode()
    return f"{kepala}.{baru}.{tanda}"


class UjiToken(unittest.TestCase):
    def test_bolak_balik(self):
        t = auth.buat_token(klaim(), RAHASIA, 3600, sekarang=T0)
        isi = auth.baca_token(t, RAHASIA, sekarang=T0 + 10)
        self.assertEqual((isi["sub"], isi["role"], isi["nama"]), ("rina", "kasir", "Rina"))
        self.assertEqual(isi["exp"], T0 + 3600)

    def test_kedaluwarsa(self):
        t = auth.buat_token(klaim(), RAHASIA, 60, sekarang=T0)
        with self.assertRaisesRegex(auth.TokenError, "berakhir"):
            auth.baca_token(t, RAHASIA, sekarang=T0 + 60)
        auth.baca_token(t, RAHASIA, sekarang=T0 + 59)   # satu detik sebelum habis masih sah

    def test_rahasia_salah(self):
        t = auth.buat_token(klaim(), RAHASIA, 3600, sekarang=T0)
        with self.assertRaises(auth.TokenError):
            auth.baca_token(t, "rahasia-lain-yang-panjang", sekarang=T0)

    def test_isi_dipalsukan(self):
        t = auth.buat_token(klaim("kasir"), RAHASIA, 3600, sekarang=T0)
        palsu = ubah_badan(t, role="pemilik")          # kasir mencoba menjadi pemilik
        with self.assertRaises(auth.TokenError):
            auth.baca_token(palsu, RAHASIA, sekarang=T0)

    def test_algoritma_none_ditolak(self):
        kepala = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
        badan = base64.urlsafe_b64encode(json.dumps(
            {"sub": "x", "role": "pemilik", "iss": auth.ISSUER, "exp": T0 + 99}).encode()).rstrip(b"=").decode()
        with self.assertRaises(auth.TokenError):
            auth.baca_token(f"{kepala}.{badan}.", RAHASIA, sekarang=T0)

    def test_sampah_ditolak(self):
        for sampah in ["", "abc", "a.b", "a.b.c.d", "....", "###.###.###", "é.é.é"]:
            with self.subTest(sampah=sampah):
                with self.assertRaises(auth.TokenError):
                    auth.baca_token(sampah, RAHASIA, sekarang=T0)

    def test_peran_tidak_dikenal_ditolak(self):
        t = auth.buat_token({"sub": "x", "role": "admin"}, RAHASIA, 60, sekarang=T0)
        with self.assertRaises(auth.TokenError):
            auth.baca_token(t, RAHASIA, sekarang=T0)

    def test_penerbit_salah_ditolak(self):
        t = auth.buat_token(klaim(), RAHASIA, 60, sekarang=T0)
        with self.assertRaises(auth.TokenError):
            auth.baca_token(ubah_badan(t, iss="lain"), RAHASIA, sekarang=T0)


class UjiKonfigurasi(unittest.TestCase):
    def tearDown(self):
        auth.muat_konfigurasi(RAHASIA, KUNCI)

    def test_rahasia_pendek_ditolak(self):
        with self.assertRaisesRegex(RuntimeError, "JWT_SECRET"):
            auth.muat_konfigurasi("pendek", KUNCI)
        with self.assertRaisesRegex(RuntimeError, "SERVICE_KEY"):
            auth.muat_konfigurasi(RAHASIA, "pendek")

    def test_layanan_auth_tidak_butuh_kunci_layanan(self):
        auth.muat_konfigurasi(RAHASIA, "", butuh_service_key=False)
        with self.assertRaises(RuntimeError):
            auth.header_layanan()

    def test_header_layanan(self):
        auth.muat_konfigurasi(RAHASIA, KUNCI)
        self.assertEqual(auth.header_layanan(), {"X-Service-Key": KUNCI})


class UjiAkses(unittest.TestCase):
    def setUp(self):
        auth.muat_konfigurasi(RAHASIA, KUNCI)
        self.kasir = "Bearer " + auth.buat_token(klaim("kasir"), RAHASIA, 3600)
        self.pemilik = "Bearer " + auth.buat_token(klaim("pemilik", "pak.anton"), RAHASIA, 3600)

    def status(self, *a, **k):
        try:
            auth.periksa_akses(*a, **k)
            return 200
        except auth.AksesDitolak as e:
            return e.status

    def test_tanpa_token_401(self):
        self.assertEqual(self.status(None, None, ("kasir", "pemilik")), 401)
        self.assertEqual(self.status("", None, ("kasir",)), 401)

    def test_skema_salah_401(self):
        self.assertEqual(self.status("Basic abc", None, ("kasir",)), 401)
        self.assertEqual(self.status("Bearer", None, ("kasir",)), 401)
        self.assertEqual(self.status("Bearer sampah", None, ("kasir",)), 401)

    def test_peran_diizinkan_200(self):
        self.assertEqual(self.status(self.kasir, None, ("kasir", "pemilik")), 200)
        self.assertEqual(self.status(self.pemilik, None, ("pemilik",)), 200)

    def test_kasir_ke_endpoint_pemilik_403(self):
        self.assertEqual(self.status(self.kasir, None, ("pemilik",)), 403)

    def test_endpoint_khusus_layanan_menolak_pengguna(self):
        # peran_boleh kosong + layanan_boleh=True: hanya pemanggil antar-layanan
        self.assertEqual(self.status(self.kasir, None, (), True), 403)
        self.assertEqual(self.status(self.pemilik, None, (), True), 403)
        self.assertEqual(self.status(None, None, (), True), 401)

    def test_kunci_layanan_benar_diterima_bila_diizinkan(self):
        k = auth.periksa_akses(None, KUNCI, ("pemilik",), True)
        self.assertEqual(k["role"], "layanan")

    def test_kunci_layanan_ditolak_di_endpoint_pengguna(self):
        self.assertEqual(self.status(None, KUNCI, ("kasir",), False), 401)

    def test_kunci_layanan_salah_ditolak(self):
        self.assertEqual(self.status(None, "kunci-salah-tapi-panjang", ("kasir",), True), 401)

    def test_kunci_salah_tapi_token_sah_tetap_lolos_sebagai_pengguna(self):
        self.assertEqual(self.status(self.kasir, "kunci-salah", ("kasir",), True), 200)

    def test_token_kedaluwarsa_401(self):
        lama = "Bearer " + auth.buat_token(klaim(), RAHASIA, 60, sekarang=T0)
        self.assertEqual(self.status(lama, None, ("kasir",), sekarang=T0 + 61), 401)

    def test_peran_tidak_dikenal_pada_dekorator_ditolak(self):
        with self.assertRaises(ValueError):
            auth.dibutuhkan("admin")


if __name__ == "__main__":
    unittest.main()
