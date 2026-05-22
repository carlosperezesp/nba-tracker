from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import json
import re
import sqlite3
import time


ROOT    = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "nba.db"
PORT    = 8000
CACHE_TTL_SECONDS = 45

ESPN_ENDPOINTS = {
    "/api/scoreboard": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    "/api/standings":  "https://site.web.api.espn.com/apis/v2/sports/basketball/nba/standings",
    "/api/teams":      "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams",
}

cache = {}


def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ESPN_ENDPOINTS:
            self.proxy_json(path)
            return

        if path.startswith("/api/roster/"):
            team = quote(path.rsplit("/", 1)[-1].lower())
            self.proxy_url(
                f"roster:{team}",
                f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team}/roster",
            )
            return

        if path.startswith("/api/athlete/") and path.endswith("/stats"):
            athlete_id = quote(path.split("/")[3])
            self.proxy_url(
                f"athlete-stats:{athlete_id}",
                "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/"
                f"seasons/2026/types/2/athletes/{athlete_id}/statistics?lang=en&region=us",
                ttl=60 * 30,
            )
            return

        if path.startswith("/api/athlete/") and path.endswith("/history"):
            athlete_id = quote(path.split("/")[3])
            self.proxy_url(
                f"athlete-history:{athlete_id}",
                "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/"
                f"athletes/{athlete_id}/stats?region=us&lang=en&contentorigin=espn",
                ttl=60 * 60,
            )
            return

        # ── SQLite endpoints ──────────────────────────────────────────────────

        if path == "/api/db/players":
            self.serve_db_players()
            return

        m = re.match(r"^/api/db/players/(\d+)/seasons$", path)
        if m:
            self.serve_db_player_seasons(int(m.group(1)))
            return

        m = re.match(r"^/api/db/teams/([A-Z]+)/roster$", path)
        if m:
            self.serve_db_team_roster(m.group(1))
            return

        if path == "/":
            self.path = "/index.html"

        super().do_GET()

    # ── DB handlers ───────────────────────────────────────────────────────────

    def serve_db_players(self):
        if not DB_PATH.exists():
            self.send_json({"error": "DB not built. Run: python3 build_db.py"}, status=503)
            return
        with db_conn() as conn:
            rows = conn.execute("""
                SELECT p.id, p.name, p.pos, p.headshot, p.team,
                       s.season, s.year, s.gp, s.min,
                       s.pts, s.reb, s.ast, s.stl, s.blk, s.tov, s.pf,
                       s.fgm, s.fga, s.ftm, s.fta, s.fg_pct,
                       s.pir_base, s.pir_36, s.score_season, s.score_alltime
                FROM players p
                JOIN (
                    SELECT *, ROW_NUMBER() OVER (
                        PARTITION BY player_id ORDER BY year DESC, gp DESC
                    ) AS rn FROM seasons
                ) s ON s.player_id = p.id AND s.rn = 1
                ORDER BY s.score_season DESC
            """).fetchall()
        self.send_json([dict(r) for r in rows])

    def serve_db_player_seasons(self, player_id):
        if not DB_PATH.exists():
            self.send_json([], status=503)
            return
        with db_conn() as conn:
            rows = conn.execute("""
                SELECT s.season, s.year, s.team, s.gp, s.min,
                       s.pts, s.reb, s.ast, s.stl, s.blk, s.tov, s.pf,
                       s.fgm, s.fga, s.ftm, s.fta, s.fg_pct,
                       s.pir_base, s.pir_36, s.score_season, s.score_alltime
                FROM seasons s
                WHERE s.player_id = ?
                ORDER BY s.year ASC
            """, (player_id,)).fetchall()
        self.send_json([dict(r) for r in rows])

    def serve_db_team_roster(self, abbr):
        if not DB_PATH.exists():
            self.send_json([], status=503)
            return
        with db_conn() as conn:
            rows = conn.execute("""
                SELECT p.id, p.name, p.pos, p.headshot, p.team,
                       s.season, s.year, s.gp, s.min,
                       s.pts, s.reb, s.ast, s.stl, s.blk, s.tov, s.pf,
                       s.fgm, s.fga, s.ftm, s.fta, s.fg_pct,
                       s.pir_base, s.pir_36, s.score_season, s.score_alltime
                FROM players p
                JOIN (
                    SELECT *, ROW_NUMBER() OVER (
                        PARTITION BY player_id ORDER BY year DESC, gp DESC
                    ) AS rn FROM seasons
                ) s ON s.player_id = p.id AND s.rn = 1
                WHERE p.team = ?
                ORDER BY s.score_season DESC
            """, (abbr,)).fetchall()
        self.send_json([dict(r) for r in rows])

    # ── ESPN proxy ────────────────────────────────────────────────────────────

    def proxy_json(self, route):
        self.proxy_url(route, ESPN_ENDPOINTS[route])

    def proxy_url(self, cache_key, url, ttl=CACHE_TTL_SECONDS):
        now    = time.time()
        cached = cache.get(cache_key)
        if cached and now - cached["time"] < ttl:
            self.send_json(cached["payload"], cached=True)
            return

        request = Request(url, headers={
            "User-Agent": "Mozilla/5.0 CourtsideAnalyticsLocal/1.0",
            "Accept":     "application/json",
        })

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
        self.send_header("Content-Type",   "application/json; charset=utf-8")
        self.send_header("Cache-Control",  "no-store")
        self.send_header("X-Local-Cache",  "hit" if cached else "miss")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # silence request logs


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    db_status = f"DB: {DB_PATH}" if DB_PATH.exists() else "DB: not built (run python3 build_db.py)"
    print(f"Courtside Analytics: http://127.0.0.1:{PORT}")
    print(db_status)
    server.serve_forever()
