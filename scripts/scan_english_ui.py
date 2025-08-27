import requests
from bs4 import BeautifulSoup
import re

HOST = 'http://127.0.0.1:8000'
LANG = 'ar'

paths = [
    f'/{LANG}/banks/accounts/',
    f'/{LANG}/banks/transfers/',
    f'/{LANG}/cashboxes/',
    f'/{LANG}/cashboxes/transfers/',
    f'/{LANG}/receipts/',
    f'/{LANG}/receipts/checks/',
    f'/{LANG}/payments/',
]

english_re = re.compile(r"[A-Za-z0-9]{2,}")
word_re = re.compile(r"[A-Za-z]{2,}")

results = {}

for p in paths:
    url = HOST + p
    try:
        r = requests.get(url, timeout=5)
    except Exception as e:
        results[p] = {'error': str(e)}
        continue
    if r.status_code != 200:
        results[p] = {'status': r.status_code}
        continue
    soup = BeautifulSoup(r.text, 'html.parser')
    # remove scripts and styles
    for s in soup(['script','style','noscript']):
        s.extract()
    text = soup.get_text(separator=' ')
    # find english word sequences of length>=2
    words = set([m.group(0) for m in word_re.finditer(text)])
    # filter out purely numeric and Arabic mixture
    en_words = sorted([w for w in words if any(c.isalpha() and c.isascii() for c in w)])
    results[p] = {'found': en_words[:200]}

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
            print(' ', ', '.join(v['found'][:50]))
