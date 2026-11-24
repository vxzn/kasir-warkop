# Pemakaian (butuh: pip install playwright && playwright install chromium; mock_server.py harus sedang berjalan di port 8099):
#   python scripts/uji_antarmuka/uji_ui.py design/screenshots
"""Uji antarmuka di Chromium: alur lengkap, ukuran area sentuh, overflow, aksesibilitas dasar,
dan pengambilan tangkapan layar untuk portofolio."""
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8099"
OUT = pathlib.Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
hasil = []


def cek(kondisi, pesan):
    hasil.append((bool(kondisi), pesan))
    print(("ok   : " if kondisi else "GAGAL: ") + pesan)


def masuk(pg, user="kasir1", sandi="kasir123"):
    pg.fill("#login-user", user)
    pg.fill("#login-sandi", sandi)
    pg.click("#login-ok")
    pg.wait_for_selector(".item")


def buka(pg, user="kasir1", sandi="kasir123"):
    pg.goto(BASE)
    masuk(pg, user, sandi)


UKURAN = {"hp": (390, 844), "tablet": (1024, 768), "desktop": (1440, 900)}

with sync_playwright() as pw:
    br = pw.chromium.launch()

    # ---------- Alur fungsional di ukuran HP ----------
    ctx = br.new_context(viewport={"width": 390, "height": 844}, has_touch=True, locale="id-ID")
    page = ctx.new_page()
    galat = []
    # 401 pada login yang sengaja salah dicatat browser sebagai "Failed to load resource": itu perilaku yang diharapkan.
    page.on("console", lambda m: galat.append(m.text) if m.type == "error" and "401" not in m.text else None)
    page.on("pageerror", lambda e: galat.append(str(e)))
    page.goto(BASE)

    # ---------- Halaman masuk ----------
    cek(page.locator("#form-login").is_visible(), "belum masuk: hanya formulir login yang tampil")
    cek(not page.locator("#aplikasi").is_visible() and not page.locator(".bottomnav").is_visible(),
        "belum masuk: menu, pesanan, dan navigasi tersembunyi")
    cek(page.evaluate("document.activeElement.id") == "login-user", "fokus awal di kolom nama pengguna")
    page.screenshot(path=str(OUT / "hp-0-login.png"))
    page.click("#login-ok")
    cek("Isi nama pengguna" in page.inner_text("#login-galat"), "login kosong: pesan galat jelas")
    page.fill("#login-user", "kasir1")
    page.fill("#login-sandi", "salah-total")
    page.click("#login-ok")
    page.wait_for_function("document.querySelector('#login-galat').innerText.includes('salah')")
    cek(page.locator("#login-galat").get_attribute("role") == "alert", "galat login diumumkan ke pembaca layar (role=alert)")
    cek(not page.locator("#aplikasi").is_visible(), "sandi salah: tetap di halaman masuk")
    cek(page.evaluate("sessionStorage.getItem('warkop.sesi')") is None, "sandi salah: tidak ada token tersimpan")
    page.click("#lihat-sandi")
    cek(page.get_attribute("#login-sandi", "type") == "text", "tombol Tampilkan membuka isi sandi")
    page.click("#lihat-sandi")
    page.fill("#login-sandi", "kasir123")
    page.keyboard.press("Enter")
    page.wait_for_selector(".item")
    cek(page.inner_text("#akun-nama") == "Kasir Satu" or page.inner_text("#akun-nama") != "", "nama akun tampil di header")
    cek(page.inner_text("#akun-peran") == "Kasir", "peran Kasir tampil di header")
    cek(page.locator('.bottomnav [data-tab="rekap"]').is_hidden(), "kasir: tab Rekap tidak ada")
    cek(page.locator("#halaman").is_hidden(), "kasir: pindah halaman Rekap tidak ada")

    cek(page.locator(".item").count() == 9, "9 menu tampil")
    cek(page.locator(".item[disabled]").count() == 1, "menu stok habis dinonaktifkan")
    cek(page.locator(".bottomnav").is_visible(), "navigasi bawah tampil di HP")
    cek(not page.locator("#sec-keranjang").is_visible(), "HP: keranjang tersembunyi sampai dipilih")
    page.screenshot(path=str(OUT / "hp-1-menu.png"))

    # filter + cari
    page.click('[data-kat="Makanan"]')
    cek(page.locator(".item").count() == 3, "filter kategori Makanan -> 3 menu")
    page.click('[data-kat="Semua"]')
    page.fill("#cari", "kopi")
    cek(page.locator(".item").count() == 3, "pencarian 'kopi' -> 3 menu")
    page.fill("#cari", "zzz")
    cek("Tidak ada menu yang cocok" in page.inner_text("#menu"), "pencarian kosong menampilkan pesan bantu")
    page.fill("#cari", "")

    # menu hampir habis
    cek("Sisa 8" in page.inner_text("#menu"), "stok menipis ditandai 'Sisa 8'")

    # tambah item
    page.click('[data-add="1"]')
    page.click('[data-add="1"]')
    page.click('[data-add="5"]')
    cek(page.locator("#badge").inner_text() == "3", "lencana keranjang = 3 item")
    page.click('.bottomnav [data-tab="keranjang"]')
    cek(page.locator("#sec-keranjang").is_visible(), "tab Keranjang tampil")
    cek(page.inner_text("#total") == "Rp 21.000", "total keranjang Rp 21.000")
    page.screenshot(path=str(OUT / "hp-2-keranjang.png"))

    # keranjang bertahan setelah muat ulang
    page.reload()
    page.wait_for_selector(".item")
    cek(page.locator("#form-login").is_hidden(), "sesi bertahan setelah muat ulang (tidak diminta masuk lagi)")
    page.click('.bottomnav [data-tab="keranjang"]')
    cek(page.inner_text("#total") == "Rp 21.000", "keranjang bertahan setelah muat ulang")

    # buat pesanan
    page.fill("#nama", "Budi")
    page.fill("#meja", "3")
    page.click("#buat")
    page.wait_for_selector(".pesanan")
    cek(page.evaluate("document.body.dataset.tab") == "pesanan", "setelah pesan, otomatis ke tab Pesanan")
    cek("Menunggu bayar" in page.inner_text("#pesanan"), "pesanan berstatus Menunggu bayar")
    page.screenshot(path=str(OUT / "hp-3-pesanan.png"))

    # bayar tunai
    page.click("[data-bayar]")
    page.wait_for_selector("#dlg-bayar[open]")
    page.fill("#bayar", "20000")
    cek("kurang" in page.inner_text("#kembalian").lower(), "uang kurang ditandai langsung")
    page.click('[data-nominal="50000"]')
    cek("Rp 29.000" in page.inner_text("#kembalian"), "kembalian 29.000 dihitung langsung")
    page.screenshot(path=str(OUT / "hp-4-bayar.png"))
    page.click("#bayar-ok")
    page.wait_for_function("document.querySelector('#pesanan').innerText.includes('Sudah dibayar')")
    cek(True, "pembayaran berhasil -> Sudah dibayar")
    cek("Kembalian Rp 29.000" in page.inner_text("#toast"), "toast menyebut kembalian")
    cek("1 transaksi" in page.inner_text("#laporan"), "laporan harian ikut diperbarui")

    # selesai
    page.click("[data-selesai]")
    page.wait_for_function("!document.querySelector('#pesanan .pesanan')")
    cek("Tidak ada pesanan aktif" in page.inner_text("#pesanan"), "pesanan selesai hilang dari filter Aktif")
    page.click('[data-tampil="semua"]')
    cek("Selesai" in page.inner_text("#pesanan"), "filter Semua menampilkan yang selesai")

    # batal lewat dialog konfirmasi
    page.click('.bottomnav [data-tab="menu"]')
    page.click('[data-add="6"]')
    page.click('.bottomnav [data-tab="keranjang"]')
    page.click("#buat")
    page.wait_for_selector("[data-batal]")
    page.click("[data-batal]")
    page.wait_for_selector("#dlg-tanya[open]")
    cek(page.evaluate("document.activeElement.id") == "tanya-tidak", "dialog batal: fokus awal di aksi aman 'Kembali'")
    page.click("#tanya-tidak")
    cek("Menunggu bayar" in page.inner_text("#pesanan"), "memilih 'Kembali' tidak membatalkan")
    page.click("[data-batal]")
    page.click("#tanya-ya")
    page.wait_for_function("document.querySelector('#pesanan').innerText.includes('Dibatalkan')")
    cek(True, "pesanan dibatalkan setelah konfirmasi")
    page.click('.bottomnav [data-tab="menu"]')
    cek("Stok 60" in page.inner_text("#menu"), "stok kembali setelah batal (Es Jeruk 60)")

    cek(not galat, "tidak ada error di konsol: " + (galat[0] if galat else "-"))
    ctx.close()

    # ---------- Per ukuran: overflow, area sentuh, label, tangkapan layar ----------
    for nama, (w, h) in UKURAN.items():
        ctx = br.new_context(viewport={"width": w, "height": h}, has_touch=(nama != "desktop"), locale="id-ID")
        pg = ctx.new_page()
        buka(pg)
        pg.reload()
        pg.wait_for_selector(".item")
        # fokus keyboard diperiksa di halaman yang baru dibuka (Tab 1 = tautan lompat, 2 = Keluar, 3 = kolom cari)
        for _ in range(3):
            pg.keyboard.press("Tab")
        info = pg.evaluate("""() => { const e = document.activeElement; const c = getComputedStyle(e);
          return { id: e.id || e.className || e.tagName, garis: c.outlineStyle, lebar: c.outlineWidth }; }""")
        cek(info["garis"] != "none" and info["lebar"] != "0px", f"{nama}: indikator fokus terlihat pada '{info['id']}' ({info['garis']} {info['lebar']})")
        pg.click('[data-add="2"]')
        pg.click('[data-add="3"]')
        pg.click('[data-add="7"]')
        if nama == "hp":
            pg.click('.bottomnav [data-tab="keranjang"]')

        lebih = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        cek(lebih <= 0, f"{nama}: tidak ada gulir horizontal (selisih {lebih}px)")

        kecil = pg.evaluate("""() => [...document.querySelectorAll('button, input, select, a[href]')]
          .filter(e => e.offsetParent !== null || e.getClientRects().length)
          .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.height < 44 || r.width < 44); })
          .map(e => (e.id || e.className || e.tagName) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))""")
        # batas minimum area sentuh: 44 px (kontrol utama 48 px ke atas)
        cek(not kecil, f"{nama}: semua kontrol terlihat >= 44px" + (f" -> {kecil[:4]}" if kecil else ""))

        tanpa_nama = pg.evaluate("""() => [...document.querySelectorAll('button')]
          .filter(b => b.getClientRects().length)
          .filter(b => !(b.innerText || '').trim() && !b.getAttribute('aria-label'))
          .map(b => b.outerHTML.slice(0, 60))""")
        cek(not tanpa_nama, f"{nama}: setiap tombol punya nama aksesibel" + (f" -> {tanpa_nama}" if tanpa_nama else ""))

        pg.screenshot(path=str(OUT / f"{nama}-layar-penuh.png"))
        ctx.close()

    # ---------- Layar sempit: tidak ada gulir horizontal di ketiga tab ----------
    for w in (320, 360, 390):
        ctx = br.new_context(viewport={"width": w, "height": 740}, has_touch=True)
        pg = ctx.new_page()
        buka(pg, "pemilik", "pemilik123")
        lebih = []
        for tab in ("menu", "keranjang", "pesanan", "rekap"):
            pg.click(f'.bottomnav [data-tab="{tab}"]')
            lebih.append(pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"))
        cek(all(x <= 0 for x in lebih), f"lebar {w}px: tidak ada gulir horizontal di tab menu/keranjang/pesanan/rekap {lebih}")
        ctx.close()

    # ---------- Keyboard: Enter mengirim pembayaran, Esc menutup dialog tanpa membatalkan ----------
    ctx = br.new_context(viewport={"width": 1280, "height": 800})
    pg = ctx.new_page()
    buka(pg)
    pg.click('[data-add="1"]')
    pg.click("#buat")
    pg.wait_for_selector("[data-bayar]")
    pg.click("[data-bayar]")
    pg.wait_for_selector("#dlg-bayar[open]")
    pg.focus("#bayar")
    pg.keyboard.press("Enter")
    pg.wait_for_function("document.querySelector('#pesanan').innerText.includes('Sudah dibayar')", timeout=8000)
    cek(True, "keyboard: Enter di kolom uang mengonfirmasi pembayaran")
    pg.click('[data-add="2"]')
    pg.click("#buat")
    pg.wait_for_function("document.querySelectorAll('[data-batal]').length > 0")
    pg.click("[data-batal]")
    pg.wait_for_selector("#dlg-tanya[open]")
    pg.keyboard.press("Escape")
    pg.wait_for_function("!document.querySelector('#dlg-tanya').open")
    cek("Menunggu bayar" in pg.inner_text("#pesanan"), "keyboard: Esc menutup dialog batal dan pesanan tidak dibatalkan")
    ctx.close()

    # ---------- Pemilik: halaman Rekap ----------
    ctx = br.new_context(viewport={"width": 1280, "height": 800}, locale="id-ID")
    pg = ctx.new_page()
    buka(pg, "pemilik", "pemilik123")
    cek(pg.inner_text("#akun-peran") == "Pemilik", "pemilik: peran tampil di header")
    cek(pg.locator("#halaman").is_visible(), "pemilik: tombol Kasir | Rekap tampil di desktop")
    pg.click('#halaman [data-halaman="rekap"]')
    pg.wait_for_selector(".kartu-kpi")
    cek(pg.locator("#sec-rekap").is_visible() and not pg.locator("#sec-menu").is_visible(), "desktop: halaman Rekap menggantikan layar kasir")
    cek(pg.get_attribute('#rekap-periode [data-periode="mingguan"]', "aria-pressed") == "true", "periode awal: Mingguan")
    cek("-" in pg.inner_text("#rekap-label"), "label rentang pekan tampil: " + pg.inner_text("#rekap-label"))
    cek(pg.locator(".kartu-kpi").count() == 3, "tiga kartu ringkasan (total, transaksi, rata-rata)")
    cek(pg.locator(".grafik .bar").count() == 7, "grafik mingguan: 7 batang")
    cek("Grafik batang" in (pg.get_attribute(".grafik", "aria-label") or ""), "grafik punya teks alternatif")
    pg.click(".tabel-rincian summary")
    cek(pg.locator(".tabel-rincian table tbody tr").count() >= 1, "tabel alternatif bisa dibuka")
    pg.screenshot(path=str(OUT / "desktop-rekap-mingguan.png"), full_page=True)

    pg.click('[data-periode="bulanan"]')
    pg.wait_for_function("document.querySelectorAll('.grafik .bar').length >= 28")
    cek(True, "periode Bulanan: batang per tanggal (>= 28)")
    pg.screenshot(path=str(OUT / "desktop-rekap-bulanan.png"), full_page=True)
    pg.click('[data-periode="harian"]')
    pg.wait_for_function("document.querySelectorAll('.grafik .bar').length === 24")
    cek(True, "periode Harian: 24 batang per jam")

    pg.click("#rekap-prev")
    pg.wait_for_function("document.querySelector('#rekap-label').innerText.includes(',')")
    kemarin = pg.input_value("#rekap-tgl")
    cek(kemarin < pg.evaluate("hariIni()"), "tombol sebelumnya memundurkan tanggal: " + kemarin)
    cek(pg.locator("#rekap-next").is_enabled(), "periode lampau: tombol berikutnya aktif")
    pg.click("#rekap-ini")
    pg.wait_for_function("document.querySelector('#rekap-isi').getAttribute('aria-busy') === 'false'")
    cek(pg.locator("#rekap-next").is_disabled(), "hari ini: tidak bisa maju ke masa depan")

    pg.click('[data-periode="mingguan"]')
    pg.click("#rekap-prev")
    pg.wait_for_selector(".banding")
    cek("dibanding pekan lalu" in pg.inner_text(".banding"), "perbandingan dengan pekan lalu tampil")
    cek(pg.locator(".metode-daftar li").count() >= 1, "rincian per metode pembayaran tampil")

    # rekap bertambah setelah ada pembayaran hari ini
    pg.click('[data-periode="harian"]')
    pg.click("#rekap-ini")
    pg.wait_for_function("document.querySelector('#rekap-isi').getAttribute('aria-busy') === 'false' && document.querySelector('#rekap-isi .kpi')")
    sebelum = pg.evaluate("""() => { const k = document.querySelector('#rekap-isi .kartu-kpi:nth-child(2) strong');
                                      return k ? Number(k.textContent) : 0; }""")
    pg.click('#halaman [data-halaman="kasir"]')
    pg.click('[data-add="1"]')
    pg.click("#buat")
    pg.wait_for_selector("[data-bayar]")
    pg.click("[data-bayar]")
    pg.click("#bayar-ok")
    pg.wait_for_function("document.querySelector('#pesanan').innerText.includes('Sudah dibayar')")
    pg.click('#halaman [data-halaman="rekap"]')
    pg.click('[data-periode="harian"]')
    pg.click("#rekap-ini")
    pg.wait_for_function("document.querySelector('#rekap-isi').getAttribute('aria-busy') === 'false' && document.querySelector('#rekap-isi .kpi')")
    sesudah = int(pg.inner_text("#rekap-isi .kartu-kpi:nth-child(2) strong"))
    cek(sesudah == sebelum + 1, f"rekap harian bertambah satu transaksi setelah pembayaran ({sebelum} -> {sesudah})")

    # rekap kosong: pilih tanggal di masa lalu jauh
    pg.fill("#rekap-tgl", "2020-01-01")
    pg.wait_for_function("document.querySelector('#rekap-isi').innerText.includes('Belum ada pembayaran')")
    cek(True, "periode tanpa penjualan: pesan kosong yang jelas")
    ctx.close()

    # HP (pemilik): tab Rekap di navigasi bawah
    ctx = br.new_context(viewport={"width": 390, "height": 844}, has_touch=True, locale="id-ID")
    pg = ctx.new_page()
    buka(pg, "pemilik", "pemilik123")
    cek(pg.locator('.bottomnav [data-tab="rekap"]').is_visible(), "HP pemilik: tab Rekap tampil")
    cek(pg.locator("#halaman").is_hidden(), "HP: pindah halaman memakai navigasi bawah saja")
    pg.click('.bottomnav [data-tab="rekap"]')
    pg.wait_for_selector(".kartu-kpi")
    pg.screenshot(path=str(OUT / "hp-5-rekap.png"), full_page=True)
    cek(pg.get_attribute('.bottomnav [data-tab="rekap"]', "aria-current") == "page", "tab Rekap ditandai aktif")
    ctx.close()

    # ---------- Keamanan di sisi antarmuka ----------
    ctx = br.new_context(viewport={"width": 1280, "height": 800})
    pg = ctx.new_page()
    buka(pg)   # kasir
    kode = pg.evaluate("""async () => (await fetch('/api/tagihan/rekap?periode=harian',
        { headers: { Authorization: 'Bearer ' + JSON.parse(sessionStorage.getItem('warkop.sesi')).token } })).status""")
    cek(kode == 403, f"kasir memanggil API rekap langsung -> {kode} (diharapkan 403)")
    kode = pg.evaluate("async () => (await fetch('/api/pesanan')).status")
    cek(kode == 401, f"tanpa token -> {kode} (diharapkan 401)")
    pg.evaluate("""() => { const s = JSON.parse(sessionStorage.getItem('warkop.sesi')); s.token = s.token.slice(0, -4) + 'AAAA';
                           sessionStorage.setItem('warkop.sesi', JSON.stringify(s)); }""")
    pg.reload()
    pg.wait_for_selector("#login-halaman:not([hidden])")
    cek("Sesi berakhir" in pg.inner_text("#login-info"), "token rusak: kembali ke login dengan pesan 'Sesi berakhir'")
    cek(pg.evaluate("sessionStorage.getItem('warkop.sesi')") is None, "token rusak dihapus dari penyimpanan")

    masuk(pg)
    pg.click("#keluar")
    pg.wait_for_selector("#dlg-tanya[open]")
    pg.click("#tanya-ya")
    pg.wait_for_selector("#login-halaman:not([hidden])")
    cek(pg.locator("#aplikasi").is_hidden() and pg.evaluate("sessionStorage.getItem('warkop.sesi')") is None,
        "keluar: data disembunyikan dan token dihapus")
    cek(pg.evaluate("document.activeElement.id") == "login-user", "keluar: fokus kembali ke kolom nama pengguna")

    for _ in range(5):
        pg.fill("#login-user", "penyusup")
        pg.fill("#login-sandi", "tebak-tebakan")
        pg.click("#login-ok")
        pg.wait_for_function("!document.querySelector('#login-ok').disabled")
    pg.fill("#login-user", "penyusup")
    pg.fill("#login-sandi", "tebak-tebakan")
    pg.click("#login-ok")
    pg.wait_for_function("document.querySelector('#login-galat').innerText.includes('Terlalu banyak')")
    cek(True, "5 kali gagal: percobaan berikutnya diblokir sementara (429)")
    ctx.close()

    br.close()

gagal = [m for ok, m in hasil if not ok]
print(f"\n{len(hasil) - len(gagal)}/{len(hasil)} pemeriksaan lolos")
sys.exit(1 if gagal else 0)
