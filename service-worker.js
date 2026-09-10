/* PWA sin caché: todas las páginas y recursos se solicitan a la red.
   No se registra al abrir archivos locales ni en localhost.
   No se añaden listeners fetch ni almacenamiento offline deliberadamente. */
'use strict';
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
