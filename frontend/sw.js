/* Service worker sederhana: kerangka aplikasi (HTML/CSS/JS/ikon) disimpan di cache
   supaya aplikasi terbuka cepat dan bisa "dipasang". Data (/api) SELALU diambil
   dari jaringan agar stok dan pembayaran tidak pernah basi. */
const CACHE = 'warkop-shell-v1';
const SHELL = ['./', 'index.html', 'css/style.css', 'js/app.js', 'manifest.json', 'icons/icon.svg'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api/')) return;
  // Jaringan dulu (agar pembaruan kode langsung terlihat), cache sebagai cadangan saat offline.
  e.respondWith(
    fetch(e.request)
      .then(res => {
        const salinan = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, salinan));
        return res;
      })
      .catch(() => caches.match(e.request).then(r => r || caches.match('index.html')))
  );
});
