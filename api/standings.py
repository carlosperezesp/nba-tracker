from http.server import BaseHTTPRequestHandler
from _espn import proxy

URL = "https://site.web.api.espn.com/apis/v2/sports/basketball/nba/standings"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        proxy(self, URL)
