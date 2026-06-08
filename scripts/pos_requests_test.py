import requests
from urllib.parse import urljoin
from html.parser import HTMLParser

class CsrfParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.csrf = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'input':
            attrs = dict(attrs)
            if attrs.get('name') == 'csrfmiddlewaretoken':
                self.csrf = attrs.get('value')


def get_csrf(html):
    parser = CsrfParser()
    parser.feed(html)
    return parser.csrf


def main():
    base = 'http://127.0.0.1:8000/ar/'
    login_url = urljoin(base, 'auth/login/')
    pos_url = urljoin(base, 'sales/pos/')
    create_url = urljoin(base, 'sales/pos/create-invoice/')

    s = requests.Session()
    res = s.get(login_url)
    print('GET login', res.status_code, res.url)
    csrf = get_csrf(res.text)
    print('csrf', csrf)
    print('cookies after GET', s.cookies.get_dict())

    res2 = s.post(login_url, data={'username': 'pos', 'password': 'admin123', 'csrfmiddlewaretoken': csrf}, headers={'Referer': login_url}, allow_redirects=False)
    print('POST login status', res2.status_code, res2.url)
    print('request body', res2.request.body)
    print('request headers', {k: v for k, v in res2.request.headers.items() if k in ['Referer', 'Content-Type', 'Cookie', 'Accept']})
    print('POST login headers', res2.headers)
    if 'location' in res2.headers:
        print('raw location', res2.headers['location'])
    print('cookies after POST', s.cookies.get_dict())
    print('history before redirects', res2.history)
    if res2.status_code == 302:
        res2_follow = s.get(urljoin(login_url, res2.headers['location']))
        print('followed status', res2_follow.status_code, res2_follow.url)
        print('followed headers', res2_follow.headers)
        print('followed cookies', s.cookies.get_dict())
    else:
        res2_follow = res2

    res3 = s.get(pos_url)
    print('GET pos status', res3.status_code, res3.url)
    print('pos page title snippet', res3.text[:200])

    if 'finspilot_sessionid' in s.cookies:
        print('session cookie found')
    else:
        print('NO session cookie found')

    # Try create invoice
    import json
    sale_data = {
        'items': [{'product_id': 1, 'quantity': 1, 'unit_price': 1.0, 'total': 1.0, 'tax_rate': 0, 'tax_amount': 0}],
        'subtotal': 1.0,
        'tax_amount': 0.0,
        'discount_amount': 0.0,
        'total': 1.0,
    }
    csrf_token = s.cookies.get('finspilot_csrftoken')
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': pos_url,
    }
    if csrf_token:
        headers['X-CSRFToken'] = csrf_token
    res4 = s.post(create_url, json=sale_data, headers=headers)
    print('POST create status', res4.status_code, res4.headers.get('Content-Type'))
    print('create history', [(r.status_code, r.url) for r in res4.history])
    print('response text', res4.text[:2000])


if __name__ == '__main__':
    main()
