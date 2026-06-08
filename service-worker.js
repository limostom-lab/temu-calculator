// TEMU 成本计算器 — Service Worker v2.1
const CACHE_NAME = 'temu-calc-v4';
const ASSETS = [
  './',
  './temuV0.6.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png'
];

// 安装：预缓存 + 强制跳过等待
self.addEventListener('install', event => {
  console.log('[SW] 安装中…');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS))
      .then(() => {
        console.log('[SW] 跳过等待，立即激活');
        return self.skipWaiting();
      })
  );
});

// 激活：清理旧缓存 + 立即接管所有页面
self.addEventListener('activate', event => {
  console.log('[SW] 激活中…');
  event.waitUntil(
    caches.keys().then(keys => {
      const oldKeys = keys.filter(k => k !== CACHE_NAME);
      console.log('[SW] 清理旧缓存:', oldKeys);
      return Promise.all(oldKeys.map(k => caches.delete(k)));
    }).then(() => {
      console.log('[SW] 接管所有页面');
      return self.clients.claim();
    }).then(() => {
      // 通知所有已打开的页面
      return self.clients.matchAll({ type: 'window' }).then(clients => {
        clients.forEach(client => {
          client.postMessage({ type: 'UPDATE_AVAILABLE' });
        });
      });
    })
  );
});

// 请求拦截：网络优先（确保拿到最新版本），失败时回退到缓存
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  // 外部资源：网络优先
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

  // 本地资源：网络优先
  event.respondWith(
    fetch(event.request)
      .then(response => {
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
    console.log('[SW] 收到 SKIP_WAITING 消息');
    self.skipWaiting();
  }
});
