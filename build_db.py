#!/usr/bin/env python3
"""
NBA DB Builder – ESPN source
Usage:
    python3 build_db.py           # full rebuild (~5-10 min)
    python3 build_db.py --update  # refresh current season only (~2 min)
"""
import json, sqlite3, sys, time, urllib.request, urllib.error
from bisect import bisect_left
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

DB_PATH = Path("data/nba.db")
HEADERS = {"User-Agent": "Mozilla/5.0 CourtsideAnalytics/1.0", "Accept": "application/json"}

TEAM_ABBRS = [
    "ATL","BOS","BKN","CHA","CHI","CLE","DAL","DEN","DET","GS",
    "HOU","IND","LAC","LAL","MEM","MIA","MIL","MIN","NO","NY",
    "OKC","ORL","PHI","PHX","POR","SAC","SA","TOR","UTAH","WSH",
]

# NBA championships per current franchise (all-time, including relocated predecessors)
FRANCHISE_CUPS = {
    "ATL": 1,  "BOS": 18, "BKN": 0,  "CHA": 0,  "CHI": 6,
    "CLE": 1,  "DAL": 1,  "DEN": 1,  "DET": 3,  "GS":  7,
    "HOU": 2,  "IND": 0,  "LAC": 0,  "LAL": 17, "MEM": 0,
    "MIA": 3,  "MIL": 2,  "MIN": 0,  "NO":  0,  "NY":  2,
    "OKC": 1,  "ORL": 0,  "PHI": 3,  "PHX": 0,  "POR": 1,
    "SAC": 0,  "SA":  5,  "TOR": 1,  "UTAH":0,  "WSH": 1,
}

# Championship rings for active players (name-based)
PLAYER_RINGS = {
    "LeBron James": 4, "Stephen Curry": 4, "Klay Thompson": 4, "Draymond Green": 4,
    "Udonis Haslem": 3, "Kevin Durant": 2, "Kyrie Irving": 1,
    "Nikola Jokic": 1, "Jamal Murray": 1, "Michael Porter Jr.": 1,
    "Kentavious Caldwell-Pope": 2, "Aaron Gordon": 1,
    "Jayson Tatum": 1, "Jaylen Brown": 1, "Al Horford": 1,
    "Jrue Holiday": 2, "Kristaps Porzingis": 1, "Derrick White": 1,
    "Sam Hauser": 1, "Payton Pritchard": 1, "Luke Kornet": 1,
}


def get(url):
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == 2:
                print(f"  [fail: {e}]")
                return None
            time.sleep(2)


def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id           INTEGER PRIMARY KEY,
            name         TEXT    NOT NULL,
            pos          TEXT,
            headshot     TEXT,
            team         TEXT,
            updated      TEXT,
            birth_year   INTEGER DEFAULT 0,
            career_score INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS seasons (
            player_id     INTEGER NOT NULL REFERENCES players(id),
            season        TEXT    NOT NULL,
            year          INTEGER NOT NULL,
            team          TEXT    NOT NULL DEFAULT '',
            gp            INTEGER,
            min           REAL,
            pts           REAL,
            reb           REAL,
            ast           REAL,
            stl           REAL,
            blk           REAL,
            tov           REAL,
            pf            REAL,
            fgm           REAL,
            fga           REAL,
            ftm           REAL,
            fta           REAL,
            fg_pct        REAL,
            pir_base      REAL,
            pir_36        REAL,
            score_season  INTEGER DEFAULT 0,
            score_alltime INTEGER DEFAULT 0,
            PRIMARY KEY (player_id, season, team)
        );

        CREATE INDEX IF NOT EXISTS idx_seasons_year   ON seasons(year);
        CREATE INDEX IF NOT EXISTS idx_seasons_player ON seasons(player_id);
    """)
    conn.commit()


def fetch_roster(abbr):
    data = get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{abbr}/roster")
    if not data:
        return []
    out = []
    for p in data.get("athletes", []):
        # Handle both flat list and grouped (items) format
        if "items" in p:
            players = p["items"]
        else:
            players = [p]
        for player in players:
            pid = player.get("id")
            if pid:
                birth_year = 0
                dob = player.get("dateOfBirth") or ""
                if dob:
                    try:
                        birth_year = int(dob[:4])
                    except (ValueError, IndexError):
                        pass
                if not birth_year and player.get("age"):
                    try:
                        birth_year = date.today().year - int(player["age"])
                    except (ValueError, TypeError):
                        pass
                out.append({
                    "id":         int(pid),
                    "name":       player.get("displayName") or player.get("fullName", ""),
                    "pos":        (player.get("position") or {}).get("abbreviation", ""),
                    "headshot":   (player.get("headshot") or {}).get("href", ""),
                    "team":       abbr,
                    "birth_year": birth_year,
                })
    return out


def parse_history(data):
    if not data:
        return []
    averages = next((c for c in data.get("categories", []) if c.get("name") == "averages"), None)
    if not averages:
        return []

    names = averages.get("names", [])

    def idx(name):
        try:
            return names.index(name)
        except ValueError:
            return -1

    def num(row, name):
        i = idx(name)
        return float(row["stats"][i] or 0) if 0 <= i < len(row["stats"]) else 0.0

    def pair(row, name):
        i = idx(name)
        if i < 0 or i >= len(row["stats"]):
            return 0.0, 0.0
        parts = str(row["stats"][i] or "0-0").split("-")
        a = float(parts[0]) if parts[0] else 0.0
        b = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
        return a, b

    out = []
    for row in averages.get("statistics", []):
        label = row.get("displayName", "")
        if "Totals" in label:
            continue
        gp = int(num(row, "gamesPlayed") or 0)
        if gp == 0:
            continue
        fgm, fga = pair(row, "avgFieldGoalsMade-avgFieldGoalsAttempted")
        ftm, fta = pair(row, "avgFreeThrowsMade-avgFreeThrowsAttempted")
        season_info = row.get("season") or {}
        out.append({
            "season":  season_info.get("displayName", label),
            "year":    int(season_info.get("year") or 0),
            "team_id": str(row.get("teamId", "")),
            "gp":      gp,
            "min":     num(row, "avgMinutes"),
            "pts":     num(row, "avgPoints"),
            "reb":     num(row, "avgRebounds"),
            "ast":     num(row, "avgAssists"),
            "stl":     num(row, "avgSteals"),
            "blk":     num(row, "avgBlocks"),
            "tov":     num(row, "avgTurnovers"),
            "pf":      num(row, "avgFouls"),
            "fgm":     fgm,
            "fga":     fga,
            "ftm":     ftm,
            "fta":     fta,
            "fg_pct":  num(row, "fieldGoalPct") / 100,
        })
    return out


def calc_pir(s):
    base = (s["pts"] + s["reb"] + s["ast"] + s["stl"] + s["blk"] + s["ftm"]
            - (s["fga"] - s["fgm"]) - (s["fta"] - s["ftm"]) - s["tov"] - s["pf"])
    per36 = base / s["min"] * 36 if s["min"] > 0 else 0.0
    return round(base, 2), round(per36, 2)


def to_percentiles(values):
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    return [max(1, min(100, round((bisect_left(sorted_vals, v) + 1) / n * 100)))
            for v in values]


def dynasty_cups_value(cups):
    if cups == 0:  return 10
    if cups <= 1:  return 22
    if cups <= 2:  return 32
    if cups <= 3:  return 40
    if cups <= 5:  return 50
    if cups <= 7:  return 60
    return min(85, round(55 + cups * 1.7))


def calc_career_score(alltime_scores, rings=0):
    if not alltime_scores:
        return 0
    s = sorted(alltime_scores, reverse=True)
    top3_avg = sum(s[:3]) / min(len(s), 3)
    top8_avg = sum(s[:8]) / min(len(s), 8)
    length_bonus = min(len(alltime_scores) / 18, 1.0) * 15
    cups_bonus   = rings * 4
    return round(top3_avg * 0.55 + top8_avg * 0.20 + length_bonus + cups_bonus)


def build_road_to_glory(conn):
    print("Building road_to_glory.json...")
    rows = conn.execute("""
        SELECT p.id, p.name, p.pos, p.headshot, p.team, p.birth_year, p.career_score,
               s.score_season, s.score_alltime
        FROM players p
        JOIN (
            SELECT player_id, score_season, score_alltime,
                   ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY year DESC, gp DESC) rn
            FROM seasons
        ) s ON s.player_id = p.id AND s.rn = 1
        WHERE p.career_score > 0
        ORDER BY p.career_score DESC
    """).fetchall()

    counts = {r["player_id"]: r["cnt"] for r in conn.execute(
        "SELECT player_id, COUNT(*) cnt FROM seasons GROUP BY player_id"
    ).fetchall()}

    active = []
    for r in rows:
        d = dict(r)
        d["seasons_count"] = counts.get(d["id"], 1)
        d["current_score_season"] = d.pop("score_season", 0) or 0
        d["current_score_alltime"] = d.pop("score_alltime", 0) or 0
        active.append(d)

    dynasty = []
    for abbr in TEAM_ABBRS:
        cups = FRANCHISE_CUPS.get(abbr, 0)
        cv   = dynasty_cups_value(cups)
        row  = conn.execute("""
            SELECT AVG(s.score_season) avg
            FROM players p
            JOIN (
                SELECT player_id, score_season,
                       ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY year DESC, gp DESC) rn
                FROM seasons
            ) s ON s.player_id = p.id AND s.rn = 1
            WHERE p.team = ? AND s.score_season > 0
        """, (abbr,)).fetchone()
        avg = float(row["avg"] or 0) if row else 0.0
        dynasty.append({
            "abbr":             abbr,
            "cups":             cups,
            "cups_value":       cv,
            "avg_roster_score": round(avg, 1),
            "dynasty_score":    round(cv + avg * 0.55),
        })
    dynasty.sort(key=lambda x: -x["dynasty_score"])

    out = {
        "built":                date.today().isoformat(),
        "active_career_scores": active,
        "dynasty_scores":       dynasty,
    }
    path = Path("data/road_to_glory.json")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"  ✅  {path}  ({len(active)} players · {len(dynasty)} franchises)")


def main():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    # 1. Fetch team ID → abbreviation mapping
    print("Fetching team metadata...")
    teams_data = get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams")
    team_id_to_abbr = {}
    if teams_data:
        for t in (teams_data.get("sports") or [{}])[0].get("leagues", [{}])[0].get("teams", []):
            team = t.get("team", {})
            team_id_to_abbr[str(team.get("id", ""))] = team.get("abbreviation", "")

    # 2. Fetch all rosters
    print("Fetching 30 team rosters...")
    all_players = {}
    for abbr in TEAM_ABBRS:
        players = fetch_roster(abbr)
        for p in players:
            all_players[p["id"]] = p
        print(f"  {abbr}: {len(players)} players")
        time.sleep(0.3)
    print(f"\n{len(all_players)} unique players\n")

    # 3. Upsert players
    today = date.today().isoformat()
    for p in all_players.values():
        conn.execute("""
            INSERT INTO players(id, name, pos, headshot, team, updated, birth_year)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
              name=excluded.name, pos=excluded.pos,
              headshot=excluded.headshot, team=excluded.team, updated=excluded.updated,
              birth_year=CASE WHEN excluded.birth_year > 0 THEN excluded.birth_year ELSE birth_year END
        """, (p["id"], p["name"], p["pos"], p["headshot"], p["team"], today, p.get("birth_year", 0)))
    conn.commit()

    # 4. Fetch season histories (8 concurrent)
    print("Fetching player histories...")
    all_rows = []  # list of (player_id, season_dict)

    def fetch_one(pid):
        url = (
            "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba"
            f"/athletes/{pid}/stats?region=us&lang=en&contentorigin=espn"
        )
        return pid, parse_history(get(url))

    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_one, pid): pid for pid in all_players}
        for f in as_completed(futures):
            pid, seasons = f.result()
            for s in seasons:
                s["team"] = team_id_to_abbr.get(s.pop("team_id", ""), "")
                s["pir_base"], s["pir_36"] = calc_pir(s)
                all_rows.append((pid, s))
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(all_players)}")
    print(f"  {done}/{len(all_players)} done")
    print(f"\n{len(all_rows)} season rows collected")

    # 5. Compute score_season: percentile within each year (min 15 GP, 10 MPG)
    MIN_GP, MIN_MPG = 15, 10.0

    by_year = {}
    for pid, s in all_rows:
        by_year.setdefault(s["year"], []).append((pid, s))

    for year, rows in by_year.items():
        qualified = [(pid, s) for pid, s in rows if s["gp"] >= MIN_GP and s["min"] >= MIN_MPG]
        if not qualified:
            continue
        vals   = [s["pir_36"] for _, s in qualified]
        scores = to_percentiles(vals)
        for (_, s), sc in zip(qualified, scores):
            s["score_season"] = sc

    # 6. Compute score_alltime: percentile across all qualified seasons
    qualified_all = [(pid, s) for pid, s in all_rows if s["gp"] >= MIN_GP and s["min"] >= MIN_MPG]
    all_pir36 = [s["pir_36"] for _, s in qualified_all]
    alltime   = to_percentiles(all_pir36)
    for (_, s), sc in zip(qualified_all, alltime):
        s["score_alltime"] = sc

    # 7. Upsert seasons
    for pid, s in all_rows:
        conn.execute("""
            INSERT INTO seasons(
              player_id, season, year, team, gp, min, pts, reb, ast, stl, blk,
              tov, pf, fgm, fga, ftm, fta, fg_pct, pir_base, pir_36,
              score_season, score_alltime)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(player_id, season, team) DO UPDATE SET
              year=excluded.year, gp=excluded.gp, min=excluded.min,
              pts=excluded.pts, reb=excluded.reb, ast=excluded.ast,
              stl=excluded.stl, blk=excluded.blk, tov=excluded.tov,
              pf=excluded.pf, fgm=excluded.fgm, fga=excluded.fga,
              ftm=excluded.ftm, fta=excluded.fta, fg_pct=excluded.fg_pct,
              pir_base=excluded.pir_base, pir_36=excluded.pir_36,
              score_season=excluded.score_season, score_alltime=excluded.score_alltime
        """, (
            pid, s["season"], s["year"], s.get("team", ""),
            s["gp"], s["min"], s["pts"], s["reb"], s["ast"],
            s["stl"], s["blk"], s["tov"], s["pf"],
            s["fgm"], s["fga"], s["ftm"], s["fta"], s["fg_pct"],
            s["pir_base"], s["pir_36"],
            s.get("score_season", 0), s.get("score_alltime", 0),
        ))
    conn.commit()

    # 8. Compute career scores
    print("Computing career scores...")
    by_player: dict = {}
    for pid, s in all_rows:
        v = s.get("score_alltime", 0)
        if v > 0:
            by_player.setdefault(pid, []).append(v)
    for pid, player in all_players.items():
        rings  = PLAYER_RINGS.get(player["name"], 0)
        career = calc_career_score(by_player.get(pid, []), rings)
        conn.execute("UPDATE players SET career_score = ? WHERE id = ?", (career, pid))
    conn.commit()
    print(f"  {len(all_players)} career scores computed")

    # 9. Export road_to_glory.json
    build_road_to_glory(conn)

    conn.close()

    kb = DB_PATH.stat().st_size // 1024
    print(f"\n✅  {DB_PATH}  ({kb} KB)")
    print(f"   {len(all_players)} players · {len(all_rows)} season rows")


if __name__ == "__main__":
    main()
