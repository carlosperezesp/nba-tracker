#!/usr/bin/env python3
"""
NBA All-Time Data Builder
Usage:
    python3 build_db.py            # all seasons 1980-present (~5 min)
    python3 build_db.py --from 2000  # from 2000 onward (faster test)

Output: data/nba_all_time.json
"""
import json, time, sys
from pathlib import Path

try:
    from nba_api.stats.endpoints import (
        LeagueDashPlayerStats, LeagueStandingsV3, LeagueGameLog
    )
    from nba_api.stats.static import teams as static_teams
except ImportError:
    print("Run: pip3 install nba_api"); sys.exit(1)

ERA_CONTEXT = {
    1979:.70, 1980:.72, 1981:.73, 1982:.73, 1983:.74, 1984:.75, 1985:.76,
    1986:.77, 1987:.78, 1988:.79, 1989:.79, 1990:.80, 1991:.80, 1992:.79,
    1993:.80, 1994:.79, 1995:.78, 1996:.78, 1997:.78, 1998:.76, 1999:.74,
    2000:.76, 2001:.76, 2002:.76, 2003:.77, 2004:.76, 2005:.77, 2006:.80,
    2007:.82, 2008:.82, 2009:.82, 2010:.82, 2011:.81, 2012:.83, 2013:.86,
    2014:.87, 2015:.87, 2016:.94, 2017:.95, 2018:.96, 2019:.97, 2020:.99,
    2021:1.00, 2022:1.01, 2023:1.03, 2024:1.05, 2025:1.05, 2026:1.06,
}

TEAM_ID_TO_ABBR = {t["id"]: t["abbreviation"] for t in static_teams.get_teams()}


def season_year(s):
    return int(s[:4]) + 1


def box_score(pts, reb, ast, stl, blk, fg, fg3, mpg, tov):
    return max(1.0,
        pts*1.7 + reb*1.08 + ast*1.28 + stl*4 + blk*3
        + fg*0.10 + fg3*0.045 + mpg*0.20 - tov*1.15
    )


def fetch(cls, **kw):
    for attempt in range(3):
        try:
            df = cls(**kw).get_data_frames()[0]
            time.sleep(0.7)
            return df
        except Exception as e:
            print(f" [retry {attempt+1}: {e}]", end="", flush=True)
            time.sleep(3)
    return None


def main():
    from_year = int(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 1980
    seasons = [f"{y}-{str(y+1)[2:]:>02}" for y in range(from_year - 1, 2026)]
    print(f"Building NBA all-time data: {seasons[0]} → {seasons[-1]} ({len(seasons)} seasons)\n")

    player_seasons, team_seasons, raw_games = [], {}, []

    for season in seasons:
        year = season_year(season)
        print(f"  {season}", end="  ", flush=True)

        # ── Player stats ─────────────────────────────────────────────────────
        df = fetch(LeagueDashPlayerStats, season=season, per_mode_detailed="PerGame",
                   season_type_all_star="Regular Season", measure_type_detailed_defense="Base")
        if df is not None:
            for _, r in df.iterrows():
                gp  = int(r.get("GP",  0) or 0)
                mpg = float(r.get("MIN", 0) or 0)
                abbr = str(r.get("TEAM_ABBREVIATION", ""))
                if gp < 15 or mpg < 15 or abbr in ("", "TOT"):
                    continue
                pts  = float(r.get("PTS",    0) or 0)
                reb  = float(r.get("REB",    0) or 0)
                ast  = float(r.get("AST",    0) or 0)
                stl  = float(r.get("STL",    0) or 0)
                blk  = float(r.get("BLK",    0) or 0)
                tov  = float(r.get("TOV",    0) or 0)
                fg   = float(r.get("FG_PCT", 0) or 0)
                fg3  = float(r.get("FG3_PCT",0) or 0)
                raw  = box_score(pts, reb, ast, stl, blk, fg, fg3, mpg, tov)
                adj  = raw / ERA_CONTEXT.get(year, 1.0)
                player_seasons.append({
                    "pid":  int(r["PLAYER_ID"]),
                    "name": str(r["PLAYER_NAME"]),
                    "team": abbr,
                    "season": season, "year": year, "gp": gp,
                    "mpg": round(mpg,1), "pts": round(pts,1),
                    "reb": round(reb,1), "ast": round(ast,1),
                    "stl": round(stl,1), "blk": round(blk,1),
                    "fg_pct": round(fg,3),
                    "raw": round(raw,1), "adj": round(adj,1),
                })
            n = sum(1 for s in player_seasons if s["season"] == season)
            print(f"{n} players", end="  ", flush=True)

        # ── Team standings ────────────────────────────────────────────────────
        df = fetch(LeagueStandingsV3, season=season, season_type="Regular Season")
        if df is not None:
            for _, r in df.iterrows():
                tid  = int(r.get("TeamID", 0))
                abbr = TEAM_ID_TO_ABBR.get(tid, "")
                wins = int(r.get("WINS",   0) or 0)
                loss = int(r.get("LOSSES", 0) or 0)
                wpct = float(r.get("WinPCT", 0) or 0)
                team_seasons[f"{tid}_{year}"] = {
                    "tid": tid, "abbr": abbr, "year": year, "season": season,
                    "name": f"{r.get('TeamCity','')} {r.get('TeamName','')}".strip(),
                    "wins": wins, "losses": loss, "wpct": round(wpct, 3),
                }

        # ── Playoff game log ──────────────────────────────────────────────────
        df = fetch(LeagueGameLog, season=season, season_type_all_star="Playoffs")
        if df is not None and len(df):
            for _, r in df.iterrows():
                raw_games.append({
                    "gid":     str(r.get("GAME_ID",    "")),
                    "date":    str(r.get("GAME_DATE",   "")),
                    "team":    str(r.get("TEAM_ABBREVIATION", "")),
                    "tid":     int(r.get("TEAM_ID",    0)),
                    "pts":     int(r.get("PTS",        0) or 0),
                    "wl":      str(r.get("WL",         "")),
                    "matchup": str(r.get("MATCHUP",    "")),
                    "season": season, "year": year,
                })
            print(f"{len(df)//2} playoff games", end="", flush=True)

        print("  ✓")

    print("\nComputing rankings…")

    # ── Global normalise ──────────────────────────────────────────────────────
    max_adj = max((s["adj"] for s in player_seasons), default=1)
    for s in player_seasons:
        s["score"] = round(min(100, s["adj"] / max_adj * 100), 1)

    top_seasons = sorted(player_seasons, key=lambda x: -x["score"])[:100]

    # ── Career ratings (weighted top-5 seasons) ───────────────────────────────
    by_player = {}
    for s in player_seasons:
        by_player.setdefault(s["pid"], {"name": s["name"], "s": []})["s"].append(s)

    careers = []
    for pid, data in by_player.items():
        best = sorted(data["s"], key=lambda x: -x["adj"])
        top5 = best[:5]
        wts  = [5, 4, 3, 2, 1][: len(top5)]
        cadj = sum(s["adj"] * w for s, w in zip(top5, wts)) / sum(wts)
        careers.append({
            "pid": pid, "name": data["name"],
            "career_adj": round(cadj, 1),
            "peak_season": top5[0]["season"], "peak_team": top5[0]["team"],
            "peak_pts": top5[0]["pts"], "peak_reb": top5[0]["reb"],
            "peak_ast": top5[0]["ast"], "peak_score": top5[0]["score"],
            "total_seasons": len(best),
            "total_gp": sum(s["gp"] for s in data["s"]),
        })
    careers.sort(key=lambda x: -x["career_adj"])
    mx = careers[0]["career_adj"] if careers else 1
    for c in careers:
        c["career_score"] = round(min(100, c["career_adj"] / mx * 100), 1)
    top_careers = careers[:100]

    # ── Team season scores ────────────────────────────────────────────────────
    team_scored = []
    for t in team_seasons.values():
        abbr, year = t["abbr"], t["year"]
        rotation = [s for s in player_seasons
                    if s["team"] == abbr and s["year"] == year and s["mpg"] >= 15]
        if len(rotation) < 5:
            continue
        best12 = sorted(rotation, key=lambda x: -x["adj"])[:12]
        tadj   = sum(s["adj"] for s in best12) / len(best12)
        team_scored.append({**t,
            "team_adj": round(tadj, 1),
            "roster_count": len(best12),
            "best_player":      best12[0]["name"],
            "best_player_pts":  best12[0]["pts"],
            "best_player_score": best12[0]["score"],
        })
    team_scored.sort(key=lambda x: -x["team_adj"])
    mxt = team_scored[0]["team_adj"] if team_scored else 1
    for t in team_scored:
        t["team_score"] = round(min(100, t["team_adj"] / mxt * 100), 1)
    top_teams = team_scored[:100]

    # ── Best playoff games ────────────────────────────────────────────────────
    tq = {f"{t['abbr']}_{t['year']}": t.get("team_score", 40) for t in team_scored}

    by_game = {}
    for g in raw_games:
        by_game.setdefault(g["gid"], []).append(g)

    scored_games = []
    for gid, entries in by_game.items():
        if len(entries) != 2:
            continue
        t1, t2 = entries
        q1 = tq.get(f"{t1['team']}_{t1['year']}", 40)
        q2 = tq.get(f"{t2['team']}_{t2['year']}", 40)
        diff      = abs(t1["pts"] - t2["pts"])
        closeness = max(0, 20 - diff) / 20  # 1.0 = tie, 0.0 = 20+ pt blowout
        quality   = round((q1 + q2) / 2 * (1 + closeness * 0.3), 1)
        winner    = t1 if t1["wl"] == "W" else t2
        loser     = t2 if winner is t1 else t1
        scored_games.append({
            "date": t1["date"], "season": t1["season"], "year": t1["year"],
            "winner": winner["team"], "loser": loser["team"],
            "winner_pts": winner["pts"], "loser_pts": loser["pts"],
            "winner_score": round(tq.get(f"{winner['team']}_{winner['year']}", 40), 1),
            "loser_score":  round(tq.get(f"{loser['team']}_{loser['year']}", 40), 1),
            "quality": quality,
        })
    scored_games.sort(key=lambda x: -x["quality"])

    # ── Write output ──────────────────────────────────────────────────────────
    out = {
        "meta": {
            "built": time.strftime("%Y-%m-%d"),
            "seasons": len(seasons),
            "player_seasons": len(player_seasons),
        },
        "top_player_seasons": top_seasons,
        "top_careers":        top_careers,
        "top_team_seasons":   top_teams,
        "top_games":          scored_games[:100],
    }

    path = Path("data/nba_all_time.json")
    path.write_text(json.dumps(out, separators=(",", ":")))
    kb = path.stat().st_size / 1024
    print(f"\n✅  data/nba_all_time.json  ({kb:.0f} KB)")
    print(f"   {len(top_seasons)} top seasons | {len(top_careers)} careers"
          f" | {len(top_teams)} teams | {len(scored_games[:100])} games")


if __name__ == "__main__":
    main()
