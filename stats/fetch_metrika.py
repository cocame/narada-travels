import json
import os
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError

COUNTER = 109555301
TOKEN = os.environ.get('YM_TOKEN', '')
BASE = 'https://api-metrika.yandex.net/stat/v1/data'


def api(params):
    qs = '&'.join(f'{k}={v}' for k, v in params.items())
    req = Request(f'{BASE}?{qs}', headers={'Authorization': f'OAuth {TOKEN}'})
    try:
        with urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except URLError as e:
        print(f'API error: {e}', file=sys.stderr)
        sys.exit(1)


def totals(date1, date2, metrics):
    d = api({'ids': COUNTER, 'metrics': metrics, 'date1': date1, 'date2': date2})
    vals = d.get('totals', [[]])[0] if d.get('totals') else []
    n = len(metrics.split(','))
    return vals + [0.0] * (n - len(vals))


today = totals('today', 'today', 'ym:s:visits,ym:s:users,ym:s:bounceRate')
week = totals('7daysAgo', 'today', 'ym:s:visits,ym:s:users')
month = totals('30daysAgo', 'today', 'ym:s:visits,ym:s:users')

src_raw = api({
    'ids': COUNTER,
    'dimensions': 'ym:s:trafficSourceName',
    'metrics': 'ym:s:visits',
    'date1': '30daysAgo', 'date2': 'today',
    'sort': '-ym:s:visits', 'limit': 10,
})
sources = [
    {'name': r['dimensions'][0]['name'], 'visits': r['metrics'][0]}
    for r in src_raw.get('data', [])
]

pg_raw = api({
    'ids': COUNTER,
    'dimensions': 'ym:s:URLPath',
    'metrics': 'ym:s:visits',
    'date1': '30daysAgo', 'date2': 'today',
    'sort': '-ym:s:visits', 'limit': 10,
})
pages = [
    {'url': 'https://narada-travels.com' + r['dimensions'][0]['name'], 'visits': r['metrics'][0]}
    for r in pg_raw.get('data', [])
]

data = {
    'updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'today': {'visits': today[0], 'users': today[1], 'bounce': today[2]},
    'week': {'visits': week[0], 'users': week[1]},
    'month': {'visits': month[0], 'users': month[1]},
    'sources': sources,
    'pages': pages,
}

out = os.path.join(os.path.dirname(__file__), 'data.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✓ {data['updated']}  today={today[0]:.0f}v  week={week[0]:.0f}v  month={month[0]:.0f}v")
