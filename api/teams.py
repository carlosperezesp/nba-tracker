from http.server import BaseHTTPRequestHandler
from _espn import proxy

URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        proxy(self, URL)
