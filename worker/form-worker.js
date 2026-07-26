/**
 * Cloudflare Worker — приём заявок с narada-travels.com и отправка в Telegram.
 *
 * Токен бота НИКОГДА не попадает в код сайта. Он живёт в переменных
 * окружения воркера:
 *   BOT_TOKEN — токен от @BotFather (тип: Secret)
 *   CHAT_ID   — куда слать заявки (тип: Text)
 *
 * Деплой: Cloudflare → Workers & Pages → Create Worker → вставить этот код →
 * Deploy → Settings → Variables and Secrets → добавить BOT_TOKEN и CHAT_ID.
 */

const ALLOWED_ORIGINS = [
  'https://narada-travels.com',
  'https://www.narada-travels.com'
];

function corsHeaders(origin) {
  return {
    'Access-Control-Allow-Origin': ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0],
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400'
  };
}

function json(body, status, headers) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...headers, 'Content-Type': 'application/json' }
  });
}

// Обрезаем поля и вырезаем угловые скобки — текст уходит в Telegram без parse_mode,
// так что этого достаточно, чтобы заявка не превратилась в разметку или простыню.
const clean = (v, max) => String(v ?? '').replace(/[<>]/g, '').trim().slice(0, max);

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const headers = corsHeaders(origin);

    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers });
    if (request.method !== 'POST') return json({ ok: false }, 405, headers);
    if (!ALLOWED_ORIGINS.includes(origin)) return json({ ok: false }, 403, headers);

    let d;
    try {
      d = await request.json();
    } catch {
      return json({ ok: false }, 400, headers);
    }

    // Honeypot: поле скрыто от людей, боты его заполняют. Отвечаем "ок" и молчим.
    if (d.website) return json({ ok: true }, 200, headers);

    const name = clean(d.name, 100);
    const contact = clean(d.contact, 100);
    if (!name || !contact) return json({ ok: false }, 400, headers);

    const text = [
      'Новая заявка!',
      '',
      `Имя: ${name}`,
      `Контакт: ${contact}`,
      `Тур: ${clean(d.tour, 120) || 'не указан'}`,
      `Человек: ${clean(d.people, 20) || 'не указано'}`,
      `Даты: ${clean(d.dates, 80) || 'не указаны'}`,
      `Комментарий: ${clean(d.comment, 1000) || 'нет'}`
    ].join('\n');

    // Токен вставляют руками — подчищаем пробелы, перевод строки и случайный префикс "bot"
    const token = String(env.BOT_TOKEN ?? '').trim().replace(/^bot/, '');
    if (!/^\d+:[A-Za-z0-9_-]{30,}$/.test(token)) {
      console.error('BOT_TOKEN не похож на токен: длина', token.length);
    }

    const tg = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: env.CHAT_ID, text })
    });

    if (!tg.ok) {
      // Тело ответа Telegram — без токена, он только в URL
      console.error('Telegram error', tg.status, await tg.text());
      return json({ ok: false }, 502, headers);
    }
    return json({ ok: true }, 200, headers);
  }
};
