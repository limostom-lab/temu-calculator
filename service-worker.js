// TEMU 成本计算器 — Service Worker v2.1
const CACHE_NAME = 'temu-calc-v2';
const ASSETS = [
  './',
  './temuV0.5.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png'
];

// 安装：预缓存核心资源
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

// 激活：清理旧缓存 + 通知所有客户端有更新
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
    .then(() => {
      // 通知所有已打开的页面：新版本已激活
      return self.clients.matchAll({ type: 'window' }).then(clients => {
        clients.forEach(client => {
          client.postMessage({ type: 'UPDATE_AVAILABLE' });
        });
      });
    })
  );
});

// 请求拦截：缓存优先，网络回退
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  // 外部资源：网络优先（Google Fonts 等）
  if (!event.request.url.startsWith(self.location.origin)) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // 本地资源：网络优先（确保拿到最新版本），失败时回退到缓存
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // 更新缓存
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});

// 监听来自主页面的消息
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
