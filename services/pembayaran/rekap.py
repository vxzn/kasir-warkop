"""Rekap penjualan harian, mingguan, dan bulanan dari tabel `tagihan` (hanya yang LUNAS).

Hanya fungsi murni dan satu query SQLite, tanpa FastAPI, supaya mudah diuji.

Definisi periode (zona waktu WIB, sama dengan waktu yang disimpan di kolom waktu_bayar):
  harian   = satu tanggal
  mingguan = Senin sampai Minggu pada pekan yang memuat tanggal acuan
  bulanan  = tanggal 1 sampai akhir bulan pada bulan yang memuat tanggal acuan
"""
from datetime import date, timedelta

PERIODE = ("harian", "mingguan", "bulanan")
METODE = ("TUNAI", "QRIS", "TRANSFER")

HARI = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
HARI_PANJANG = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
BULAN_PANJANG = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
                 "Agustus", "September", "Oktober", "November", "Desember"]


def rentang(periode: str, acuan: date):
    """Kembalikan (dari, sampai) dengan `sampai` eksklusif."""
    if periode == "harian":
        return acuan, acuan + timedelta(days=1)
    if periode == "mingguan":
        awal = acuan - timedelta(days=acuan.weekday())
        return awal, awal + timedelta(days=7)
    if periode == "bulanan":
        awal = acuan.replace(day=1)
        akhir = date(awal.year + (1 if awal.month == 12 else 0), awal.month % 12 + 1, 1)
        return awal, akhir
    raise ValueError(f"Periode harus salah satu dari {PERIODE}")


def _tgl(d: date) -> str:
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


def label_rentang(periode: str, dari: date, sampai: date) -> str:
    terakhir = sampai - timedelta(days=1)
    if periode == "harian":
        return f"{HARI_PANJANG[dari.weekday()]}, {_tgl(dari)}"
    if periode == "mingguan":
        return f"{_tgl(dari)} - {_tgl(terakhir)}"
    return f"{BULAN_PANJANG[dari.month - 1]} {dari.year}"


def _kerangka(periode: str, dari: date, sampai: date):
    """Daftar baris rincian kosong: 24 jam (harian) atau satu baris per tanggal."""
    if periode == "harian":
        return [{"kunci": f"{j:02d}", "label": f"{j:02d}", "keterangan": f"Pukul {j:02d}.00-{j:02d}.59"}
                for j in range(24)]
    baris = []
    d = dari
    while d < sampai:
        if periode == "mingguan":
            label = f"{HARI[d.weekday()]} {d.day}"
        else:
            label = str(d.day)
        baris.append({
            "kunci": d.isoformat(),
            "label": label,
            "keterangan": f"{HARI_PANJANG[d.weekday()]}, {_tgl(d)}",
        })
        d += timedelta(days=1)
    return baris


def susun_rekap(baris, periode: str, acuan: date) -> dict:
    """Susun rekap dari baris (waktu_bayar ISO, jumlah, metode).

    Baris di luar rentang diabaikan. waktu_bayar berformat 'YYYY-MM-DDTHH:MM:SS+07:00'.
    """
    dari, sampai = rentang(periode, acuan)
    rincian = _kerangka(periode, dari, sampai)
    indeks = {r["kunci"]: r for r in rincian}
    for r in rincian:
        r["jumlah_transaksi"] = 0
        r["total"] = 0

    awal, akhir = dari.isoformat(), sampai.isoformat()
    metode = {m: {"metode": m, "jumlah_transaksi": 0, "total": 0} for m in METODE}
    total = jumlah_tx = 0
    for waktu, nilai, cara in baris:
        if not (awal <= waktu[:10] < akhir):
            continue
        kunci = waktu[11:13] if periode == "harian" else waktu[:10]
        r = indeks.get(kunci)
        if r is None:
            continue
        r["jumlah_transaksi"] += 1
        r["total"] += nilai
        total += nilai
        jumlah_tx += 1
        m = metode.setdefault(cara or "LAINNYA", {"metode": cara or "LAINNYA", "jumlah_transaksi": 0, "total": 0})
        m["jumlah_transaksi"] += 1
        m["total"] += nilai

    puncak = max(rincian, key=lambda r: r["total"]) if rincian else None
    if puncak is not None and puncak["total"] <= 0:
        puncak = None
    return {
        "periode": periode,
        "tanggal_acuan": acuan.isoformat(),
        "dari": dari.isoformat(),
        "sampai": (sampai - timedelta(days=1)).isoformat(),
        "label": label_rentang(periode, dari, sampai),
        "total_pendapatan": total,
        "jumlah_transaksi": jumlah_tx,
        "rata_rata_transaksi": round(total / jumlah_tx) if jumlah_tx else 0,
        "per_metode": list(metode.values()),
        "rincian": rincian,
        "puncak": ({"kunci": puncak["kunci"], "keterangan": puncak["keterangan"], "total": puncak["total"]}
                   if puncak else None),
    }


def _ambil_baris(conn, dari: date, sampai: date):
    # waktu_bayar disimpan sebagai teks ISO, sehingga perbandingan teks sama dengan urutan waktu.
    return conn.execute(
        "SELECT waktu_bayar, jumlah, metode FROM tagihan "
        "WHERE status = 'LUNAS' AND waktu_bayar >= ? AND waktu_bayar < ?",
        (dari.isoformat(), sampai.isoformat()),
    ).fetchall()


def ambil_rekap(conn, periode: str, acuan: date) -> dict:
    """Rekap periode yang diminta, lengkap dengan perbandingan terhadap periode sebelumnya."""
    dari, sampai = rentang(periode, acuan)
    hasil = susun_rekap(_ambil_baris(conn, dari, sampai), periode, acuan)

    dari_lalu, sampai_lalu = rentang(periode, dari - timedelta(days=1))
    lalu = susun_rekap(_ambil_baris(conn, dari_lalu, sampai_lalu), periode, dari_lalu)
    hasil["periode_sebelumnya"] = {
        "label": lalu["label"],
        "total_pendapatan": lalu["total_pendapatan"],
        "jumlah_transaksi": lalu["jumlah_transaksi"],
    }
    hasil["perubahan_persen"] = (
        round((hasil["total_pendapatan"] - lalu["total_pendapatan"]) / lalu["total_pendapatan"] * 100, 1)
        if lalu["total_pendapatan"] > 0 else None
    )
    return hasil
