from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api._espn import proxy

SEASON = 2026


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        athlete_id = parse_qs(urlparse(self.path).query).get("id", [""])[0]
        url = (
            f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
            f"/seasons/{SEASON}/types/2/athletes/{athlete_id}/statistics?lang=en&region=us"
        )
        proxy(self, url)
