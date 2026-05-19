from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import json
import time


ROOT = Path(__file__).resolve().parent
PORT = 8000
CACHE_TTL_SECONDS = 45

ESPN_ENDPOINTS = {
    "/api/scoreboard": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    "/api/standings": "https://site.web.api.espn.com/apis/v2/sports/basketball/nba/standings",
    "/api/teams": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams",
}

cache = {}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path in ESPN_ENDPOINTS:
            self.proxy_json(self.path)
            return

        if self.path.startswith("/api/roster/"):
            team = quote(self.path.rsplit("/", 1)[-1].lower())
            self.proxy_url(
                f"roster:{team}",
                f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team}/roster",
            )
            return

        if self.path.startswith("/api/athlete/") and self.path.endswith("/stats"):
            athlete_id = quote(self.path.split("/")[3])
            self.proxy_url(
                f"athlete-stats:{athlete_id}",
                "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/"
                f"seasons/2026/types/2/athletes/{athlete_id}/statistics?lang=en&region=us",
                ttl=60 * 30,
            )
            return

        if self.path.startswith("/api/athlete/") and self.path.endswith("/history"):
            athlete_id = quote(self.path.split("/")[3])
            self.proxy_url(
                f"athlete-history:{athlete_id}",
                "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/"
                f"athletes/{athlete_id}/stats?region=us&lang=en&contentorigin=espn",
                ttl=60 * 60,
            )
            return

        if self.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def proxy_json(self, route):
        self.proxy_url(route, ESPN_ENDPOINTS[route])

    def proxy_url(self, cache_key, url, ttl=CACHE_TTL_SECONDS):
        now = time.time()
        cached = cache.get(cache_key)
        if cached and now - cached["time"] < ttl:
            self.send_json(cached["payload"], cached=True)
            return

        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 CourtsideAnalyticsLocal/1.0",
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
                cache[cache_key] = {"time": now, "payload": payload}
                self.send_json(payload, cached=False)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            fallback = cached["payload"] if cached else {"error": str(error)}
            self.send_json(fallback, status=200 if cached else 502, cached=bool(cached))

    def send_json(self, payload, status=200, cached=False):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Local-Cache", "hit" if cached else "miss")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Courtside Analytics live server: http://127.0.0.1:{PORT}")
    print("Data source: ESPN public NBA endpoints, refreshed every 45 seconds.")
    server.serve_forever()
