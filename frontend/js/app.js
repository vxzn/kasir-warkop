'use strict';
/* Kasir Warkop - prototype frontend.
   Tanpa framework: HTML + CSS + JavaScript biasa, supaya mudah dibaca dan dijalankan di platform apa pun. */

const $ = (s, r = document) => r.querySelector(s);
const rp = n => 'Rp ' + Number(n).toLocaleString('id-ID');
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const STATUS = {
  MENUNGGU_PEMBAYARAN: { label: 'Menunggu bayar', ikon: '○' },
  DIBAYAR: { label: 'Sudah dibayar', ikon: '●' },
  SELESAI: { label: 'Selesai', ikon: '✔' },
  BATAL: { label: 'Dibatalkan', ikon: '✕' },
};
const STOK_MENIPIS = 10;
const KUNCI_KERANJANG = 'warkop.keranjang';
const KUNCI_SESI = 'warkop.sesi';      // sessionStorage: hilang saat tab/browser ditutup

const state = {
  menu: [],
  cart: {},            // menu_id -> jumlah
  kategori: 'Semua',
  q: '',
  tampil: 'aktif',     // 'aktif' | 'semua'
  pesanan: [],
  bayar: null,         // { id, total }
  sibuk: false,
  sesi: null,          // { token, exp (ms), user: { username, nama, role } }
  tabKasir: 'menu',    // tab terakhir di sisi kasir (untuk kembali dari Rekap)
  rekap: { periode: 'mingguan', acuan: null, no: 0 },
  timer: null,
};

/* ---------- Sesi masuk (token JWT dari layanan auth) ---------- */
function simpanSesi() {
  try { sessionStorage.setItem(KUNCI_SESI, JSON.stringify(state.sesi)); } catch (_) { /* abaikan */ }
}
function muatSesi() {
  try {
    const d = JSON.parse(sessionStorage.getItem(KUNCI_SESI) || 'null');
    if (d && d.token && d.user && d.exp > Date.now()) state.sesi = d;
  } catch (_) { state.sesi = null; }
}
function hapusSesi() {
  state.sesi = null;
  try { sessionStorage.removeItem(KUNCI_SESI); } catch (_) { /* abaikan */ }
}
const peran = () => (state.sesi ? state.sesi.user.role : '');

/* ---------- Penyimpanan lokal (keranjang tidak hilang saat halaman dimuat ulang) ---------- */
function simpanKeranjang() {
  try { localStorage.setItem(KUNCI_KERANJANG, JSON.stringify(state.cart)); } catch (_) { /* abaikan */ }
}
function muatKeranjang() {
  try {
    const d = JSON.parse(localStorage.getItem(KUNCI_KERANJANG) || '{}');
    if (d && typeof d === 'object') state.cart = d;
  } catch (_) { state.cart = {}; }
}

/* ---------- API ---------- */
async function api(path, opts = {}) {
  const { tanpaToken, ...fetchOpts } = opts;
  const headers = { 'Content-Type': 'application/json' };
  if (state.sesi && !tanpaToken) headers.Authorization = 'Bearer ' + state.sesi.token;
  let r;
  try {
    r = await fetch('/api' + path, { ...fetchOpts, headers });
  } catch (_) {
    throw new Error('Tidak dapat terhubung ke server. Periksa koneksi lalu coba lagi.');
  }
  const data = await r.json().catch(() => ({}));
  if (r.status === 401 && !tanpaToken) {
    // Token ditolak atau kedaluwarsa: kembali ke halaman masuk.
    keluar('Sesi berakhir. Silakan masuk lagi.');
    throw new Error('Sesi berakhir. Silakan masuk lagi.');
  }
  if (!r.ok) {
    const d = data.detail;
    throw new Error(Array.isArray(d) ? d.map(x => x.msg).join(', ') : (d || 'Terjadi kesalahan (' + r.status + ')'));
  }
  return data;
}

/* ---------- Umpan balik ---------- */
let timerToast;
function toast(pesan, salah = false) {
  const t = $('#toast');
  t.textContent = pesan;
  t.className = 'toast show' + (salah ? ' salah' : '');
  clearTimeout(timerToast);
  timerToast = setTimeout(() => { t.className = 'toast'; }, 4000);
}

/* Dialog konfirmasi yang bisa dioperasikan dengan keyboard dan pembaca layar */
function tanya(judul, isi, teksYa) {
  return new Promise(resolve => {
    const d = $('#dlg-tanya');
    $('#tanya-judul').textContent = judul;
    $('#tanya-isi').textContent = isi;
    $('#tanya-ya').textContent = teksYa;
    const selesai = ya => { d.close(); $('#tanya-ya').onclick = $('#tanya-tidak').onclick = null; resolve(ya); };
    $('#tanya-ya').onclick = () => selesai(true);
    $('#tanya-tidak').onclick = () => selesai(false);
    d.oncancel = () => resolve(false);
    d.showModal();
    $('#tanya-tidak').focus();   // fokus awal pada aksi yang aman
  });
}

/* ---------- Menu ---------- */
function daftarKategori() {
  return ['Semua', ...new Set(state.menu.map(m => m.kategori))];
}

function renderKategori() {
  $('#kategori').innerHTML = daftarKategori().map(k =>
    `<button type="button" class="chip" data-kat="${esc(k)}" aria-pressed="${k === state.kategori}">${esc(k)}</button>`
  ).join('');
}

function renderMenu() {
  const q = state.q.trim().toLowerCase();
  const tampil = state.menu.filter(m =>
    (state.kategori === 'Semua' || m.kategori === state.kategori) &&
    (!q || m.nama.toLowerCase().includes(q))
  );
  if (!state.menu.length) {
    $('#menu').innerHTML = '<p class="kosong">Belum ada menu.</p>';
    return;
  }
  if (!tampil.length) {
    $('#menu').innerHTML = '<p class="kosong" style="grid-column:1/-1">Tidak ada menu yang cocok. ' +
      '<button type="button" class="btn kecil teks" data-reset>Tampilkan semua</button></p>';
    return;
  }
  $('#menu').innerHTML = tampil.map(m => {
    const dalam = state.cart[m.id] || 0;
    const habis = m.stok <= 0;
    const menipis = !habis && m.stok <= STOK_MENIPIS;
    const stokTeks = habis ? 'Habis' : (menipis ? 'Sisa ' + m.stok : 'Stok ' + m.stok);
    const label = `Tambah ${m.nama}, ${rp(m.harga)}, ${stokTeks}` + (dalam ? `, ${dalam} di keranjang` : '');
    return `<button type="button" class="item" data-add="${m.id}" ${habis ? 'disabled' : ''} aria-label="${esc(label)}">
      <span class="kat">${esc(m.kategori)}</span>
      <span class="nama">${esc(m.nama)}</span>
      <span class="harga">${rp(m.harga)}</span>
      <span class="stok${menipis ? ' menipis' : ''}">${stokTeks}</span>
      ${dalam ? `<span class="dalam" aria-hidden="true">${dalam}</span>` : ''}
    </button>`;
  }).join('');
}

async function muatMenu() {
  state.menu = await api('/menu');
  // Buang item keranjang yang sudah tidak ada atau melebihi stok terbaru.
  for (const id of Object.keys(state.cart)) {
    const m = state.menu.find(x => x.id === Number(id));
    if (!m || m.stok <= 0) delete state.cart[id];
    else state.cart[id] = Math.min(state.cart[id], m.stok);
  }
  if (!daftarKategori().includes(state.kategori)) state.kategori = 'Semua';
  renderKategori();
  renderMenu();
}

/* ---------- Keranjang ---------- */
function tambah(id) {
  const m = state.menu.find(x => x.id === id);
  if (!m) return;
  if ((state.cart[id] || 0) + 1 > m.stok) return toast('Stok ' + m.nama + ' tidak cukup', true);
  state.cart[id] = (state.cart[id] || 0) + 1;
  perbaruiKeranjang();
}

function ubah(id, d) {
  const m = state.menu.find(x => x.id === id);
  const baru = (state.cart[id] || 0) + d;
  if (m && baru > m.stok) return toast('Stok ' + m.nama + ' tidak cukup', true);
  if (baru <= 0) delete state.cart[id]; else state.cart[id] = baru;
  perbaruiKeranjang();
}

function hitungKeranjang() {
  let total = 0, jumlah = 0;
  for (const [id, n] of Object.entries(state.cart)) {
    const m = state.menu.find(x => x.id === Number(id));
    if (m) { total += m.harga * n; jumlah += n; }
  }
  return { total, jumlah };
}

function renderKeranjang() {
  const ids = Object.keys(state.cart).map(Number).filter(id => state.menu.some(m => m.id === id));
  const { total, jumlah } = hitungKeranjang();
  $('#keranjang').innerHTML = ids.length ? ids.map(id => {
    const m = state.menu.find(x => x.id === id);
    const n = state.cart[id];
    return `<div class="baris">
      <div class="info"><strong>${esc(m.nama)}</strong><small>${n > 1 ? n + ' &times; ' + rp(m.harga) + ' =' : ''} <b>${rp(m.harga * n)}</b></small></div>
      <div class="qty">
        <button type="button" data-ubah="${id}" data-d="-1" aria-label="Kurangi ${esc(m.nama)}">&minus;</button>
        <output aria-label="Jumlah ${esc(m.nama)}">${n}</output>
        <button type="button" data-ubah="${id}" data-d="1" aria-label="Tambah ${esc(m.nama)}">+</button>
      </div>
    </div>`;
  }).join('') : `<div class="kosong">Keranjang masih kosong.
      <div class="aksi-inline"><button type="button" class="btn kecil alt" data-ke-menu>Pilih menu</button></div></div>`;

  $('#total').textContent = rp(total);
  $('#buat').disabled = !ids.length || state.sibuk;
  $('#petunjuk').hidden = ids.length > 0;
  $('#kosongkan').hidden = !ids.length;
  const b = $('#badge');
  b.hidden = jumlah === 0;
  b.textContent = jumlah;
  b.setAttribute('aria-label', jumlah + ' item di keranjang');
}

function perbaruiKeranjang() {
  simpanKeranjang();
  renderKeranjang();
  renderMenu();
}

async function buatPesanan() {
  const item = Object.entries(state.cart).map(([id, jumlah]) => ({ menu_id: Number(id), jumlah }));
  if (!item.length || state.sibuk) return;
  state.sibuk = true;
  $('#buat').disabled = true;
  $('#buat').textContent = 'Membuat pesanan…';
  try {
    const p = await api('/pesanan', {
      method: 'POST',
      body: JSON.stringify({
        nama_pelanggan: $('#nama').value.trim() || 'Pelanggan',
        meja: $('#meja').value.trim() || null,
        item,
      }),
    });
    state.cart = {};
    simpanKeranjang();
    $('#nama').value = '';
    $('#meja').value = '';
    toast('Pesanan #' + p.id + ' dibuat. Total ' + rp(p.total));
    if (window.matchMedia('(max-width: 699px)').matches) setTab('pesanan');
  } catch (e) {
    toast(e.message, true);
  } finally {
    state.sibuk = false;
    $('#buat').textContent = 'Buat Pesanan';
    await segarkan();
  }
}

/* ---------- Daftar pesanan ---------- */
function renderPesanan() {
  const aktif = ['MENUNGGU_PEMBAYARAN', 'DIBAYAR'];
  const daftar = state.pesanan.filter(p => state.tampil === 'semua' || aktif.includes(p.status));
  $('#pesanan').innerHTML = daftar.length ? daftar.map(p => {
    const s = STATUS[p.status] || { label: p.status, ikon: '' };
    let aksi = '';
    if (p.status === 'MENUNGGU_PEMBAYARAN') {
      aksi = `<button type="button" class="btn kecil" data-bayar="${p.id}" data-total="${p.total}">Bayar</button>
              <button type="button" class="btn kecil bahaya-garis" data-batal="${p.id}">Batalkan</button>`;
    } else if (p.status === 'DIBAYAR') {
      aksi = `<button type="button" class="btn kecil alt" data-selesai="${p.id}">Tandai selesai</button>`;
    }
    return `<article class="pesanan" aria-label="Pesanan ${p.id}, ${esc(p.nama_pelanggan)}, ${s.label}">
      <div class="atas">
        <strong>#${p.id} &middot; ${esc(p.nama_pelanggan)}${p.meja ? ' &middot; Meja ' + esc(p.meja) : ''}</strong>
        <span class="status ${esc(p.status)}"><span aria-hidden="true">${s.ikon}</span> ${s.label}</span>
      </div>
      <ul>${p.item.map(i => `<li>${i.jumlah} &times; ${esc(i.nama)}</li>`).join('')}</ul>
      <div class="bawah"><strong>${rp(p.total)}</strong><div class="aksi-baris">${aksi}</div></div>
    </article>`;
  }).join('') : `<p class="kosong">${state.tampil === 'aktif' ? 'Tidak ada pesanan aktif.' : 'Belum ada pesanan.'}</p>`;
}

async function muatPesanan() {
  state.pesanan = await api('/pesanan?limit=40');
  renderPesanan();
}

async function batalkan(id) {
  const ya = await tanya('Batalkan pesanan #' + id + '?',
    'Stok akan dikembalikan dan pesanan tidak bisa dibuka lagi.', 'Ya, batalkan');
  if (!ya) return;
  try { await api('/pesanan/' + id + '/batal', { method: 'POST' }); toast('Pesanan #' + id + ' dibatalkan'); }
  catch (e) { toast(e.message, true); }
  await segarkan();
}

async function selesaikan(id) {
  try {
    await api('/pesanan/' + id + '/status', { method: 'PATCH', body: JSON.stringify({ status: 'SELESAI' }) });
    toast('Pesanan #' + id + ' selesai');
  } catch (e) { toast(e.message, true); }
  await segarkan();
}

/* ---------- Pembayaran ---------- */
function nominalCepat(total) {
  const bulat = [20000, 50000, 100000].filter(n => n >= total);
  return [{ label: 'Uang pas', nilai: total }, ...bulat.map(n => ({ label: rp(n), nilai: n }))];
}

function hitungKembalian() {
  const total = state.bayar.total;
  const el = $('#kembalian');
  if ($('#metode').value !== 'TUNAI') { el.textContent = ''; el.className = 'kembalian'; return; }
  const dibayar = Number($('#bayar').value) || 0;
  if (dibayar >= total) {
    el.textContent = 'Kembalian: ' + rp(dibayar - total);
    el.className = 'kembalian';
  } else {
    el.textContent = dibayar ? 'Uang kurang ' + rp(total - dibayar) : '';
    el.className = 'kembalian kurang';
  }
}

function bukaBayar(id, total) {
  state.bayar = { id, total };
  $('#dlg-id').textContent = '#' + id;
  $('#dlg-total').textContent = rp(total);
  $('#metode').value = 'TUNAI';
  $('#blok-tunai').hidden = false;
  $('#bayar').value = total;
  $('#cepat').innerHTML = nominalCepat(total).map(n =>
    `<button type="button" class="chip" data-nominal="${n.nilai}">${esc(n.label)}</button>`).join('');
  hitungKembalian();
  $('#dlg-bayar').showModal();
  $('#bayar').select();
}

async function konfirmasiBayar() {
  if (!state.bayar || state.sibuk) return;
  const { id, total } = state.bayar;
  const metode = $('#metode').value;
  const jumlah = metode === 'TUNAI' ? Number($('#bayar').value) : total;
  if (metode === 'TUNAI' && jumlah < total) {
    hitungKembalian();
    return toast('Uang yang diterima masih kurang', true);
  }
  state.sibuk = true;
  $('#bayar-ok').disabled = true;
  try {
    const t = await api('/tagihan/' + id + '/bayar', {
      method: 'POST',
      body: JSON.stringify({ metode, jumlah_bayar: jumlah }),
    });
    $('#dlg-bayar').close();
    toast(t.kembalian ? 'Lunas. Kembalian ' + rp(t.kembalian) : 'Lunas. Terima kasih!');
  } catch (e) {
    toast(e.message, true);
  } finally {
    state.sibuk = false;
    $('#bayar-ok').disabled = false;
    await segarkan();
  }
}

/* ---------- Laporan dan penyegaran ---------- */
async function muatLaporan() {
  const l = await api('/tagihan/laporan');
  $('#laporan').textContent = 'Hari ini: ' + l.jumlah_transaksi + ' transaksi, ' + rp(l.total_pendapatan);
}

async function segarkan() {
  try {
    await Promise.all([muatMenu(), muatPesanan(), muatLaporan()]);
    renderKeranjang();
  } catch (e) {
    toast(e.message, true);
  }
}

/* ---------- Navigasi ---------- */
function setTab(nama) {
  if (nama === 'rekap' && peran() !== 'pemilik') nama = 'menu';   // kasir tidak punya halaman Rekap
  if (nama !== 'rekap') state.tabKasir = nama;
  document.body.dataset.tab = nama;
  document.querySelectorAll('.bottomnav button').forEach(b => {
    if (b.dataset.tab === nama) b.setAttribute('aria-current', 'page');
    else b.removeAttribute('aria-current');
  });
  document.querySelectorAll('[data-halaman]').forEach(b =>
    b.setAttribute('aria-pressed', String((b.dataset.halaman === 'rekap') === (nama === 'rekap'))));
  window.scrollTo({ top: 0 });
  if (nama === 'rekap') muatRekap();
}

/* ---------- Rekap penjualan (khusus pemilik) ---------- */
function hariIni() {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Jakarta' });   // YYYY-MM-DD, WIB
}

function geser(iso, periode, arah) {
  const [y, m, d] = iso.split('-').map(Number);
  if (periode === 'bulanan') {
    const tujuan = new Date(Date.UTC(y, m - 1 + arah, 1));
    const hariTerakhir = new Date(Date.UTC(tujuan.getUTCFullYear(), tujuan.getUTCMonth() + 1, 0)).getUTCDate();
    tujuan.setUTCDate(Math.min(d, hariTerakhir));
    return tujuan.toISOString().slice(0, 10);
  }
  const t = new Date(Date.UTC(y, m - 1, d + arah * (periode === 'mingguan' ? 7 : 1)));
  return t.toISOString().slice(0, 10);
}

function awalPeriode(iso, periode) {
  const [y, m, d] = iso.split('-').map(Number);
  if (periode === 'bulanan') return iso.slice(0, 8) + '01';
  if (periode === 'harian') return iso;
  const t = new Date(Date.UTC(y, m - 1, d));
  t.setUTCDate(t.getUTCDate() - ((t.getUTCDay() + 6) % 7));   // mundur ke Senin
  return t.toISOString().slice(0, 10);
}

function perbaruiKontrolRekap() {
  const r = state.rekap;
  document.querySelectorAll('[data-periode]').forEach(b =>
    b.setAttribute('aria-pressed', String(b.dataset.periode === r.periode)));
  $('#rekap-tgl').value = r.acuan;
  $('#rekap-tgl').max = hariIni();
  $('#rekap-next').disabled = awalPeriode(geser(r.acuan, r.periode, 1), r.periode) > hariIni();
}

const NAMA_METODE = { TUNAI: 'Tunai', QRIS: 'QRIS', TRANSFER: 'Transfer', LAINNYA: 'Lainnya' };

function renderRekap(d) {
  const maks = Math.max(1, ...d.rincian.map(x => x.total));
  const padat = d.rincian.length > 12;
  const langkah = d.periode === 'harian' ? 3 : (d.rincian.length > 20 ? 5 : 1);
  const lalu = d.periode_sebelumnya;
  const nama = { harian: 'kemarin', mingguan: 'pekan lalu', bulanan: 'bulan lalu' }[d.periode];
  let banding;
  if (d.perubahan_persen === null) {
    banding = lalu.total_pendapatan > 0 ? '' : 'Tidak ada pembanding (' + nama + ' belum ada penjualan)';
  } else {
    const naik = d.perubahan_persen >= 0;
    banding = `<span class="${naik ? 'naik' : 'turun'}"><span aria-hidden="true">${naik ? '▲' : '▼'}</span> ` +
      `${naik ? 'Naik' : 'Turun'} ${Math.abs(d.perubahan_persen).toLocaleString('id-ID')}%</span> dibanding ${nama} (${rp(lalu.total_pendapatan)})`;
  }

  if (!d.jumlah_transaksi) {
    $('#rekap-isi').innerHTML = '<p class="kosong">Belum ada pembayaran lunas pada periode ini.</p>' +
      (banding ? `<p class="banding">${banding}</p>` : '');
    return;
  }

  const ringkas = d.rincian.map(x => `${x.keterangan}: ${rp(x.total)}`).join('; ');
  const batang = d.rincian.map((x, i) => {
    const tinggi = x.total ? Math.max(3, Math.round(x.total / maks * 100)) : 0;
    const puncak = d.puncak && d.puncak.kunci === x.kunci;
    const tampil = i % langkah === 0;
    return `<div class="bar${puncak ? ' puncak' : ''}" title="${esc(x.keterangan)}: ${rp(x.total)}, ${x.jumlah_transaksi} transaksi">
      <div class="bar-isi" style="height:${tinggi}%"></div>
      <span class="bar-label" aria-hidden="true">${tampil ? esc(x.label) : ''}</span></div>`;
  }).join('');

  const metode = d.per_metode.filter(m => m.jumlah_transaksi > 0).map(m => {
    const persen = d.total_pendapatan ? Math.round(m.total / d.total_pendapatan * 100) : 0;
    return `<li><span>${esc(NAMA_METODE[m.metode] || m.metode)}</span>
      <span class="meter" aria-hidden="true"><span style="width:${persen}%"></span></span>
      <span class="angka"><strong>${rp(m.total)}</strong> <small>${m.jumlah_transaksi}x &middot; ${persen}%</small></span></li>`;
  }).join('');

  const kolom = d.periode === 'harian' ? 'Jam' : 'Tanggal';
  const baris = d.rincian.filter(x => x.jumlah_transaksi > 0).map(x =>
    `<tr><th scope="row">${esc(x.keterangan)}</th><td>${x.jumlah_transaksi}</td><td>${rp(x.total)}</td></tr>`).join('');

  $('#rekap-isi').innerHTML = `
    <div class="kpi">
      <div class="kartu-kpi"><span>Total pendapatan</span><strong>${rp(d.total_pendapatan)}</strong></div>
      <div class="kartu-kpi"><span>Transaksi</span><strong>${d.jumlah_transaksi}</strong></div>
      <div class="kartu-kpi"><span>Rata-rata per transaksi</span><strong>${rp(d.rata_rata_transaksi)}</strong></div>
    </div>
    ${banding ? `<p class="banding">${banding}</p>` : ''}
    <h3>Pendapatan per ${d.periode === 'harian' ? 'jam' : 'hari'}</h3>
    <div class="grafik${padat ? ' padat' : ''}" role="img" aria-label="Grafik batang pendapatan. ${esc(ringkas)}">${batang}</div>
    ${d.puncak ? `<p class="puncak-info">Tertinggi: ${esc(d.puncak.keterangan)} (${rp(d.puncak.total)})</p>` : ''}
    <h3>Metode pembayaran</h3>
    <ul class="metode-daftar">${metode}</ul>
    <details class="tabel-rincian">
      <summary>Lihat rincian sebagai tabel</summary>
      <div class="tabel-bungkus"><table>
        <caption class="sr">Rincian penjualan ${esc(d.label)}</caption>
        <thead><tr><th scope="col">${kolom}</th><th scope="col">Transaksi</th><th scope="col">Pendapatan</th></tr></thead>
        <tbody>${baris}</tbody>
        <tfoot><tr><th scope="row">Total</th><td>${d.jumlah_transaksi}</td><td>${rp(d.total_pendapatan)}</td></tr></tfoot>
      </table></div>
    </details>`;
}

async function muatRekap() {
  if (peran() !== 'pemilik') return;
  const r = state.rekap;
  if (!r.acuan) r.acuan = hariIni();
  perbaruiKontrolRekap();
  const no = ++r.no;                       // abaikan jawaban lama bila pengguna cepat berpindah periode
  $('#rekap-isi').setAttribute('aria-busy', 'true');
  $('#rekap-label').textContent = 'Memuat…';
  $('#rekap-isi').innerHTML = '<p class="kosong">Memuat rekap&hellip;</p>';
  try {
    const d = await api('/tagihan/rekap?periode=' + r.periode + '&tanggal=' + r.acuan);
    if (no !== r.no) return;
    $('#rekap-label').textContent = d.label;
    renderRekap(d);
  } catch (e) {
    if (no !== r.no || !state.sesi) return;
    $('#rekap-label').textContent = '';
    $('#rekap-isi').innerHTML = `<p class="kosong galat-blok">${esc(e.message)}
      <button type="button" class="btn kecil" id="rekap-ulang">Coba lagi</button></p>`;
    $('#rekap-ulang').addEventListener('click', muatRekap);
  } finally {
    if (no === r.no) $('#rekap-isi').setAttribute('aria-busy', 'false');
  }
}

/* ---------- Pemasangan event ---------- */
function pasangEvent() {
  $('#cari').addEventListener('input', e => { state.q = e.target.value; renderMenu(); });

  $('#kategori').addEventListener('click', e => {
    const b = e.target.closest('[data-kat]');
    if (!b) return;
    state.kategori = b.dataset.kat;
    renderKategori();
    renderMenu();
  });

  $('#menu').addEventListener('click', e => {
    if (e.target.closest('[data-reset]')) {
      state.q = ''; state.kategori = 'Semua'; $('#cari').value = '';
      renderKategori(); renderMenu(); return;
    }
    const b = e.target.closest('[data-add]');
    if (b) tambah(Number(b.dataset.add));
  });

  $('#keranjang').addEventListener('click', e => {
    if (e.target.closest('[data-ke-menu]')) return setTab('menu');
    const b = e.target.closest('[data-ubah]');
    if (b) ubah(Number(b.dataset.ubah), Number(b.dataset.d));
  });

  $('#kosongkan').addEventListener('click', async () => {
    if (await tanya('Kosongkan keranjang?', 'Semua item yang dipilih akan dihapus.', 'Ya, kosongkan')) {
      state.cart = {};
      perbaruiKeranjang();
    }
  });

  $('#buat').addEventListener('click', buatPesanan);

  document.querySelectorAll('[data-tampil]').forEach(b => b.addEventListener('click', () => {
    state.tampil = b.dataset.tampil;
    document.querySelectorAll('[data-tampil]').forEach(x => x.setAttribute('aria-pressed', x === b));
    renderPesanan();
  }));

  $('#pesanan').addEventListener('click', e => {
    const bayar = e.target.closest('[data-bayar]');
    if (bayar) return bukaBayar(Number(bayar.dataset.bayar), Number(bayar.dataset.total));
    const batal = e.target.closest('[data-batal]');
    if (batal) return batalkan(Number(batal.dataset.batal));
    const selesai = e.target.closest('[data-selesai]');
    if (selesai) selesaikan(Number(selesai.dataset.selesai));
  });

  $('#form-bayar').addEventListener('submit', e => { e.preventDefault(); konfirmasiBayar(); });
  $('#bayar-tutup').addEventListener('click', () => $('#dlg-bayar').close());
  $('#bayar').addEventListener('input', hitungKembalian);
  $('#metode').addEventListener('change', () => {
    $('#blok-tunai').hidden = $('#metode').value !== 'TUNAI';
    hitungKembalian();
  });
  $('#cepat').addEventListener('click', e => {
    const b = e.target.closest('[data-nominal]');
    if (!b) return;
    $('#bayar').value = b.dataset.nominal;
    hitungKembalian();
  });

  document.querySelectorAll('.bottomnav button').forEach(b =>
    b.addEventListener('click', () => setTab(b.dataset.tab)));
  document.querySelectorAll('[data-halaman]').forEach(b =>
    b.addEventListener('click', () => setTab(b.dataset.halaman === 'rekap' ? 'rekap' : state.tabKasir)));

  /* Rekap */
  document.querySelectorAll('[data-periode]').forEach(b => b.addEventListener('click', () => {
    state.rekap.periode = b.dataset.periode;
    muatRekap();
  }));
  $('#rekap-prev').addEventListener('click', () => { state.rekap.acuan = geser(state.rekap.acuan, state.rekap.periode, -1); muatRekap(); });
  $('#rekap-next').addEventListener('click', () => { state.rekap.acuan = geser(state.rekap.acuan, state.rekap.periode, 1); muatRekap(); });
  $('#rekap-ini').addEventListener('click', () => { state.rekap.acuan = hariIni(); muatRekap(); });
  $('#rekap-tgl').addEventListener('change', e => { if (e.target.value) { state.rekap.acuan = e.target.value; muatRekap(); } });
  $('#rekap-muat').addEventListener('click', muatRekap);

  /* Masuk dan keluar */
  $('#form-login').addEventListener('submit', e => { e.preventDefault(); masuk(); });
  $('#lihat-sandi').addEventListener('click', () => {
    const tampil = $('#login-sandi').type === 'password';
    $('#login-sandi').type = tampil ? 'text' : 'password';
    $('#lihat-sandi').textContent = tampil ? 'Sembunyikan' : 'Tampilkan';
    $('#lihat-sandi').setAttribute('aria-pressed', String(tampil));
  });
  $('#keluar').addEventListener('click', async () => {
    if (await tanya('Keluar dari akun?', 'Keranjang yang belum dibuat menjadi pesanan akan dikosongkan.', 'Ya, keluar')) {
      state.cart = {};
      simpanKeranjang();
      keluar('Anda sudah keluar.');
    }
  });

  const offline = () => { $('#offline').hidden = navigator.onLine; };
  window.addEventListener('online', () => { offline(); segarkan(); });
  window.addEventListener('offline', offline);
  offline();
}

/* ---------- Masuk, keluar, dan siklus sesi ---------- */
function tampilkanLogin(info) {
  document.body.dataset.sesi = 'keluar';
  document.body.dataset.peran = '';
  $('#login-halaman').hidden = false;
  $('#aplikasi').hidden = true;
  $('#bottomnav').hidden = true;
  $('#halaman').hidden = true;
  $('#akun').hidden = true;
  $('#laporan').hidden = true;
  $('#skip').textContent = 'Langsung ke formulir masuk';
  $('#skip').setAttribute('href', '#login-user');
  $('#login-sandi').value = '';
  $('#login-galat').hidden = true;
  $('#login-info').hidden = !info;
  $('#login-info').textContent = info || '';
  $('#login-user').focus();
}

function tampilkanAplikasi() {
  const u = state.sesi.user;
  document.body.dataset.sesi = 'masuk';
  document.body.dataset.peran = u.role;
  $('#login-halaman').hidden = true;
  $('#aplikasi').hidden = false;
  $('#bottomnav').hidden = false;
  const pemilik = u.role === 'pemilik';
  $('#halaman').hidden = !pemilik;
  $('#sec-rekap').hidden = !pemilik;
  document.querySelector('.bottomnav [data-tab="rekap"]').hidden = !pemilik;
  document.querySelector('.bottomnav').style.setProperty('--kolom', pemilik ? 4 : 3);
  $('#akun-nama').textContent = u.nama;
  $('#akun-peran').textContent = u.role === 'pemilik' ? 'Pemilik' : 'Kasir';
  $('#akun').hidden = false;
  $('#laporan').hidden = false;
  $('#skip').textContent = 'Langsung ke konten';
  $('#skip').setAttribute('href', '#h-menu');
  setTab('menu');
  $('#menu').innerHTML = '<p class="kosong">Memuat menu&hellip;</p>';
  segarkan().then(() => {
    if (!state.menu.length && state.sesi) {
      $('#menu').innerHTML = '<p class="kosong">Menu belum bisa dimuat. ' +
        '<button type="button" class="btn kecil" id="ulang">Coba lagi</button></p>';
      $('#ulang').addEventListener('click', segarkan);
    }
  });
  clearInterval(state.timer);
  state.timer = setInterval(() => {
    if (!state.sesi) return;
    if (state.sesi.exp <= Date.now()) return keluar('Sesi berakhir. Silakan masuk lagi.');
    if (document.hidden) return;
    muatPesanan().catch(() => {});
    muatLaporan().catch(() => {});
  }, 5000);
}

async function masuk() {
  if (state.sibuk) return;
  const username = $('#login-user').value.trim();
  const password = $('#login-sandi').value;
  const galat = $('#login-galat');
  if (!username || !password) {
    galat.textContent = !username ? 'Isi nama pengguna.' : 'Isi kata sandi.';
    galat.hidden = false;
    return (!username ? $('#login-user') : $('#login-sandi')).focus();
  }
  state.sibuk = true;
  galat.hidden = true;
  $('#login-ok').disabled = true;
  $('#login-ok').textContent = 'Memeriksa…';
  try {
    const d = await api('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }), tanpaToken: true });
    state.sesi = { token: d.access_token, exp: Date.now() + d.expires_in * 1000, user: d.user };
    simpanSesi();
    $('#login-sandi').value = '';
    $('#login-info').hidden = true;
    state.rekap.acuan = null;
    tampilkanAplikasi();
    $('#h-menu').focus();
  } catch (e) {
    galat.textContent = e.message;
    galat.hidden = false;
    $('#login-sandi').select();
  } finally {
    state.sibuk = false;
    $('#login-ok').disabled = false;
    $('#login-ok').textContent = 'Masuk';
  }
}

function keluar(info) {
  if (!state.sesi) return;                // sudah keluar (mis. beberapa permintaan ditolak sekaligus)
  hapusSesi();
  clearInterval(state.timer);
  state.timer = null;
  state.menu = []; state.pesanan = [];
  document.querySelectorAll('dialog[open]').forEach(d => d.close());
  tampilkanLogin(info);
}

/* ---------- Mulai ---------- */
muatKeranjang();
muatSesi();
pasangEvent();
if (state.sesi) tampilkanAplikasi(); else tampilkanLogin();

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('sw.js').catch(() => { /* PWA bersifat tambahan */ });
}
