from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request, urllib.error

_H = {"User-Agent": "Mozilla/5.0 CourtsideAnalytics/1.0", "Accept": "application/json"}
SEASON = 2026


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
        athlete_id = parse_qs(urlparse(self.path).query).get("id", [""])[0]
        url = (
            f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
            f"/seasons/{SEASON}/types/2/athletes/{athlete_id}/statistics?lang=en&region=us"
        )
        body, code = _get(url)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)
