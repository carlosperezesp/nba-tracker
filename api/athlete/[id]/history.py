from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api._espn import proxy


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        athlete_id = parse_qs(urlparse(self.path).query).get("id", [""])[0]
        url = (
            f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba"
            f"/athletes/{athlete_id}/stats?region=us&lang=en&contentorigin=espn"
        )
        proxy(self, url)
