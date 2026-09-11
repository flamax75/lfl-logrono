/* PWA sin caché de aplicación. El JSON de ESPN siempre va a red, sin reutilizar
   una respuesta anterior; el navegador puede gestionar con normalidad los estáticos. */
'use strict';
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  if (new URL(event.request.url).pathname.endsWith('/data/league.json')) {
    event.respondWith(fetch(new Request(event.request, { cache: 'no-store' })));
  }
});
