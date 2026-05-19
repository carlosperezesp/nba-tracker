from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from api._espn import proxy


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        team = parse_qs(urlparse(self.path).query).get("team", [""])[0]
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team}/roster"
        proxy(self, url)
