from http.server import BaseHTTPRequestHandler
import urllib.request, urllib.error

_H = {"User-Agent": "Mozilla/5.0 CourtsideAnalytics/1.0", "Accept": "application/json"}
_URL = "https://site.web.api.espn.com/apis/v2/sports/basketball/nba/standings"


def _get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=_H), timeout=12) as r:
            return r.read(), 200
    except urllib.error.HTTPError as e:
        return f'{{"error":"{e}"}}'.encode(), e.code
    except Exception as e:
        return f'{{"error":"{e}"}}'.encode(), 502


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body, code = _get(_URL)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=45")
        self.end_headers()
        self.wfile.write(body)
