"""Pembatas percobaan masuk: melawan tebak kata sandi (brute force).

Setelah `maks_gagal` kegagalan dalam `jendela` detik untuk satu kunci (nama pengguna + alamat IP),
kunci itu dikunci selama `kunci` detik. Disimpan di memori (cukup untuk satu proses; untuk
beberapa replika gunakan Redis).
"""
import math
import time


class PembatasLogin:
    def __init__(self, maks_gagal=5, jendela=300, kunci=60, jam=time.monotonic):
        self.maks_gagal = maks_gagal
        self.jendela = jendela
        self.kunci = kunci
        self.jam = jam
        self._gagal = {}        # kunci -> daftar waktu kegagalan
        self._terkunci = {}     # kunci -> waktu kunci berakhir

    def sisa_kunci(self, kunci: str) -> int:
        """Detik tersisa bila terkunci, selain itu 0."""
        akhir = self._terkunci.get(kunci)
        if akhir is None:
            return 0
        sisa = akhir - self.jam()
        if sisa <= 0:
            del self._terkunci[kunci]
            return 0
        return math.ceil(sisa)

    def gagal(self, kunci: str):
        sekarang = self.jam()
        riwayat = [t for t in self._gagal.get(kunci, []) if sekarang - t < self.jendela]
        riwayat.append(sekarang)
        if len(riwayat) >= self.maks_gagal:
            self._terkunci[kunci] = sekarang + self.kunci
            riwayat = []
        self._gagal[kunci] = riwayat
        self._bersihkan(sekarang)

    def berhasil(self, kunci: str):
        self._gagal.pop(kunci, None)
        self._terkunci.pop(kunci, None)

    def _bersihkan(self, sekarang: float):
        """Buang catatan lama supaya memori tidak membengkak."""
        for k in [k for k, v in self._gagal.items() if not v or sekarang - v[-1] >= self.jendela]:
            del self._gagal[k]
        for k in [k for k, akhir in self._terkunci.items() if akhir <= sekarang]:
            del self._terkunci[k]
