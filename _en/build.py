#!/usr/bin/env python3
"""Английская версия сайта: /en/… собирается из русских страниц.

Запуск из корня репозитория:  python3 _en/build.py
  — пересобирает все страницы en/…/index.html из русских;
  — переводит каждую русскую строку по словарю _en/strings.json ([русский, английский]);
  — новые русские строки дописывает в словарь с пустым переводом и печатает список:
    их надо перевести и запустить сборку ещё раз. Пока перевода нет, на английской
    странице остаётся русский текст — сборка об этом предупреждает.

Правка русской страницы → сразу пересобрать английскую (и перевести новые строки).
Сами en/…/index.html руками не правим: сборка их перезаписывает.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(ROOT, '_en', 'strings.json')

# русская страница → каталог (у корня каталог пустой)
PAGES = ['', 'ba-na-hills', 'danang-one-day', 'hoi-an', 'hue', 'phu-quoc', 'nha-trang',
         'vietnam', 'ho-chi-minh', 'hanoi', 'mui-ne', 'uslugi']
# Политика уже двуязычная: английская часть — /privacy/#en, отдельной страницы не делаем
EN_DIRS = set(PAGES)

CYR = re.compile(r'[А-Яа-яЁё]')
ATTRS = r'content|alt|title|placeholder|aria-label|value|label|data-[\w-]+'


# ── словарь ──────────────────────────────────────────────
def load():
    rows = json.load(open(DICT, encoding='utf-8')) if os.path.exists(DICT) else []
    return {r[0]: r[1] for r in rows}, rows

def save(rows):
    with open(DICT, 'w', encoding='utf-8') as f:
        f.write('[\n' + ',\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n]\n')


# ── разбор страницы ──────────────────────────────────────
def js_strings(code, fn):
    """Заменяет строковые литералы JS с кириллицей через fn; комментарии не трогает."""
    out, i, n = [], 0, len(code)
    while i < n:
        c = code[i]
        if code.startswith('//', i):
            j = code.find('\n', i); j = n if j < 0 else j
            out.append(code[i:j]); i = j
        elif code.startswith('/*', i):
            j = code.find('*/', i + 2); j = n if j < 0 else j + 2
            out.append(code[i:j]); i = j
        elif c in '"\'`':
            j = i + 1
            while j < n and code[j] != c:
                if code[j] == '\\': j += 1
                elif c != '`' and code[j] == '\n': break
                j += 1
            body = code[i + 1:j]
            if CYR.search(body):
                # в переводе апостроф (we'll) не должен закрыть строку JS
                body = re.sub(r'(?<!\\)' + re.escape(c), '\\' + c, fn(body, js=True))
            out.append(c + body + c)
            i = j + 1
        else:
            out.append(c); i += 1
    return ''.join(out)

def transform(s, fn):
    parts = re.split(r'(<!--.*?-->|<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>|<[^>]+>)', s, flags=re.S)
    out = []
    for p in parts:
        if not p: continue
        if p.startswith('<!--'):
            out.append(p)
        elif p.startswith('<script'):
            m = re.match(r'(<script\b[^>]*>)(.*?)(</script>)$', p, re.S)
            out.append(m.group(1) + js_strings(m.group(2), fn) + m.group(3))
        elif p.startswith('<style'):
            out.append(p)
        elif p.startswith('<'):
            out.append(re.sub(r'\b(' + ATTRS + r')="([^"]*)"',
                              lambda m: m.group(1) + '="' + (fn(m.group(2)) if CYR.search(m.group(2)) else m.group(2)) + '"', p))
        else:
            t = p.strip()
            if CYR.search(t):
                a = p[:len(p) - len(p.lstrip())]; b = p[len(p.rstrip()):]
                out.append(a + fn(t) + b)
            else:
                out.append(p)
    return ''.join(out)


# ── ссылки, язык, переключатель ──────────────────────────
def en_path(path):
    """/phu-quoc/#x → /en/phu-quoc/#x, если у страницы есть английская версия."""
    m = re.match(r'/([\w-]*)/?([?#].*)?$', path)
    if m and m.group(1) == 'privacy': return '/privacy/#en'
    if not m or m.group(1) not in EN_DIRS: return None
    d = m.group(1)
    return '/en/' + (d + '/' if d else '') + (m.group(2) or '')

def fix_links(s, d):
    def href(m):
        p = en_path(m.group(2))
        return m.group(1) + '"' + (p or m.group(2)) + '"'
    s = re.sub(r'\b(href|data-preview-href)="(/[^"]*)"', href, s)
    # относительные картинки и видео → абсолютные, иначе из /en/… они не найдутся
    base = '/' + d + '/' if d else '/'
    s = re.sub(r'(["\'(])\.\./images/', r'\1/images/', s)
    s = re.sub(r'(["\'(])images/', lambda m: m.group(1) + base + 'images/', s)
    return s

HEAD_BITS = """<!-- langsw -->
{alt}<style>
  html:not(.preview) .langsw.only-preview{{display:none!important}}
  .langsw{{display:inline-flex;gap:2px;font:600 12px/1 system-ui,-apple-system,sans-serif;letter-spacing:.04em;align-items:center}}
  .langsw a{{padding:5px 7px;border-radius:6px;color:inherit;text-decoration:none;opacity:.6}}
  .langsw a[aria-current]{{opacity:1;background:rgba(127,127,127,.18)}}
  .langsw.float{{position:fixed;top:10px;right:10px;z-index:999;background:rgba(255,255,255,.85);border-radius:8px;color:#222}}
  nav:not(.solid) .nav-r .langsw a{{color:#fff}}
  .nav-r .langsw{{margin-right:4px}}
  /* телефон: только ссылка на другой язык, чтобы не выдавить меню */
  @media (max-width:768px){{.nav-r .langsw a[aria-current]{{display:none}} .nav-r .langsw a{{opacity:.9;padding:5px 8px}}}}
</style>
<script>try{{if(localStorage.getItem('narada_preview')==='1')document.documentElement.classList.add('preview')}}catch(e){{}}</script>
<!-- /langsw -->
"""

def switcher(ru, en, cur, float_=False):
    cls = 'langsw only-preview' + (' float' if float_ else '')
    a_ru = ' aria-current="true"' if cur == 'ru' else ''
    a_en = ' aria-current="true"' if cur == 'en' else ''
    return (f'<!-- langsw --><span class="{cls}" aria-label="Language">'
            f'<a href="{ru}" hreflang="ru"{a_ru}>RU</a><a href="{en}" hreflang="en"{a_en}>EN</a></span><!-- /langsw -->')

def add_lang_bits(s, d, cur):
    ru = '/' + (d + '/' if d else '')
    en = '/en' + ru
    alt = (f'<link rel="alternate" hreflang="ru" href="https://narada-travels.com{ru}">\n'
           f'<link rel="alternate" hreflang="en" href="https://narada-travels.com{en}">\n')
    s = re.sub(r'<!-- langsw -->.*?<!-- /langsw -->\n?', '', s, flags=re.S)
    s = s.replace('</head>', HEAD_BITS.format(alt=alt) + '</head>', 1)
    if '<div class="nav-r">' in s:
        s = s.replace('<div class="nav-r">', '<div class="nav-r">' + switcher(ru, en, cur), 1)
    else:
        s = re.sub(r'(<body\b[^>]*>)', lambda m: m.group(1) + switcher(ru, en, cur, True), s, count=1)
    return s


def build():
    d_, rows = load()
    known = {r[0] for r in rows}
    missing = []

    def fn(t, js=False):
        if t not in known:
            rows.append([t, '']); known.add(t); d_[t] = ''
        tr = d_.get(t)
        if not tr:
            missing.append(t); return t
        return tr

    for d in PAGES:
        src = os.path.join(ROOT, d, 'index.html')
        s = open(src, encoding='utf-8').read()
        # русская страница: только переключатель и hreflang
        ru = add_lang_bits(s, d, 'ru')
        if ru != s: open(src, 'w', encoding='utf-8').write(ru)
        en = transform(s, fn)
        en = fix_links(en, d)
        en = en.replace("location.replace('/')", "location.replace('/en/')")
        # заявка с английской версии — с пометкой, чтобы было видно, что клиент англоязычный
        en = en.replace("comment: КОГДА,", "comment: 'EN-сайт · ' + КОГДА,").replace("comment: '',", "comment: 'EN-сайт',")
        en = en.replace('<html lang="ru"', '<html lang="en"', 1)
        en = en.replace('content="ru_RU"', 'content="en_US"')
        en = re.sub(r'(https://narada-travels\.com)(/[\w-]*/?)(?=["#?])',
                    lambda m: m.group(1) + (en_path(m.group(2)) or m.group(2)), en)
        # пока английская версия не открыта — не индексировать
        en = re.sub(r'<meta name="robots" content="[^"]*">', '<meta name="robots" content="noindex, follow">', en)
        en = add_lang_bits(en, d, 'en')
        out = os.path.join(ROOT, 'en', d, 'index.html')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, 'w', encoding='utf-8').write(en)

    save(rows)
    miss = sorted(set(missing))
    print(f'страниц: {len(PAGES)}, строк в словаре: {len(rows)}, без перевода: {len(miss)}')
    return miss

if __name__ == '__main__':
    miss = build()
    if miss and '-q' not in sys.argv:
        for t in miss[:30]: print('  нет перевода:', t[:90])
