import sys
from urllib.parse import urljoin
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.request import build_opener, HTTPCookieProcessor, Request
from urllib.parse import urlencode

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


def request_text(opener, url, data=None, headers=None):
    if headers is None:
        headers = {}
    if data is not None:
        data = data.encode('utf-8')
    req = Request(url, data=data, headers=headers)
    with opener.open(req) as response:
        return response.read().decode('utf-8'), response.getcode(), response.headers


def main():
    base = 'http://127.0.0.1:8000/ar/'
    login_url = urljoin(base, 'auth/login/')
    pos_url = urljoin(base, 'sales/pos/')
    create_url = urljoin(base, 'sales/pos/create-invoice/')

    cookie_jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))

    print('GET login page:', login_url)
    html, code, headers = request_text(opener, login_url)
    print('login status', code)
    csrf = get_csrf(html)
    print('csrf token', csrf)
    if csrf is None:
        print('Failed to find CSRF token on login page')
        sys.exit(1)

    login_data = {
        'username': 'pos',
        'password': 'admin123',
        'csrfmiddlewaretoken': csrf,
    }
    body = urlencode(login_data)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': login_url,
    }
    print('POST login')
    html, code, headers = request_text(opener, login_url, data=body, headers=headers)
    print('login post status', code)

    print('GET POS page:', pos_url)
    html, code, headers = request_text(opener, pos_url)
    print('pos page status', code)
    csrf = get_csrf(html)
    print('pos page csrf', csrf)
    if csrf is None:
        print('Failed to find CSRF token on POS page')

    sale_data = {
        'items': [
            {'product_id': 1, 'quantity': 1, 'unit_price': 1.0, 'total': 1.0, 'tax_rate': 0, 'tax_amount': 0}
        ],
        'subtotal': 1.0,
        'tax_amount': 0.0,
        'discount_amount': 0.0,
        'total': 1.0,
    }
    import json
    body = json.dumps(sale_data).encode('utf-8')
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/json',
        'Referer': pos_url,
    }
    # add csrf token from cookies if present
    for cookie in cookie_jar:
        if cookie.name in ('csrftoken', 'finspilot_csrftoken') or cookie.name.endswith('csrftoken'):
            headers['X-CSRFToken'] = cookie.value
            print('using csrftoken cookie', cookie.name, cookie.value)
            break

    print('POST create invoice:', create_url)
    req = Request(create_url, data=body, headers=headers)
    with opener.open(req) as response:
        res_text = response.read().decode('utf-8')
        print('status', response.getcode())
        print('content-type', response.headers.get('Content-Type'))
        print('response body', res_text)


if __name__ == '__main__':
    main()
