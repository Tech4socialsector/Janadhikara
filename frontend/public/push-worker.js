// A small service worker just for push alerts, registered on its own (scope
// /janadhikara/push-scope/) so alerts keep working no matter which version of the
// app's main service worker a device has cached. It reuses push-sw.js's handlers.
importScripts('/assets/janadhikara/frontend/push-sw.js')

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))
