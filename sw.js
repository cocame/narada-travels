/* Service worker для упаковки сайта в приложение (PWA → Google Play).
   Задача у него одна: показать осмысленную страницу, когда интернета нет.
   Ничего лишнего он не делает и в отправку заявок не вмешивается.

   Правила кэширования выбраны осознанно:
   — только свои адреса (narada-travels.com), чужие скрипты и счётчики не трогаем;
   — только GET: заявка уходит POST'ом на воркер и мимо кэша;
   — только успешные обычные ответы: ошибки и переадресации в кэш не попадают,
     иначе человек офлайн увидел бы сохранённую «404» вместо страницы;
   — адреса с «?» не кэшируем: рекламные метки плодили бы копии одной страницы;
   — сначала сеть, кэш только как запасной вариант, поэтому цены на экране
     всегда свежие, пока есть связь.

   При правке этого файла менять V — иначе браузеры не заметят обновления.
   GitHub Pages отдаёт файлы с Cache-Control: max-age=600, поэтому новая версия
   доезжает до людей в течение десяти минут. */

const V = 'narada-v3';   // v3 — кремовая иконка приложения, 16 октября 2026
const OFFLINE = '/offline.html';

self.addEventListener('install', e => {
  e.waitUntil(caches.open(V).then(c => c.add(OFFLINE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(k => Promise.all(k.filter(x => x !== V).map(x => caches.delete(x))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  e.respondWith(
    fetch(req).then(res => {
      const можноВКэш = res.ok && res.type === 'basic' && !url.search;
      if (можноВКэш) {
        const копия = res.clone();
        caches.open(V).then(c => c.put(req, копия)).catch(() => {});
      }
      return res;
    }).catch(() =>
      caches.match(req, { ignoreSearch: true }).then(r =>
        r || (req.mode === 'navigate' ? caches.match(OFFLINE) : Response.error())
      )
    )
  );
});
