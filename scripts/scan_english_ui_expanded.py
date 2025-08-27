import requests
from bs4 import BeautifulSoup
import re

HOST = 'http://127.0.0.1:8000'
LANG = 'ar'

paths = [
    f'/{LANG}/',
    f'/{LANG}/accounts/login/',
    f'/{LANG}/accounts/logout/',
    f'/{LANG}/banks/accounts/',
    f'/{LANG}/banks/transfers/',
    f'/{LANG}/cashboxes/',
    f'/{LANG}/cashboxes/transfers/',
    f'/{LANG}/receipts/',
    f'/{LANG}/receipts/checks/',
    f'/{LANG}/payments/',
    f'/{LANG}/products/',
    f'/{LANG}/inventory/',
    f'/{LANG}/customers/',
    f'/{LANG}/reports/',
    f'/{LANG}/journal/',
    f'/{LANG}/settings/',
    f'/{LANG}/purchases/',
    f'/{LANG}/sales/',
    f'/{LANG}/search/',
]

word_re = re.compile(r"[A-Za-z]{2,}")

results = {}

for p in paths:
    url = HOST + p
    try:
        r = requests.get(url, timeout=8)
    except Exception as e:
        results[p] = {'error': str(e)}
        continue
    if r.status_code != 200:
        results[p] = {'status': r.status_code}
        continue
    soup = BeautifulSoup(r.text, 'html.parser')
    for s in soup(['script','style','noscript']):
        s.extract()
    text = soup.get_text(separator=' ')
    words = set([m.group(0) for m in word_re.finditer(text)])
    en_words = sorted([w for w in words if any(c.isalpha() and c.isascii() for c in w)])
    # exclude the brand 'Finspilot' (any case)
    en_words = [w for w in en_words if w.lower() != 'finspilot']
    results[p] = {'found': en_words}

# print report
for p,v in results.items():
    print('\n==> URL:', p)
    if 'error' in v:
        print(' ERROR:', v['error'])
    elif 'status' in v:
        print(' HTTP status:', v['status'])
    else:
        print(' English tokens found:', len(v['found']))
        if v['found']:
            print(' ', ', '.join(v['found'][:200]))
